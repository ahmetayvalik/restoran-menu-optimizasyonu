#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bayes tabanli olasiliksal modelleme ile restoran menu optimizasyonu.

Gerekli kutuphaneler:
    # pip install pandas numpy matplotlib mlxtend

Calistirma:
    # python restaurant_menu_optimizer.py
    # python restaurant_menu_optimizer.py --data-path "comprehensive-restaurant-orders-popular-items-high-value-transactions-patterns.csv"
"""

from __future__ import annotations

import argparse
import difflib
import itertools
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder
except ImportError as exc:
    raise SystemExit(
        "mlxtend paketi bulunamadi. Lutfen once `pip install mlxtend` komutunu calistirin."
    ) from exc


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "raw" / "restaurant_orders.csv"
OUTPUT_TABLES_DIR = BASE_DIR / "outputs" / "tables"
OUTPUT_FIGURES_DIR = BASE_DIR / "outputs" / "figures"
CLEANED_OUTPUT = "cleaned_orders.csv"
RULES_OUTPUT = "association_rules.csv"
TOP_RECOMMENDATIONS_OUTPUT = "top_recommendations.csv"
MENU_SUGGESTIONS_OUTPUT = "menu_suggestions.csv"
DEFAULT_MIN_SUPPORT = 0.005
DEFAULT_MIN_CONFIDENCE = 0.08
DEFAULT_MIN_LIFT = 1.0
DEFAULT_EXTRA_ITEMS = 2
DEFAULT_TOP_N = 3
PLOT_TOP_ITEMS = "top_items.png"
CATEGORY_PLOT = "category_distribution.png"
ORDER_SIZE_PLOT = "order_size_distribution.png"
PRICE_PLOT = "item_prices.png"


COLUMN_ALIASES = {
    "order_details_id": ["order_details_id", "order_detail_id", "detail_id"],
    "order_id": ["order_id", "transaction_id", "invoice_id"],
    "order_date": ["order_date", "date", "transaction_date"],
    "order_time": ["order_time", "time", "transaction_time"],
    "item_id": ["item_id", "menu_item_id", "product_id"],
    "item_name": ["item_name", "product_name", "menu_item", "item"],
    "category": ["category", "item_category", "product_category", "cuisine"],
    "price": ["price", "item_price", "unit_price", "amount"],
}


@dataclass
class MenuScoreWeights:
    conditional_probability: float = 0.45
    lift: float = 0.25
    price: float = 0.15
    diversity: float = 0.15


def normalize_column_name(column_name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(column_name).strip().lower())
    return normalized.strip("_")


def normalize_text_value(value: object, default: str = "Unknown") -> str:
    if pd.isna(value):
        return default
    text = re.sub(r"\s+", " ", str(value).strip())
    if not text:
        return default
    return text.title()


def normalize_lookup_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def mode_or_default(series: pd.Series, default: str = "Unknown") -> str:
    cleaned = series.dropna()
    if cleaned.empty:
        return default
    modes = cleaned.mode()
    if modes.empty:
        return default
    return str(modes.iloc[0])


def detect_delimiter(header_line: str) -> Optional[str]:
    delimiter_counts = {
        "|": header_line.count("|"),
        ",": header_line.count(","),
        ";": header_line.count(";"),
        "\t": header_line.count("\t"),
    }
    best_delimiter = max(delimiter_counts, key=delimiter_counts.get)
    return best_delimiter if delimiter_counts[best_delimiter] > 0 else None


def split_single_column_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.shape[1] != 1:
        return df

    raw_header = str(df.columns[0])
    delimiter = detect_delimiter(raw_header)
    if delimiter is None:
        sample_text = " ".join(df.iloc[:5, 0].astype(str).tolist())
        delimiter = detect_delimiter(sample_text)
    if delimiter is None:
        raise ValueError("Veri tek sutunda ve ayirac tespit edilemedi. Dosya formatini kontrol edin.")

    split_df = df.iloc[:, 0].astype(str).str.split(delimiter, expand=True, regex=False)
    header_parts = [normalize_column_name(part) for part in raw_header.split(delimiter)]
    if len(header_parts) == split_df.shape[1]:
        split_df.columns = header_parts
    else:
        split_df.columns = [f"column_{index + 1}" for index in range(split_df.shape[1])]
    return split_df


def read_flexible_csv(data_path: Path) -> pd.DataFrame:
    if not data_path.exists():
        raise FileNotFoundError(f"Veri dosyasi bulunamadi: {data_path}")

    with data_path.open("r", encoding="utf-8-sig", errors="ignore") as file_obj:
        header_line = file_obj.readline()

    delimiter = detect_delimiter(header_line)
    read_kwargs = {"dtype": str, "engine": "python", "on_bad_lines": "skip"}
    if delimiter is not None:
        df = pd.read_csv(data_path, sep=delimiter, **read_kwargs)
    else:
        df = pd.read_csv(data_path, sep=None, **read_kwargs)

    if df.shape[1] == 1:
        df = split_single_column_dataframe(df)
    return df


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_column_name(column) for column in df.columns]

    rename_map = {}
    for canonical_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_column_name(alias)
            if normalized_alias in df.columns:
                rename_map[normalized_alias] = canonical_name
                break
    return df.rename(columns=rename_map)


def assign_time_period(hour_value: float) -> str:
    if pd.isna(hour_value):
        return "unknown"
    if 11 <= int(hour_value) < 16:
        return "lunch"
    if 16 <= int(hour_value) < 22:
        return "dinner"
    return "other"


def clean_order_data(raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    df = standardize_columns(raw_df)
    df = df.replace(r"^\s*$", np.nan, regex=True)
    df = df.dropna(how="all").copy()

    missing_required = [column for column in ["order_id", "item_name"] if column not in df.columns]
    if missing_required:
        raise ValueError(
            "Veri setinde zorunlu kolonlar bulunamadi: " + ", ".join(missing_required)
        )

    if "category" not in df.columns:
        df["category"] = "Unknown"
    if "price" not in df.columns:
        df["price"] = np.nan
    if "order_date" not in df.columns:
        df["order_date"] = np.nan
    if "order_time" not in df.columns:
        df["order_time"] = np.nan

    initial_rows = len(df)
    df["order_id"] = df["order_id"].astype(str).str.strip()
    df["item_name"] = df["item_name"].apply(lambda value: normalize_text_value(value, default=""))
    df["category"] = df["category"].apply(lambda value: normalize_text_value(value, default="Unknown"))
    df["price"] = pd.to_numeric(
        df["price"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce",
    )
    missing_price_before_fill = int(df["price"].isna().sum())

    df = df[df["order_id"] != ""].copy()
    df = df[df["item_name"] != ""].copy()

    dedupe_columns = [
        column
        for column in ["order_details_id", "order_id", "order_date", "order_time", "item_id", "item_name"]
        if column in df.columns
    ]
    before_deduplication = len(df)
    df = df.drop_duplicates(subset=dedupe_columns).copy()

    category_by_item = (
        df.loc[df["category"] != "Unknown"]
        .groupby("item_name")["category"]
        .agg(lambda series: mode_or_default(series, default="Unknown"))
    )
    df["category"] = (
        df["category"]
        .mask(df["category"] == "Unknown", df["item_name"].map(category_by_item))
        .fillna("Unknown")
    )

    price_by_item = df.groupby("item_name")["price"].median()
    df["price"] = df["price"].fillna(df["item_name"].map(price_by_item))
    global_median_price = df["price"].median()
    if pd.isna(global_median_price):
        global_median_price = 0.0
    df["price"] = df["price"].fillna(global_median_price)

    df["order_date_parsed"] = pd.to_datetime(df["order_date"], format="%m/%d/%y", errors="coerce")
    df["order_time_parsed"] = pd.to_datetime(df["order_time"], format="%I:%M:%S %p", errors="coerce")
    df["order_hour"] = df["order_time_parsed"].dt.hour
    df["time_period"] = df["order_hour"].apply(assign_time_period)

    ordered_columns = [
        column
        for column in [
            "order_details_id",
            "order_id",
            "order_date",
            "order_time",
            "item_id",
            "item_name",
            "category",
            "price",
            "order_date_parsed",
            "order_time_parsed",
            "order_hour",
            "time_period",
        ]
        if column in df.columns
    ]
    df = df[ordered_columns].copy()

    cleaning_report = {
        "initial_rows": initial_rows,
        "final_rows": len(df),
        "dropped_rows": initial_rows - len(df),
        "duplicate_rows_removed": before_deduplication - len(df),
        "missing_category_filled": int((df["category"] == "Unknown").sum()),
        "price_imputed_rows": missing_price_before_fill,
    }
    return df.reset_index(drop=True), cleaning_report


def create_transactions(
    df: pd.DataFrame,
    min_items_for_analysis: int = 2,
) -> Tuple[List[List[str]], List[List[str]], pd.DataFrame]:
    if df.empty:
        raise ValueError("Temizlenmis veri bos. Transaction olusturulamadi.")

    order_item_lists = (
        df.groupby("order_id")["item_name"]
        .apply(lambda series: list(dict.fromkeys(series.tolist())))
        .reset_index(name="items")
    )
    order_item_lists["item_count"] = order_item_lists["items"].apply(len)

    all_transactions = order_item_lists["items"].tolist()
    analysis_transactions = order_item_lists.loc[
        order_item_lists["item_count"] >= min_items_for_analysis, "items"
    ].tolist()
    return all_transactions, analysis_transactions, order_item_lists


def build_item_catalog(df: pd.DataFrame) -> pd.DataFrame:
    catalog = (
        df.groupby("item_name")
        .agg(
            category=("category", lambda series: mode_or_default(series, default="Unknown")),
            price=("price", "median"),
            order_frequency=("order_id", "nunique"),
            quantity_sold=("item_name", "size"),
        )
        .reset_index()
        .sort_values(["order_frequency", "quantity_sold"], ascending=False)
        .reset_index(drop=True)
    )
    return catalog


def save_bar_plot(
    series: pd.Series,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Path,
    color: str = "#2F6B7C",
) -> None:
    if series.empty:
        return

    plt.figure(figsize=(10, 6))
    series.sort_values().plot(kind="barh", color=color)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_histogram(
    series: pd.Series,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Path,
    bins: int = 10,
    color: str = "#C2663D",
) -> None:
    if series.empty:
        return

    plt.figure(figsize=(10, 6))
    plt.hist(series, bins=bins, color=color, edgecolor="black")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def exploratory_analysis(df: pd.DataFrame, output_dir: Path, save_plots: bool = True) -> Dict[str, object]:
    order_counts = df.groupby("item_name")["order_id"].nunique().sort_values(ascending=False)
    category_distribution = df.groupby("category")["item_name"].count().sort_values(ascending=False)
    order_sizes = df.groupby("order_id")["item_name"].nunique().sort_values(ascending=False)
    item_prices = df.groupby("item_name")["price"].median().sort_values(ascending=False)

    if save_plots:
        save_bar_plot(
            order_counts.head(10),
            title="En Cok Siparis Edilen Urunler",
            xlabel="Siparis Sayisi",
            ylabel="Urun",
            output_path=output_dir / PLOT_TOP_ITEMS,
        )
        save_bar_plot(
            category_distribution,
            title="Kategori Dagilimi",
            xlabel="Urun Adedi",
            ylabel="Kategori",
            output_path=output_dir / CATEGORY_PLOT,
            color="#5A9367",
        )
        save_histogram(
            order_sizes,
            title="Siparis Basi Urun Sayisi Dagilimi",
            xlabel="Urun Sayisi",
            ylabel="Siparis Adedi",
            output_path=output_dir / ORDER_SIZE_PLOT,
        )
        save_bar_plot(
            item_prices,
            title="Urun Fiyatlari",
            xlabel="Median Fiyat",
            ylabel="Urun",
            output_path=output_dir / PRICE_PLOT,
            color="#8E5C88",
        )

    return {
        "top_products": order_counts.reset_index(name="order_count"),
        "category_distribution": category_distribution.reset_index(name="item_line_count"),
        "order_sizes": order_sizes.reset_index(name="item_count"),
        "avg_items_per_order": float(order_sizes.mean()),
        "single_item_orders": int((order_sizes == 1).sum()),
        "multi_item_orders": int((order_sizes > 1).sum()),
        "most_expensive_items": item_prices.head(5).reset_index(name="median_price"),
        "cheapest_items": item_prices.sort_values(ascending=True).head(5).reset_index(name="median_price"),
    }


def encode_transactions(transactions: Sequence[Sequence[str]]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame()

    encoder = TransactionEncoder()
    encoded_array = encoder.fit(transactions).transform(transactions)
    return pd.DataFrame(encoded_array, columns=encoder.columns_)


def run_association_rule_mining(
    transactions: Sequence[Sequence[str]],
    min_support: float,
    min_confidence: float,
    min_lift: float,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    encoded_df = encode_transactions(transactions)
    if encoded_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    frequent_itemsets = apriori(encoded_df, min_support=min_support, use_colnames=True)
    if frequent_itemsets.empty:
        return frequent_itemsets, pd.DataFrame()

    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
    if rules.empty:
        return frequent_itemsets, rules

    rules = rules[rules["lift"] >= min_lift].copy()
    if rules.empty:
        return frequent_itemsets, rules

    rules["antecedents_str"] = rules["antecedents"].apply(lambda items: ", ".join(sorted(items)))
    rules["consequents_str"] = rules["consequents"].apply(lambda items: ", ".join(sorted(items)))
    rules["rule_strength"] = rules["confidence"] * rules["lift"]
    rules = rules.sort_values(
        ["rule_strength", "confidence", "lift", "support"],
        ascending=False,
    ).reset_index(drop=True)
    return frequent_itemsets, rules


def export_rules_for_csv(rules_df: pd.DataFrame) -> pd.DataFrame:
    if rules_df.empty:
        return pd.DataFrame(
            columns=[
                "antecedents",
                "consequents",
                "support",
                "confidence",
                "lift",
                "leverage",
                "conviction",
                "rule_strength",
            ]
        )

    export_df = rules_df.copy()
    export_df["antecedents"] = export_df["antecedents_str"]
    export_df["consequents"] = export_df["consequents_str"]
    selected_columns = [
        "antecedents",
        "consequents",
        "support",
        "confidence",
        "lift",
        "leverage",
        "conviction",
        "rule_strength",
    ]
    return export_df[selected_columns].copy()


def compute_transaction_statistics(
    transactions: Sequence[Sequence[str]],
) -> Tuple[Counter, Dict[str, Counter], int]:
    item_counts: Counter = Counter()
    co_occurrence_counts: Dict[str, Counter] = defaultdict(Counter)

    for transaction in transactions:
        unique_items = list(dict.fromkeys(transaction))
        for item in unique_items:
            item_counts[item] += 1
        for given_item in unique_items:
            for target_item in unique_items:
                if given_item != target_item:
                    co_occurrence_counts[given_item][target_item] += 1

    return item_counts, co_occurrence_counts, len(transactions)


def conditional_probability(
    target_item: str,
    given_item: str,
    transactions: Sequence[Sequence[str]],
) -> float:
    if not target_item or not given_item:
        return 0.0

    normalized_target = normalize_text_value(target_item, default="")
    normalized_given = normalize_text_value(given_item, default="")

    given_count = 0
    joint_count = 0
    for transaction in transactions:
        basket = set(transaction)
        if normalized_given in basket:
            given_count += 1
            if normalized_target in basket:
                joint_count += 1

    if given_count == 0:
        return 0.0
    return joint_count / given_count


def resolve_value(user_value: str, valid_values: Sequence[str]) -> Tuple[Optional[str], List[str]]:
    normalized_map = {normalize_lookup_key(value): value for value in valid_values}
    normalized_input = normalize_lookup_key(user_value)
    if normalized_input in normalized_map:
        return normalized_map[normalized_input], []

    close_matches = difflib.get_close_matches(user_value, valid_values, n=3, cutoff=0.5)
    return None, close_matches


def get_rule_metrics_for_pair(base_item: str, candidate_item: str, rules_df: pd.DataFrame) -> Tuple[float, float]:
    if rules_df.empty:
        return 0.0, 0.0

    relevant_rules = rules_df[
        rules_df["antecedents"].apply(lambda items: set(items) == {base_item})
        & rules_df["consequents"].apply(lambda items: set(items) == {candidate_item})
    ]
    if relevant_rules.empty:
        return 0.0, 0.0

    best_rule = relevant_rules.sort_values(["confidence", "lift"], ascending=False).iloc[0]
    return float(best_rule["confidence"]), float(best_rule["lift"])


def build_catalog_maps(item_catalog: pd.DataFrame) -> Tuple[Dict[str, Dict[str, object]], float, float]:
    catalog_map = item_catalog.set_index("item_name").to_dict(orient="index")
    min_price = float(item_catalog["price"].min()) if not item_catalog.empty else 0.0
    max_price = float(item_catalog["price"].max()) if not item_catalog.empty else 0.0
    return catalog_map, min_price, max_price


def normalize_score(value: float, minimum: float, maximum: float, inverse: bool = False) -> float:
    if maximum <= minimum:
        return 1.0

    scaled = (value - minimum) / (maximum - minimum)
    scaled = max(0.0, min(1.0, scaled))
    return 1.0 - scaled if inverse else scaled


def recommend_items_for_product(
    selected_item: str,
    transactions: Sequence[Sequence[str]],
    item_catalog: pd.DataFrame,
    rules_df: pd.DataFrame,
    top_n: int,
    weights: MenuScoreWeights,
) -> pd.DataFrame:
    if item_catalog.empty:
        return pd.DataFrame()

    valid_items = item_catalog["item_name"].tolist()
    resolved_item, suggestions = resolve_value(selected_item, valid_items)
    if resolved_item is None:
        suggestion_text = ", ".join(suggestions) if suggestions else "benzer urun bulunamadi"
        print(f"[UYARI] '{selected_item}' veri setinde bulunamadi. Oneri: {suggestion_text}")
        return pd.DataFrame()

    item_counts, co_occurrence_counts, total_orders = compute_transaction_statistics(transactions)
    base_count = item_counts.get(resolved_item, 0)
    if base_count == 0 or total_orders == 0:
        return pd.DataFrame()

    catalog_map, min_price, max_price = build_catalog_maps(item_catalog)
    recommendation_rows = []
    for candidate_item, joint_count in co_occurrence_counts.get(resolved_item, Counter()).items():
        candidate_count = item_counts.get(candidate_item, 0)
        if candidate_count == 0:
            continue

        raw_conditional_probability = joint_count / base_count
        raw_lift = raw_conditional_probability / (candidate_count / total_orders)
        rule_confidence, rule_lift = get_rule_metrics_for_pair(resolved_item, candidate_item, rules_df)
        confidence_score = max(raw_conditional_probability, rule_confidence)
        lift_score = max(raw_lift, rule_lift)

        candidate_price = float(catalog_map.get(candidate_item, {}).get("price", 0.0))
        price_score = normalize_score(candidate_price, min_price, max_price, inverse=True)
        recommendation_score = (
            weights.conditional_probability * confidence_score
            + weights.lift * min(lift_score / 3.0, 1.0)
            + weights.price * price_score
        )

        recommendation_rows.append(
            {
                "base_item": resolved_item,
                "recommended_item": candidate_item,
                "joint_order_count": joint_count,
                "base_order_count": base_count,
                "candidate_order_count": candidate_count,
                "conditional_probability": raw_conditional_probability,
                "confidence": confidence_score,
                "lift": lift_score,
                "recommended_item_category": catalog_map.get(candidate_item, {}).get("category", "Unknown"),
                "recommended_item_price": candidate_price,
                "item_score": recommendation_score,
            }
        )

    recommendation_df = pd.DataFrame(recommendation_rows)
    if recommendation_df.empty:
        return recommendation_df

    recommendation_df = recommendation_df.sort_values(
        ["item_score", "conditional_probability", "lift", "joint_order_count"],
        ascending=False,
    ).reset_index(drop=True)
    return recommendation_df.head(top_n).copy()


def score_menu_combination(
    base_item: str,
    extra_items: Sequence[str],
    candidate_lookup: Dict[str, Dict[str, object]],
    catalog_map: Dict[str, Dict[str, object]],
    min_price: float,
    max_price: float,
    weights: MenuScoreWeights,
) -> Dict[str, object]:
    menu_items = [base_item] + list(extra_items)
    categories = [str(catalog_map.get(item, {}).get("category", "Unknown")) for item in menu_items]
    prices = [float(catalog_map.get(item, {}).get("price", 0.0)) for item in menu_items]

    conditional_values = [
        float(candidate_lookup[item]["conditional_probability"]) for item in extra_items if item in candidate_lookup
    ]
    lift_values = [float(candidate_lookup[item]["lift"]) for item in extra_items if item in candidate_lookup]

    avg_conditional_probability = float(np.mean(conditional_values)) if conditional_values else 0.0
    avg_lift = float(np.mean(lift_values)) if lift_values else 0.0
    total_price = float(sum(prices))

    menu_min_price = prices[0] + len(extra_items) * min_price if prices else min_price
    menu_max_price = prices[0] + len(extra_items) * max_price if prices else max_price
    price_score = normalize_score(total_price, menu_min_price, menu_max_price, inverse=True)
    diversity_bonus = len(set(categories)) / len(categories) if categories else 0.0

    menu_score = (
        weights.conditional_probability * avg_conditional_probability
        + weights.lift * min(avg_lift / 3.0, 1.0)
        + weights.price * price_score
        + weights.diversity * diversity_bonus
    )

    return {
        "menu_items": " | ".join(menu_items),
        "total_price": total_price,
        "avg_conditional_probability": avg_conditional_probability,
        "avg_lift": avg_lift,
        "category_diversity": diversity_bonus,
        "menu_score": menu_score,
        "categories": " | ".join(categories),
    }


def generate_menu_suggestions(
    base_item: str,
    recommendation_df: pd.DataFrame,
    item_catalog: pd.DataFrame,
    top_n: int,
    extra_items_count: int,
    weights: MenuScoreWeights,
) -> pd.DataFrame:
    if recommendation_df.empty or extra_items_count <= 0:
        return pd.DataFrame()

    resolved_base_item = recommendation_df["base_item"].iloc[0]
    catalog_map, min_price, max_price = build_catalog_maps(item_catalog)
    candidate_pool = recommendation_df.head(max(6, top_n * 3)).copy()
    candidate_lookup = candidate_pool.set_index("recommended_item").to_dict(orient="index")
    candidate_items = candidate_pool["recommended_item"].tolist()

    if len(candidate_items) < extra_items_count:
        extra_items_count = len(candidate_items)
    if extra_items_count == 0:
        return pd.DataFrame()

    menu_rows = []
    for combination in itertools.combinations(candidate_items, extra_items_count):
        scored_menu = score_menu_combination(
            base_item=resolved_base_item,
            extra_items=combination,
            candidate_lookup=candidate_lookup,
            catalog_map=catalog_map,
            min_price=min_price,
            max_price=max_price,
            weights=weights,
        )
        scored_menu["base_item"] = resolved_base_item
        scored_menu["requested_item"] = base_item
        menu_rows.append(scored_menu)

    menu_df = pd.DataFrame(menu_rows)
    if menu_df.empty:
        return menu_df

    menu_df = menu_df.sort_values(
        ["menu_score", "avg_conditional_probability", "avg_lift"],
        ascending=False,
    ).reset_index(drop=True)
    menu_df["menu_rank"] = np.arange(1, len(menu_df) + 1)
    return menu_df.head(top_n).copy()


def recommend_for_category(
    selected_category: str,
    cleaned_df: pd.DataFrame,
    item_catalog: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    valid_categories = sorted(cleaned_df["category"].dropna().unique().tolist())
    resolved_category, suggestions = resolve_value(selected_category, valid_categories)
    if resolved_category is None:
        suggestion_text = ", ".join(suggestions) if suggestions else "benzer kategori bulunamadi"
        print(f"[UYARI] '{selected_category}' kategorisi bulunamadi. Oneri: {suggestion_text}")
        return pd.DataFrame()

    category_orders = set(cleaned_df.loc[cleaned_df["category"] == resolved_category, "order_id"].tolist())
    if not category_orders:
        return pd.DataFrame()

    item_catalog_map = item_catalog.set_index("item_name")
    in_category_items = set(
        cleaned_df.loc[cleaned_df["category"] == resolved_category, "item_name"].dropna().unique().tolist()
    )
    category_co_occurrence = (
        cleaned_df.loc[
            cleaned_df["order_id"].isin(category_orders) & ~cleaned_df["item_name"].isin(in_category_items)
        ]
        .groupby("item_name")["order_id"]
        .nunique()
        .sort_values(ascending=False)
    )

    if category_co_occurrence.empty:
        category_internal_popularity = (
            cleaned_df.loc[cleaned_df["category"] == resolved_category]
            .groupby("item_name")["order_id"]
            .nunique()
            .sort_values(ascending=False)
            .head(top_n)
        )
        fallback_df = category_internal_popularity.reset_index(name="order_count")
        fallback_df["selected_category"] = resolved_category
        fallback_df["conditional_probability_given_category"] = (
            fallback_df["order_count"] / max(len(category_orders), 1)
        )
        fallback_df["recommended_item_category"] = resolved_category
        fallback_df["recommended_item_price"] = fallback_df["item_name"].map(item_catalog_map["price"])
        return fallback_df.rename(columns={"item_name": "recommended_item"})

    category_df = category_co_occurrence.reset_index(name="co_occurring_orders")
    category_df["selected_category"] = resolved_category
    category_df["conditional_probability_given_category"] = (
        category_df["co_occurring_orders"] / max(len(category_orders), 1)
    )
    category_df["recommended_item_category"] = category_df["item_name"].map(item_catalog_map["category"])
    category_df["recommended_item_price"] = category_df["item_name"].map(item_catalog_map["price"])
    category_df = category_df.rename(columns={"item_name": "recommended_item"})
    return category_df.head(top_n).copy()


def generate_top_recommendations_export(
    item_catalog: pd.DataFrame,
    transactions: Sequence[Sequence[str]],
    rules_df: pd.DataFrame,
    top_n: int,
    weights: MenuScoreWeights,
) -> pd.DataFrame:
    all_recommendations = []
    for item_name in item_catalog["item_name"].tolist():
        product_recommendations = recommend_items_for_product(
            selected_item=item_name,
            transactions=transactions,
            item_catalog=item_catalog,
            rules_df=rules_df,
            top_n=top_n,
            weights=weights,
        )
        if not product_recommendations.empty:
            all_recommendations.append(product_recommendations)

    if not all_recommendations:
        return pd.DataFrame()
    return pd.concat(all_recommendations, ignore_index=True)


def generate_time_based_menu_analysis(
    cleaned_df: pd.DataFrame,
    min_support: float,
    min_confidence: float,
    min_lift: float,
    top_n: int,
    extra_items_count: int,
    weights: MenuScoreWeights,
) -> pd.DataFrame:
    if "time_period" not in cleaned_df.columns:
        return pd.DataFrame()

    period_frames = []
    for period_name in ["lunch", "dinner"]:
        period_df = cleaned_df.loc[cleaned_df["time_period"] == period_name].copy()
        if period_df["order_id"].nunique() < 10:
            continue

        period_catalog = build_item_catalog(period_df)
        period_transactions_all, period_transactions_analysis, _ = create_transactions(period_df)
        _, period_rules = run_association_rule_mining(
            transactions=period_transactions_analysis,
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
        )

        popular_period_items = (
            period_df.groupby("item_name")["order_id"]
            .nunique()
            .sort_values(ascending=False)
            .head(2)
            .index
            .tolist()
        )

        for base_item in popular_period_items:
            period_recommendations = recommend_items_for_product(
                selected_item=base_item,
                transactions=period_transactions_all,
                item_catalog=period_catalog,
                rules_df=period_rules,
                top_n=max(6, top_n),
                weights=weights,
            )
            period_menus = generate_menu_suggestions(
                base_item=base_item,
                recommendation_df=period_recommendations,
                item_catalog=period_catalog,
                top_n=top_n,
                extra_items_count=extra_items_count,
                weights=weights,
            )
            if period_menus.empty:
                continue

            period_menus["scenario"] = "time_period"
            period_menus["context"] = period_name
            period_frames.append(period_menus)

    if not period_frames:
        return pd.DataFrame()
    return pd.concat(period_frames, ignore_index=True)


def print_section_title(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def print_dataframe(label: str, df: pd.DataFrame, max_rows: int = 10) -> None:
    print(f"\n{label}")
    if df.empty:
        print("  Kayit bulunamadi.")
        return
    print(df.head(max_rows).to_string(index=False))


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


def demo_product_recommendations(
    demo_items: Sequence[str],
    transactions: Sequence[Sequence[str]],
    item_catalog: pd.DataFrame,
    rules_df: pd.DataFrame,
    top_n: int,
    extra_items_count: int,
    weights: MenuScoreWeights,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    recommendation_frames = []
    menu_frames = []

    for demo_item in demo_items:
        product_recommendations = recommend_items_for_product(
            selected_item=demo_item,
            transactions=transactions,
            item_catalog=item_catalog,
            rules_df=rules_df,
            top_n=max(6, top_n),
            weights=weights,
        )
        if product_recommendations.empty:
            continue

        product_recommendations["scenario"] = "demo_item"
        product_recommendations["context"] = demo_item
        recommendation_frames.append(product_recommendations.head(top_n))

        demo_menus = generate_menu_suggestions(
            base_item=demo_item,
            recommendation_df=product_recommendations,
            item_catalog=item_catalog,
            top_n=top_n,
            extra_items_count=extra_items_count,
            weights=weights,
        )
        if not demo_menus.empty:
            demo_menus["scenario"] = "demo_item"
            demo_menus["context"] = demo_item
            menu_frames.append(demo_menus)

    recommendation_export = (
        pd.concat(recommendation_frames, ignore_index=True) if recommendation_frames else pd.DataFrame()
    )
    menu_export = pd.concat(menu_frames, ignore_index=True) if menu_frames else pd.DataFrame()
    return recommendation_export, menu_export


def interactive_cli(
    cleaned_df: pd.DataFrame,
    transactions: Sequence[Sequence[str]],
    item_catalog: pd.DataFrame,
    rules_df: pd.DataFrame,
    weights: MenuScoreWeights,
    top_n: int,
    extra_items_count: int,
) -> None:
    if not sys.stdin.isatty():
        print("\n[Bilgi] Non-interactive ortam algilandi. Terminal arayuzu atlandi.")
        return

    print_section_title("DINAMIK ONERI ARAYUZU")
    print("Komutlar: item, category, quit")

    while True:
        try:
            mode = input("\nSecim tipi girin (item/category/quit): ").strip().lower()
        except EOFError:
            print("\nArayuz sonlandirildi.")
            break

        if mode in {"quit", "q", "exit"}:
            print("Arayuz kapatildi.")
            break
        if mode == "item":
            user_item = input("Urun adi: ").strip()
            recommendations = recommend_items_for_product(
                selected_item=user_item,
                transactions=transactions,
                item_catalog=item_catalog,
                rules_df=rules_df,
                top_n=max(6, top_n),
                weights=weights,
            )
            menus = generate_menu_suggestions(
                base_item=user_item,
                recommendation_df=recommendations,
                item_catalog=item_catalog,
                top_n=top_n,
                extra_items_count=extra_items_count,
                weights=weights,
            )
            print_dataframe("Urun Bazli Oneriler", recommendations, max_rows=top_n)
            print_dataframe("Menu Onerileri", menus, max_rows=top_n)
            continue
        if mode == "category":
            user_category = input("Kategori adi: ").strip()
            category_recommendations = recommend_for_category(
                selected_category=user_category,
                cleaned_df=cleaned_df,
                item_catalog=item_catalog,
                top_n=top_n,
            )
            print_dataframe("Kategori Bazli Oneriler", category_recommendations, max_rows=top_n)
            continue
        print("Gecersiz secim. Lutfen item, category veya quit girin.")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bayes tabanli olasiliksal modelleme ile restoran menu optimizasyonu"
    )
    parser.add_argument("--data-path", default=str(DATA_PATH), help="CSV veri dosyasi yolu")
    parser.add_argument("--min-support", type=float, default=DEFAULT_MIN_SUPPORT)
    parser.add_argument("--min-confidence", type=float, default=DEFAULT_MIN_CONFIDENCE)
    parser.add_argument("--min-lift", type=float, default=DEFAULT_MIN_LIFT)
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Top N cikti sayisi")
    parser.add_argument(
        "--extra-items",
        type=int,
        default=DEFAULT_EXTRA_ITEMS,
        help="Menuye eklenecek ekstra urun sayisi",
    )
    parser.add_argument("--skip-plots", action="store_true", help="PNG grafiklerini uretme")
    parser.add_argument("--skip-interactive", action="store_true", help="Terminal arayuzunu atla")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    data_path = Path(args.data_path)
    OUTPUT_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    weights = MenuScoreWeights()

    print_section_title("VERI YUKLEME VE TEMIZLEME")
    raw_df = read_flexible_csv(data_path)
    cleaned_df, cleaning_report = clean_order_data(raw_df)
    save_dataframe(cleaned_df, OUTPUT_TABLES_DIR / CLEANED_OUTPUT)

    for metric_name, metric_value in cleaning_report.items():
        print(f"{metric_name}: {metric_value}")
    print(f"Temizlenmis veri kaydedildi: {OUTPUT_TABLES_DIR / CLEANED_OUTPUT}")

    all_transactions, analysis_transactions, order_item_report = create_transactions(cleaned_df)
    item_catalog = build_item_catalog(cleaned_df)

    print_section_title("KESIFSEL ANALIZ")
    eda_results = exploratory_analysis(
        cleaned_df,
        output_dir=OUTPUT_FIGURES_DIR,
        save_plots=not args.skip_plots,
    )
    print(f"Toplam siparis sayisi: {cleaned_df['order_id'].nunique()}")
    print(f"Toplam benzersiz urun: {cleaned_df['item_name'].nunique()}")
    print(f"Ortalama siparis basi urun sayisi: {eda_results['avg_items_per_order']:.2f}")
    print(f"Tek urunlu siparis sayisi: {eda_results['single_item_orders']}")
    print(f"Cok urunlu siparis sayisi: {eda_results['multi_item_orders']}")
    print_dataframe("En Cok Siparis Edilen Urunler", eda_results["top_products"], max_rows=10)
    print_dataframe("Kategori Dagilimi", eda_results["category_distribution"], max_rows=10)
    print_dataframe("En Pahali Urunler", eda_results["most_expensive_items"], max_rows=5)
    print_dataframe("En Ucuz Urunler", eda_results["cheapest_items"], max_rows=5)
    print_dataframe(
        "Tek Urunlu Siparis Ornekleri",
        order_item_report.loc[order_item_report["item_count"] == 1].head(10),
        max_rows=10,
    )

    print_section_title("ASSOCIATION RULE MINING")
    frequent_itemsets, rules_df = run_association_rule_mining(
        transactions=analysis_transactions,
        min_support=args.min_support,
        min_confidence=args.min_confidence,
        min_lift=args.min_lift,
    )
    rules_export = export_rules_for_csv(rules_df)
    save_dataframe(rules_export, OUTPUT_TABLES_DIR / RULES_OUTPUT)
    print(f"Frequent itemset sayisi: {len(frequent_itemsets)}")
    print(f"Rule sayisi: {len(rules_export)}")
    print_dataframe("En Guclu Kurallar", rules_export, max_rows=10)
    print(f"Association rules kaydedildi: {OUTPUT_TABLES_DIR / RULES_OUTPUT}")

    print_section_title("KOSELLI OLASILIK ORNEKLERI")
    probability_examples = [
        ("Korean Beef Bowl", "Hamburger"),
        ("French Fries", "Hamburger"),
        ("Chips & Salsa", "Chicken Burrito"),
    ]
    for target_item, given_item in probability_examples:
        probability = conditional_probability(target_item, given_item, all_transactions)
        print(f"P({target_item} | {given_item}) = {probability:.4f}")

    print_section_title("URUN BAZLI ONERILER VE MENU URETIMI")
    all_top_recommendations = generate_top_recommendations_export(
        item_catalog=item_catalog,
        transactions=all_transactions,
        rules_df=rules_df,
        top_n=args.top_n,
        weights=weights,
    )
    save_dataframe(all_top_recommendations, OUTPUT_TABLES_DIR / TOP_RECOMMENDATIONS_OUTPUT)
    print(f"Top recommendations kaydedildi: {OUTPUT_TABLES_DIR / TOP_RECOMMENDATIONS_OUTPUT}")

    demo_items = ["Korean Beef Bowl", "Hamburger", "Cola"]
    demo_recommendations, demo_menu_suggestions = demo_product_recommendations(
        demo_items=demo_items,
        transactions=all_transactions,
        item_catalog=item_catalog,
        rules_df=rules_df,
        top_n=args.top_n,
        extra_items_count=args.extra_items,
        weights=weights,
    )
    print_dataframe("Demo Urun Onerileri", demo_recommendations, max_rows=20)
    print_dataframe("Demo Menu Onerileri", demo_menu_suggestions, max_rows=10)

    print_section_title("KATEGORI BAZLI AKILLI ONERI")
    for sample_category in ["Asian", "Italian"]:
        category_suggestions = recommend_for_category(
            selected_category=sample_category,
            cleaned_df=cleaned_df,
            item_catalog=item_catalog,
            top_n=args.top_n,
        )
        print_dataframe(f"{sample_category} Kategorisi Icin Oneriler", category_suggestions, max_rows=args.top_n)

    print_section_title("ZAMAN BAZLI MENU ANALIZI")
    time_based_menus = generate_time_based_menu_analysis(
        cleaned_df=cleaned_df,
        min_support=args.min_support,
        min_confidence=args.min_confidence,
        min_lift=args.min_lift,
        top_n=args.top_n,
        extra_items_count=args.extra_items,
        weights=weights,
    )
    print_dataframe("Ogle ve Aksam Menu Onerileri", time_based_menus, max_rows=10)

    menu_exports = []
    if not demo_menu_suggestions.empty:
        menu_exports.append(demo_menu_suggestions.copy())
    if not time_based_menus.empty:
        menu_exports.append(time_based_menus.copy())

    if menu_exports:
        final_menu_export = pd.concat(menu_exports, ignore_index=True)
    else:
        final_menu_export = pd.DataFrame(
            columns=[
                "base_item",
                "menu_items",
                "total_price",
                "avg_conditional_probability",
                "avg_lift",
                "category_diversity",
                "menu_score",
                "menu_rank",
                "scenario",
                "context",
            ]
        )
    save_dataframe(final_menu_export, OUTPUT_TABLES_DIR / MENU_SUGGESTIONS_OUTPUT)
    print(f"Menu suggestions kaydedildi: {OUTPUT_TABLES_DIR / MENU_SUGGESTIONS_OUTPUT}")

    print_section_title("OZET RAPOR")
    print(f"Veri dosyasi: {data_path}")
    print(f"Temizlenmis satir sayisi: {len(cleaned_df)}")
    print(f"Toplam transaction sayisi: {len(all_transactions)}")
    print(f"Analize dahil edilen cok urunlu transaction sayisi: {len(analysis_transactions)}")
    print(f"Toplam association rule sayisi: {len(rules_export)}")
    print(f"Toplam menu onerisi sayisi: {len(final_menu_export)}")
    if not args.skip_plots:
        print("Kaydedilen grafikler:")
        print(f" - {OUTPUT_FIGURES_DIR / PLOT_TOP_ITEMS}")
        print(f" - {OUTPUT_FIGURES_DIR / CATEGORY_PLOT}")
        print(f" - {OUTPUT_FIGURES_DIR / ORDER_SIZE_PLOT}")
        print(f" - {OUTPUT_FIGURES_DIR / PRICE_PLOT}")

    if not args.skip_interactive:
        interactive_cli(
            cleaned_df=cleaned_df,
            transactions=all_transactions,
            item_catalog=item_catalog,
            rules_df=rules_df,
            weights=weights,
            top_n=args.top_n,
            extra_items_count=args.extra_items,
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"[HATA] Program calisirken bir sorun olustu: {error}")
        sys.exit(1)
