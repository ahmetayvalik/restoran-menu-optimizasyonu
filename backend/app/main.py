from __future__ import annotations

import io
import logging
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mlxtend.frequent_patterns import apriori, association_rules

from backend.app.config import settings
from backend.app.schemas import (
    AnalysisSummary,
    BaselineComparison,
    BayesRule,
    FullResponse,
    MenuPackage,
    MonthlyMonthData,
    MonthlyTopRule,
    MonthlyTrend,
    MostConsistentCombination,
    TrendCombinationChange,
    TrendInsights,
)


APP_TITLE = "Cross-Sell Analysis API"
APP_VERSION = "1.3.0"
MAX_RESULTS = 3
REQUIRED_COLUMNS = {"order_id", "item_name"}
OPTIONAL_COLUMNS = {"order_time", "order_date", "category", "price"}
TIME_FILTERS = {
    "lunch": (12, 14),
    "afternoon": (15, 17),
    "dinner": (18, 21),
    "night": (22, 23),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("cross_sell_api")

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Restaurant order data analysis API for cross-sell recommendation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Any, exc: HTTPException) -> JSONResponse:
    logger.warning("HTTP error response | status=%s | detail=%s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_: Any, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Beklenmeyen bir hata olustu."},
    )


def load_csv_from_memory(file_bytes: bytes) -> pd.DataFrame:
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Yuklenen dosya bos.")

    try:
        dataframe = pd.read_csv(io.BytesIO(file_bytes), sep="|", encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            dataframe = pd.read_csv(io.BytesIO(file_bytes), sep="|", encoding="latin-1")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"CSV dosyasi okunamadi: {exc}") from exc
    except pd.errors.EmptyDataError as exc:
        raise HTTPException(
            status_code=400,
            detail="CSV dosyasi bos veya yalnizca baslik satiri iceriyor.",
        ) from exc
    except pd.errors.ParserError as exc:
        raise HTTPException(status_code=400, detail=f"CSV parse hatasi: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV dosyasi okunamadi: {exc}") from exc

    if dataframe.empty:
        raise HTTPException(status_code=400, detail="CSV dosyasi okunabildi ancak veri bos.")

    if len(dataframe.columns) == 1:
        try:
            fallback_df = pd.read_csv(io.BytesIO(file_bytes), sep=",", encoding="utf-8-sig")
            if len(fallback_df.columns) > 1:
                dataframe = fallback_df
        except Exception:
            logger.info("Comma fallback kullanilamadi, pipe parse sonucu korunuyor.")

    dataframe.columns = [str(column).strip().lower() for column in dataframe.columns]
    logger.info("CSV loaded | rows=%s | columns=%s", len(dataframe), len(dataframe.columns))
    return dataframe


def validate_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    missing_columns = REQUIRED_COLUMNS - set(dataframe.columns)
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail="Dosyada order_id ve item_name sutunlari bulunmalidir.",
        )
    return dataframe


def parse_optional_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()

    if "order_time" in dataframe.columns:
        dataframe["hour"] = pd.to_datetime(
            dataframe["order_time"],
            format="%I:%M:%S %p",
            errors="coerce",
        ).dt.hour

    if "order_date" in dataframe.columns:
        dataframe["order_date_parsed"] = pd.to_datetime(
            dataframe["order_date"],
            format="%m/%d/%y",
            errors="coerce",
        )
        dataframe["month"] = dataframe["order_date_parsed"].dt.month
        dataframe["dayofweek"] = dataframe["order_date_parsed"].dt.dayofweek

    if "price" in dataframe.columns:
        dataframe["price"] = pd.to_numeric(dataframe["price"], errors="coerce")

    logger.info(
        "Optional features parsed | available=%s",
        sorted(list(OPTIONAL_COLUMNS.intersection(dataframe.columns))),
    )
    return dataframe


def clean_order_rows(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned = dataframe.copy()
    cleaned["order_id"] = cleaned["order_id"].astype(str).str.strip()
    cleaned["item_name"] = cleaned["item_name"].astype(str).str.strip()
    cleaned = cleaned.replace({"order_id": {"": pd.NA}, "item_name": {"": pd.NA}})
    cleaned = cleaned.dropna(subset=["order_id", "item_name"]).copy()

    if cleaned.empty:
        raise HTTPException(status_code=400, detail="Gecerli order_id ve item_name verisi bulunamadi.")

    if cleaned["order_id"].nunique() < 2:
        raise HTTPException(status_code=400, detail="Analiz icin en az iki farkli siparis gereklidir.")

    return cleaned


def apply_category_filter(dataframe: pd.DataFrame, category_filter: str | None) -> pd.DataFrame:
    if category_filter is None:
        return dataframe

    if category_filter not in settings.allowed_category_filters:
        raise HTTPException(
            status_code=400,
            detail="Gecersiz kategori filtresi. Asian, Italian, Mexican veya American kullanin.",
        )

    if "category" not in dataframe.columns:
        raise HTTPException(
            status_code=400,
            detail="Kategori filtresi kullanmak icin veride category sutunu bulunmalidir.",
        )

    matching_order_ids = dataframe.loc[
        dataframe["category"].astype(str) == category_filter,
        "order_id",
    ].unique()
    filtered_df = dataframe[dataframe["order_id"].isin(matching_order_ids)].copy()
    filtered_order_count = int(filtered_df["order_id"].nunique()) if "order_id" in filtered_df.columns else 0

    if filtered_order_count < 100:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{category_filter} kategorisinde yeterli siparis yok "
                f"({filtered_order_count} siparis). Lutfen farkli bir kategori deneyin."
            ),
        )

    return filtered_df


def apply_time_filter(dataframe: pd.DataFrame, time_filter: str | None) -> pd.DataFrame:
    if time_filter is None:
        return dataframe

    if time_filter not in TIME_FILTERS:
        raise HTTPException(
            status_code=400,
            detail="Gecersiz zaman filtresi. lunch, afternoon, dinner veya night kullanin.",
        )

    if "hour" not in dataframe.columns:
        logger.warning("Time filter ignored | hour column unavailable")
        return dataframe

    start_hour, end_hour = TIME_FILTERS[time_filter]
    filtered_df = dataframe[dataframe["hour"].between(start_hour, end_hour)].copy()
    filtered_order_count = int(filtered_df["order_id"].nunique()) if "order_id" in filtered_df.columns else 0

    if filtered_order_count < 50:
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{time_filter}' zaman diliminde yeterli siparis yok "
                f"({filtered_order_count} siparis). Sabah verisi bu datasette "
                "cok az, lutfen ogle/aksam deneyin."
            ),
        )

    return filtered_df


def prepare_transaction_matrix(cleaned_rows: pd.DataFrame) -> pd.DataFrame:
    basket = (
        cleaned_rows.assign(value=1)
        .pivot_table(
            index="order_id",
            columns="item_name",
            values="value",
            aggfunc="max",
            fill_value=0,
        )
        .astype(bool)
    )

    if basket.empty or basket.shape[1] < 2:
        raise HTTPException(status_code=400, detail="Analiz icin yeterli urun cesitliligi bulunamadi.")

    return basket


def run_apriori_analysis(transaction_matrix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frequent_itemsets = apriori(
        transaction_matrix,
        min_support=settings.min_support,
        use_colnames=True,
    )

    if frequent_itemsets.empty:
        raise HTTPException(status_code=400, detail="Bu veri setinde anlamli capraz satis kombinasyonu bulunamadi.")

    freq_items_df = frequent_itemsets[frequent_itemsets["itemsets"].apply(len).eq(1)].copy()
    freq_items_df["item_name"] = freq_items_df["itemsets"].apply(lambda values: next(iter(values)))
    freq_items_df = freq_items_df[["item_name", "support"]].reset_index(drop=True)

    rules_df = association_rules(
        frequent_itemsets,
        metric="lift",
        min_threshold=settings.min_lift,
    )

    if rules_df.empty:
        raise HTTPException(status_code=400, detail="Bu veri setinde anlamli capraz satis kombinasyonu bulunamadi.")

    rules_df = rules_df[
        rules_df["antecedents"].apply(len).eq(1)
        & rules_df["consequents"].apply(len).eq(1)
    ].copy()
    if rules_df.empty:
        raise HTTPException(status_code=400, detail="Bu veri setinde tek urun bazli anlamli capraz satis kurali bulunamadi.")

    rules_df["antecedent"] = rules_df["antecedents"].apply(lambda values: next(iter(values)))
    rules_df["consequent"] = rules_df["consequents"].apply(lambda values: next(iter(values)))
    rules_df = rules_df[["antecedent", "consequent", "support", "confidence", "lift"]].copy()
    rules_df = rules_df.sort_values(["lift", "confidence", "support"], ascending=[False, False, False]).reset_index(drop=True)
    return rules_df, freq_items_df


def deduplicate_bidirectional_rules(rules_df: pd.DataFrame) -> pd.DataFrame:
    if rules_df.empty:
        return rules_df

    dedup_source = rules_df.copy()
    dedup_source["pair_key"] = dedup_source.apply(
        lambda row: tuple(sorted([str(row["antecedent"]), str(row["consequent"])])),
        axis=1,
    )
    dedup_source = dedup_source.sort_values(
        ["lift", "confidence", "support"],
        ascending=[False, False, False],
    )
    return dedup_source.drop_duplicates(subset=["pair_key"], keep="first").drop(columns=["pair_key"]).reset_index(drop=True)


def calculate_bayes_metrics(rules_df: pd.DataFrame, freq_items_df: pd.DataFrame) -> pd.DataFrame:
    if rules_df.empty:
        raise HTTPException(status_code=400, detail="Bu veri setinde anlamli capraz satis kombinasyonu bulunamadi.")

    support_map = freq_items_df.set_index("item_name")["support"].to_dict()
    bayes_rows: list[dict[str, Any]] = []

    for _, row in rules_df.iterrows():
        consequent = str(row["consequent"])
        prior_b = float(support_map.get(consequent, 0.0))
        posterior_b_given_a = float(row["confidence"])

        if prior_b <= 0:
            continue

        bayes_factor = posterior_b_given_a / prior_b
        belief_update_pct = ((posterior_b_given_a - prior_b) / prior_b) * 100

        if bayes_factor > 1.8:
            interpretation = "Guclu Bayes kaniti"
        elif bayes_factor >= 1.3:
            interpretation = "Orta Bayes kaniti"
        else:
            interpretation = "Zayif Bayes kaniti"

        bayes_rows.append(
            {
                "antecedent": str(row["antecedent"]),
                "consequent": consequent,
                "prior_probability": round(prior_b, 4),
                "posterior_probability": round(posterior_b_given_a, 4),
                "bayes_factor": round(bayes_factor, 4),
                "belief_update_pct": round(belief_update_pct, 2),
                "interpretation": interpretation,
                "support": round(float(row["support"]), 4),
            }
        )

    bayes_rules_df = pd.DataFrame(bayes_rows)
    if bayes_rules_df.empty:
        raise HTTPException(status_code=400, detail="Bu veri setinde Bayes metrikleri hesaplanabilecek kural bulunamadi.")

    return bayes_rules_df.sort_values(
        ["bayes_factor", "posterior_probability", "support"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def generate_menu_packages(
    bayes_rules_df: pd.DataFrame,
    price_map: dict[str, float],
    category_map: dict[str, str],
) -> list[MenuPackage]:
    packages: list[MenuPackage] = []

    for _, row in bayes_rules_df.head(MAX_RESULTS).iterrows():
        antecedent = str(row["antecedent"])
        consequent = str(row["consequent"])
        bayes_factor = float(row["bayes_factor"])
        posterior = float(row["posterior_probability"])
        interpretation = str(row["interpretation"])
        antecedent_category = category_map.get(antecedent, "Unknown")
        consequent_category = category_map.get(consequent, "Unknown")
        package_total_price = round(float(price_map.get(antecedent, 0.0)) + float(price_map.get(consequent, 0.0)), 2)

        if bayes_factor > 1.8:
            package_name = f"Sef'in {antecedent} Kombinasyonu"
        elif bayes_factor >= 1.3:
            package_name = f"{antecedent} & {consequent} Ozel Menusu"
        else:
            package_name = f"{consequent} ile {antecedent} Menusu"

        if bayes_factor > 1.5:
            suggested_price_strategy = (
                "Kombine fiyat onerilir - musteri zaten aliyor. "
                f"Paket fiyati: ${package_total_price:.2f}"
            )
        elif bayes_factor >= 1.2:
            suggested_price_strategy = (
                "Indirimli paket deneyin. "
                f"Onerilen paket fiyati: ${package_total_price * 0.9:.2f} (%10 indirim)"
            )
        else:
            suggested_price_strategy = "Ayri fiyatlandirin - zorlama paket olusturmayin."

        packages.append(
            MenuPackage(
                package_name=package_name,
                items=[antecedent, consequent],
                antecedent_category=antecedent_category,
                consequent_category=consequent_category,
                is_cross_category=antecedent_category != consequent_category,
                package_description=(
                    f"{antecedent} tercih eden musterilerin %{posterior * 100:.0f}'i "
                    f"{consequent} de siparis ediyor. Bu kombinasyon ortalamadan "
                    f"{bayes_factor:.1f}x daha sik goruluyor. {interpretation}"
                ),
                package_total_price=package_total_price,
                suggested_price_strategy=suggested_price_strategy,
                price_opportunity_score=round(package_total_price * bayes_factor, 2),
                confidence=round(posterior, 4),
                bayes_factor=round(bayes_factor, 4),
            )
        )

    return packages


def generate_baseline(dataframe: pd.DataFrame, bayes_rules_df: pd.DataFrame) -> BaselineComparison:
    top_popular_items = (
        dataframe.groupby("item_name")["order_id"]
        .nunique()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )
    top_item = top_popular_items[0] if top_popular_items else "urun"
    max_bf = float(bayes_rules_df["bayes_factor"].max()) if not bayes_rules_df.empty else 1.0

    return BaselineComparison(
        top_popular_items=top_popular_items,
        bayes_approach_advantage=(
            f"Geleneksel yontem herkese {top_item}'i onerirken, Bayes sistemi "
            f"siparis baglamina gore kisilestirilmis oneri uretiyor. En guclu "
            f"Bayes kaniti: {max_bf:.1f}x"
        ),
    )


def empty_monthly_trend() -> MonthlyTrend:
    return MonthlyTrend(
        months={
            "1": MonthlyMonthData(month_name="Ocak", order_count=0, top_rules=[]),
            "2": MonthlyMonthData(month_name="Subat", order_count=0, top_rules=[]),
            "3": MonthlyMonthData(month_name="Mart", order_count=0, top_rules=[]),
        },
        trend_insights=TrendInsights(
            rising_combinations=[],
            falling_combinations=[],
            new_in_march=[],
            disappeared_in_march=[],
            most_consistent=None,
        ),
    )


def run_month_rules(month_df: pd.DataFrame) -> pd.DataFrame:
    if month_df.empty or month_df["order_id"].nunique() < 2 or month_df["item_name"].nunique() < 2:
        return pd.DataFrame()

    try:
        month_matrix = prepare_transaction_matrix(month_df)
        month_rules_df, month_freq_items_df = run_apriori_analysis(month_matrix)
        month_rules_df = deduplicate_bidirectional_rules(month_rules_df)
        return calculate_bayes_metrics(month_rules_df, month_freq_items_df)
    except HTTPException:
        return pd.DataFrame()


def run_monthly_analysis(dataframe: pd.DataFrame) -> MonthlyTrend:
    if "month" not in dataframe.columns:
        return empty_monthly_trend()

    month_names = {1: "Ocak", 2: "Subat", 3: "Mart"}
    months_payload: dict[str, MonthlyMonthData] = {}
    monthly_rule_frames: dict[int, pd.DataFrame] = {}

    for month_number in (1, 2, 3):
        month_df = dataframe[dataframe["month"] == month_number].copy()
        bayes_month_df = run_month_rules(month_df)
        monthly_rule_frames[month_number] = bayes_month_df
        months_payload[str(month_number)] = MonthlyMonthData(
            month_name=month_names[month_number],
            order_count=int(month_df["order_id"].nunique()) if not month_df.empty else 0,
            top_rules=[
                MonthlyTopRule(
                    antecedent=str(row["antecedent"]),
                    consequent=str(row["consequent"]),
                    bayes_factor=float(row["bayes_factor"]),
                    confidence=float(row["posterior_probability"]),
                )
                for _, row in bayes_month_df.head(MAX_RESULTS).iterrows()
            ],
        )

    jan_map = {
        (str(row["antecedent"]), str(row["consequent"])): float(row["bayes_factor"])
        for _, row in monthly_rule_frames.get(1, pd.DataFrame()).iterrows()
    }
    feb_map = {
        (str(row["antecedent"]), str(row["consequent"])): float(row["bayes_factor"])
        for _, row in monthly_rule_frames.get(2, pd.DataFrame()).iterrows()
    }
    mar_map = {
        (str(row["antecedent"]), str(row["consequent"])): float(row["bayes_factor"])
        for _, row in monthly_rule_frames.get(3, pd.DataFrame()).iterrows()
    }

    rising: list[TrendCombinationChange] = []
    falling: list[TrendCombinationChange] = []
    for pair in sorted(set(jan_map).intersection(mar_map)):
        jan_factor = jan_map[pair]
        mar_factor = mar_map[pair]
        if jan_factor <= 0:
            continue
        change_pct = ((mar_factor - jan_factor) / jan_factor) * 100
        payload = TrendCombinationChange(
            antecedent=pair[0],
            consequent=pair[1],
            jan_factor=round(jan_factor, 4),
            mar_factor=round(mar_factor, 4),
            change_pct=round(change_pct, 2),
        )
        if change_pct > 10:
            rising.append(payload)
        elif change_pct < -10:
            falling.append(payload)

    consistent_pairs = set(jan_map).intersection(set(feb_map)).intersection(set(mar_map))
    most_consistent = None
    if consistent_pairs:
        best_pair = max(
            consistent_pairs,
            key=lambda pair: (jan_map[pair] + feb_map[pair] + mar_map[pair]) / 3,
        )
        most_consistent = MostConsistentCombination(
            antecedent=best_pair[0],
            consequent=best_pair[1],
            avg_bayes_factor=round((jan_map[best_pair] + feb_map[best_pair] + mar_map[best_pair]) / 3, 4),
        )

    return MonthlyTrend(
        months=months_payload,
        trend_insights=TrendInsights(
            rising_combinations=sorted(rising, key=lambda item: item.change_pct, reverse=True)[:MAX_RESULTS],
            falling_combinations=sorted(falling, key=lambda item: item.change_pct)[:MAX_RESULTS],
            new_in_march=[f"{pair[0]} -> {pair[1]}" for pair in sorted(set(mar_map) - set(jan_map))][:MAX_RESULTS],
            disappeared_in_march=[f"{pair[0]} -> {pair[1]}" for pair in sorted(set(jan_map) - set(mar_map))][:MAX_RESULTS],
            most_consistent=most_consistent,
        ),
    )


def build_analysis_summary(
    dataframe: pd.DataFrame,
    bayes_rules_df: pd.DataFrame,
    packages: list[MenuPackage],
    active_category_filter: str | None,
    active_time_filter: str | None,
    total_order_count: int,
) -> AnalysisSummary:
    date_range = "Tarih bilgisi yok"
    if "order_date_parsed" in dataframe.columns:
        valid_dates = dataframe["order_date_parsed"].dropna()
        if not valid_dates.empty:
            min_date = valid_dates.min()
            max_date = valid_dates.max()
            date_range = f"{min_date.month}/{min_date.day}/{str(min_date.year)[-2:]} -> {max_date.month}/{max_date.day}/{str(max_date.year)[-2:]}"

    analyzed_order_count = int(dataframe["order_id"].nunique())
    categories_available = []
    if "category" in dataframe.columns:
        categories_available = sorted(dataframe["category"].dropna().astype(str).unique().tolist())

    return AnalysisSummary(
        total_orders=analyzed_order_count,
        unique_items=int(dataframe["item_name"].nunique()),
        rules_found=int(len(bayes_rules_df)),
        packages_generated=len(packages),
        date_range=date_range,
        categories_available=categories_available,
        active_category_filter=active_category_filter,
        filtered_order_count=analyzed_order_count,
        active_time_filter=active_time_filter,
        time_filter_order_count=analyzed_order_count if active_time_filter else 0,
        time_filter_coverage_pct=round((analyzed_order_count / total_order_count) * 100, 2)
        if active_time_filter and total_order_count > 0
        else 0.0,
    )


def build_success_response(
    dataframe: pd.DataFrame,
    bayes_rules_df: pd.DataFrame,
    active_category_filter: str | None,
    active_time_filter: str | None,
    total_order_count: int,
) -> FullResponse:
    category_map: dict[str, str] = {}
    if "category" in dataframe.columns:
        category_map = (
            dataframe.dropna(subset=["item_name", "category"])
            .groupby("item_name")["category"]
            .first()
            .astype(str)
            .to_dict()
        )

    price_map: dict[str, float] = {}
    if "price" in dataframe.columns:
        price_series = dataframe.dropna(subset=["item_name", "price"]).groupby("item_name")["price"].mean()
        price_map = {item: round(float(price), 2) for item, price in price_series.to_dict().items()}

    selected_bayes_rules = bayes_rules_df.head(MAX_RESULTS).copy()
    bayes_rules = [
        BayesRule(
            antecedent=row["antecedent"],
            consequent=row["consequent"],
            antecedent_category=category_map.get(row["antecedent"], "Unknown"),
            consequent_category=category_map.get(row["consequent"], "Unknown"),
            prior_probability=float(row["prior_probability"]),
            posterior_probability=float(row["posterior_probability"]),
            bayes_factor=float(row["bayes_factor"]),
            belief_update_pct=float(row["belief_update_pct"]),
            interpretation=row["interpretation"],
            support=float(row["support"]),
        )
        for _, row in selected_bayes_rules.iterrows()
    ]

    menu_packages = generate_menu_packages(selected_bayes_rules, price_map, category_map)
    return FullResponse(
        status="success",
        analysis_summary=build_analysis_summary(
            dataframe,
            bayes_rules_df,
            menu_packages,
            active_category_filter,
            active_time_filter,
            total_order_count,
        ),
        bayes_rules=bayes_rules,
        menu_packages=menu_packages,
        baseline_comparison=generate_baseline(dataframe, bayes_rules_df),
        monthly_trend=run_monthly_analysis(dataframe),
    )


@app.get("/health")
async def health_check() -> dict[str, Any]:
    return {"status": "ok", "service": settings.service_name, "port": settings.service_port}


@app.post("/upload-and-analyze", response_model=FullResponse)
async def upload_and_analyze(
    file: UploadFile = File(...),
    category_filter: str | None = Query(default=None),
    time_filter: str | None = Query(default=None),
) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya adi alinamadi.")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Lutfen CSV formatinda bir dosya yukleyin.")

    try:
        file_bytes = await file.read()
        dataframe = load_csv_from_memory(file_bytes)
        dataframe = validate_columns(dataframe)
        dataframe = parse_optional_features(dataframe)
        total_order_count = int(dataframe["order_id"].nunique())
        dataframe = apply_category_filter(dataframe, category_filter)
        dataframe = apply_time_filter(dataframe, time_filter)
        cleaned_rows = clean_order_rows(dataframe)
        transaction_matrix = prepare_transaction_matrix(cleaned_rows)
        rules_df, freq_items_df = run_apriori_analysis(transaction_matrix)
        rules_df = deduplicate_bidirectional_rules(rules_df)
        bayes_rules_df = calculate_bayes_metrics(rules_df, freq_items_df)
        response_payload = build_success_response(
            cleaned_rows,
            bayes_rules_df,
            category_filter,
            time_filter,
            total_order_count,
        )
        return JSONResponse(status_code=200, content=response_payload.model_dump())
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected analysis failure")
        raise HTTPException(status_code=500, detail=f"Analiz islemi basarisiz oldu: {exc}") from exc
