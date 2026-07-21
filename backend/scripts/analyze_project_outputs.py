#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mevcut proje ciktilarini akademik sunum ve savunma acisindan analiz eder.

Gerekli kutuphaneler:
    # pip install pandas numpy

Calistirma:
    # python analyze_project_outputs.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


CLEANED_PATH = "cleaned_orders.csv"
RULES_PATH = "association_rules.csv"
MENUS_PATH = "menu_suggestions.csv"


def print_title(title: str) -> None:
    print("\n" + "=" * 96)
    print(title)
    print("=" * 96)


def print_df(label: str, df: pd.DataFrame, max_rows: int = 10) -> None:
    print(f"\n{label}")
    if df.empty:
        print("  Kayit bulunamadi.")
        return
    print(df.head(max_rows).to_string(index=False))


def read_csv_or_fail(path: str) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dosya bulunamadi: {file_path.resolve()}")
    return pd.read_csv(file_path)


def normalize_rule_side(text: str) -> List[str]:
    return [part.strip() for part in str(text).split(",") if part.strip()]


def analyze_cleaned_orders(cleaned_df: pd.DataFrame) -> Dict[str, object]:
    required_cols = {"order_id", "item_name", "category", "price"}
    missing = required_cols - set(cleaned_df.columns)
    if missing:
        raise ValueError(f"cleaned_orders.csv icinde eksik kolon var: {sorted(missing)}")

    order_count = cleaned_df["order_id"].nunique()
    item_count = cleaned_df["item_name"].nunique()
    avg_items_per_order = (
        cleaned_df.groupby("order_id")["item_name"].nunique().mean()
        if order_count > 0
        else 0.0
    )
    top_items = (
        cleaned_df.groupby("item_name")["order_id"]
        .nunique()
        .sort_values(ascending=False)
        .reset_index(name="order_count")
        .head(10)
    )
    category_distribution = (
        cleaned_df.groupby("category")["item_name"]
        .count()
        .sort_values(ascending=False)
        .reset_index(name="row_count")
    )
    null_report = cleaned_df[["order_id", "item_name", "category", "price"]].isna().sum().reset_index()
    null_report.columns = ["column_name", "missing_count"]
    duplicate_rows = int(cleaned_df.duplicated().sum())

    return {
        "order_count": int(order_count),
        "item_count": int(item_count),
        "avg_items_per_order": float(avg_items_per_order),
        "top_items": top_items,
        "category_distribution": category_distribution,
        "null_report": null_report,
        "duplicate_rows": duplicate_rows,
    }


def find_strict_and_fallback_rules(rules_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    required_cols = {"antecedents", "consequents", "support", "confidence", "lift"}
    missing = required_cols - set(rules_df.columns)
    if missing:
        raise ValueError(f"association_rules.csv icinde eksik kolon var: {sorted(missing)}")

    strict_rules = rules_df[(rules_df["confidence"] >= 0.4) & (rules_df["lift"] > 1)].copy()
    strict_rules = strict_rules.sort_values(["confidence", "lift"], ascending=[False, False])

    fallback_rules = rules_df[(rules_df["confidence"] >= 0.2) & (rules_df["lift"] > 1)].copy()
    fallback_rules = fallback_rules.sort_values(
        ["confidence", "lift", "support"],
        ascending=[False, False, False],
    )
    return strict_rules, fallback_rules


def select_presentation_rules(rules_df: pd.DataFrame) -> pd.DataFrame:
    candidate_rules = rules_df.copy()
    candidate_rules["antecedent_len"] = candidate_rules["antecedents"].apply(lambda x: len(normalize_rule_side(x)))
    candidate_rules["consequent_len"] = candidate_rules["consequents"].apply(lambda x: len(normalize_rule_side(x)))
    candidate_rules = candidate_rules[
        (candidate_rules["lift"] > 1.15)
        & (candidate_rules["support"] >= 0.007)
        & (candidate_rules["antecedent_len"] == 1)
        & (candidate_rules["consequent_len"] == 1)
    ].copy()
    candidate_rules["presentation_score"] = (
        0.50 * candidate_rules["confidence"]
        + 0.35 * np.minimum(candidate_rules["lift"] / 2.5, 1.0)
        + 0.15 * np.minimum(candidate_rules["support"] / 0.03, 1.0)
    )
    candidate_rules = candidate_rules.sort_values(
        ["presentation_score", "confidence", "lift", "support"],
        ascending=False,
    )
    return candidate_rules.head(3).copy()


def identify_weak_rules(rules_df: pd.DataFrame) -> pd.DataFrame:
    weak_rules = rules_df[(rules_df["lift"] <= 1.02) | (rules_df["confidence"] < 0.10)].copy()
    weak_rules["weak_reason"] = np.where(
        weak_rules["lift"] <= 1.02,
        "Lift 1'e cok yakin, iliski zayif",
        "Confidence dusuk, tahmin gucu zayif",
    )
    weak_rules = weak_rules.sort_values(["lift", "confidence"], ascending=[True, True])
    return weak_rules.head(10).copy()


def explain_rule_selection(row: pd.Series, total_orders: int) -> str:
    estimated_joint_orders = int(round(float(row["support"]) * total_orders))
    return (
        f"{row['antecedents']} -> {row['consequents']} kurali; "
        f"confidence={row['confidence']:.3f}, lift={row['lift']:.3f}, "
        f"support={row['support']:.3f}. Yaklasik {estimated_joint_orders} sipariste birlikte goruluyor. "
        f"Hem yonlu bir iliski veriyor hem de lift>1 oldugu icin rasgele birliktelikten daha guclu."
    )


def analyze_menus(menus_df: pd.DataFrame) -> Dict[str, object]:
    required_cols = {
        "menu_items",
        "total_price",
        "avg_conditional_probability",
        "avg_lift",
        "category_diversity",
        "menu_score",
        "categories",
        "base_item",
    }
    missing = required_cols - set(menus_df.columns)
    if missing:
        raise ValueError(f"menu_suggestions.csv icinde eksik kolon var: {sorted(missing)}")

    parsed = menus_df.copy()
    parsed["item_list"] = parsed["menu_items"].apply(lambda x: [part.strip() for part in str(x).split("|")])
    parsed["category_list"] = parsed["categories"].apply(lambda x: [part.strip() for part in str(x).split("|")])
    parsed["category_repeat"] = parsed["category_list"].apply(lambda cats: len(set(cats)) < len(cats))
    parsed["item_repeat"] = parsed["item_list"].apply(lambda items: len(set(items)) < len(items))

    high_price_threshold = float(parsed["total_price"].quantile(0.75))
    parsed["price_flag"] = parsed["total_price"] > high_price_threshold
    parsed["quality_flag"] = np.where(
        parsed["avg_lift"] < 1,
        "Lift 1'in altinda, menu iliskisi zayif",
        np.where(parsed["category_repeat"], "Kategori tekrari var", "Genel olarak tutarli"),
    )

    best_menus = parsed[
        (~parsed["item_repeat"])
        & (~parsed["category_repeat"])
        & (parsed["avg_lift"] >= 1)
    ].copy()
    best_menus = best_menus.sort_values(
        ["menu_score", "avg_lift", "avg_conditional_probability"],
        ascending=False,
    )
    return {
        "parsed_menus": parsed,
        "best_menus": best_menus.head(3).copy(),
        "weak_menus": parsed[(parsed["avg_lift"] < 1) | (parsed["category_repeat"])].copy(),
        "high_price_threshold": high_price_threshold,
    }


def map_menu_to_supporting_rules(menu_row: pd.Series, rules_df: pd.DataFrame) -> pd.DataFrame:
    base_item = menu_row["base_item"]
    menu_items = [item.strip() for item in str(menu_row["menu_items"]).split("|")]
    extra_items = [item for item in menu_items if item != base_item]
    support_rows = []

    for extra_item in extra_items:
        direct = rules_df[
            (rules_df["antecedents"] == base_item) & (rules_df["consequents"] == extra_item)
        ].copy()
        reverse = rules_df[
            (rules_df["antecedents"] == extra_item) & (rules_df["consequents"] == base_item)
        ].copy()
        chosen = pd.concat([direct.assign(direction="direct"), reverse.assign(direction="reverse")], ignore_index=True)
        if chosen.empty:
            support_rows.append(
                {
                    "base_item": base_item,
                    "paired_item": extra_item,
                    "rule_found": "Yok",
                    "direction": "co_occurrence_only",
                    "confidence": np.nan,
                    "lift": np.nan,
                }
            )
        else:
            chosen = chosen.sort_values(["confidence", "lift"], ascending=False).iloc[0]
            support_rows.append(
                {
                    "base_item": base_item,
                    "paired_item": extra_item,
                    "rule_found": f"{chosen['antecedents']} -> {chosen['consequents']}",
                    "direction": chosen["direction"],
                    "confidence": float(chosen["confidence"]),
                    "lift": float(chosen["lift"]),
                }
            )

    return pd.DataFrame(support_rows)


def build_presentation_summary(clean_stats: Dict[str, object], rules_df: pd.DataFrame, menus_df: pd.DataFrame) -> Dict[str, str]:
    top_rule = rules_df.sort_values(["confidence", "lift"], ascending=[False, False]).iloc[0]
    top_menu = menus_df.sort_values("menu_score", ascending=False).iloc[0]
    summary = {
        "Problem Tanimi": (
            "Bu projede restoran siparis verilerindeki urun birliktelikleri analiz edilerek "
            "tek tek urun satisina odaklanmak yerine birlikte satin alma davranisi modellenmistir. "
            "Amac, siparis verisinden karar destek ureten ve otomatik menu kombinasyonlari olusturan bir sistem gelistirmektir."
        ),
        "Veri Seti Yapisi": (
            f"Calismada siparis satiri seviyesinde tutulan restoran verisi kullanilmistir. "
            f"Temizlenmis veri setinde {clean_stats['order_count']} benzersiz siparis ve "
            f"{clean_stats['item_count']} benzersiz urun yer almaktadir. Temel alanlar order_id, item_name, category ve price kolonlaridir."
        ),
        "Veri On Isleme": (
            "Veri yukleme asamasinda ayrac ve kolon isimleri esnek sekilde ele alinmis, bos ve bozuk kayitlar kontrol edilmis, "
            "kategori ve urun adlari normalize edilmistir. Ayrica siparisler transaction formatina donusturulerek Apriori icin uygun hale getirilmistir."
        ),
        "Kullanilan Yontemler": (
            "Bu proje supervised learning problemi olarak ele alinmamistir. Bunun yerine Apriori ile frequent itemset mining, "
            "association rules ile support-confidence-lift analizi ve ham transaction verisi uzerinden kosullu olasilik hesaplari kullanilmistir."
        ),
        "Elde Edilen Temel Bulgular": (
            f"Kurallar icinde en yuksek yonlu iliskilerden biri {top_rule['antecedents']} -> {top_rule['consequents']} seklindedir "
            f"(confidence={top_rule['confidence']:.3f}, lift={top_rule['lift']:.3f}). "
            "Bu sonuc belirli urunlerin birlikte alinma egiliminin rastgele dagilimdan daha guclu oldugunu gostermektedir."
        ),
        "Otomatik Menu Oneri Sistemi": (
            f"Menu onerileri yalnizca tek bir kurala degil, kosullu olasilik, lift, fiyat ve kategori cesitliligi birlikte kullanilarak uretilmistir. "
            f"Ornek olarak en yuksek skorlu menu onerilerinden biri {top_menu['menu_items']} kombinasyonudur."
        ),
        "Sonuc": (
            "Sonuc olarak sistem, siparis verisinden elde edilen birliktelik oruntulerini isletme tarafinda capraz satis, kampanya tasarimi "
            "ve veri destekli menu planlama amaclariyla kullanilabilir hale getirmistir. Dolayisiyla proje bir tahmin modeli degil, "
            "oruntu kesfi ve karar destek sistemi olarak degerlendirilmelidir."
        ),
    }
    return summary


def build_defense_answers() -> Dict[str, str]:
    return {
        "Bu urun iliskilerini neye gore cikardin?": (
            "Iliskileri transaction bazli siparis verisinden cikardim. Ayni order_id icinde birlikte gecen urunleri Apriori ve association rules ile analiz ettim; "
            "support, confidence ve lift metrikleri bu iliskilerin nicel temelini olusturdu."
        ),
        "Pizza yaninda kola alindigini nereden biliyorsun?": (
            "Bu tur bir iddia ancak veri setinde ilgili urunler varsa kurulabilir. Ben yorumlarimi sadece CSV sonucunda gercekten bulunan urunlere dayandirdim; "
            "birlikte alinma bilgisi ayni sipariste birlikte gorulme frekansindan geliyor."
        ),
        "Bunlari sen mi uydurdun?": (
            "Hayir. Kural ve menu onerileri dogrudan veri setinden uretilen support, confidence, lift ve kosullu olasilik hesaplarina dayaniyor. "
            "Sunumda kullanilacak her ornek association_rules.csv veya menu_suggestions.csv icinde mevcut."
        ),
        "Bu projede model egitimi var mi?": (
            "Klasik anlamda etiketli bir model egitimi yok. Bu calisma supervised learning degil; association rule mining ve probabilistic modeling temelli bir karar destek sistemi."
        ),
        "Neden bu veri setini sectin?": (
            "Bu veri seti siparis bazli urun birlikteliklerini gormeye uygun oldugu icin secildi. order_id, item_name, category ve price alanlari hem davranis analizi hem de menu tasarimi icin yeterli bilgiyi sagliyor."
        ),
        "Association rule ile recommendation system arasindaki iliski nedir?": (
            "Association rule, hangi urunlerin birlikte alinma egilimi gosterdigini ortaya koyar. Recommendation system ise bu bilgiyi kullanarak kullanici bir urun sectiginde onun yanina hangi urunlerin onerilecegine karar verir."
        ),
        "Lift degeri neden onemli?": (
            "Confidence tek basina yeterli degil; cunku populer urunler zaten sik gorunur. Lift, bir birlikteligin rasgele beklenen duzeyin ne kadar uzerinde oldugunu gosterir. Bu nedenle gercek iliski gucunu daha iyi ayirt eder."
        ),
        "Bu sistem gercek hayatta nasil kullanilabilir?": (
            "Restoran tarafinda kasa ekraninda tamamlayici urun onerisi, mobil siparis uygulamasinda otomatik combo olusturma, kampanya tasarimi ve stok planlama gibi alanlarda kullanilabilir."
        ),
    }


def build_demo_scenarios(best_menus: pd.DataFrame, rules_df: pd.DataFrame) -> List[Dict[str, str]]:
    demos = []
    for _, row in best_menus.head(3).iterrows():
        supporting_rules = map_menu_to_supporting_rules(row, rules_df)
        found_rules = supporting_rules[supporting_rules["rule_found"] != "Yok"]
        if not found_rules.empty:
            rule_text = "; ".join(found_rules["rule_found"].head(2).tolist())
        else:
            rule_text = "Bu menu daha cok kosullu olasilik ve birlikte gecme skorlarina dayaniyor."

        demos.append(
            {
                "Girdi urun": row["base_item"],
                "Sistem onerisi": row["menu_items"],
                "Arkasindaki kural": rule_text,
                "Kisa sozlu anlatim": (
                    f"Sistem {row['base_item']} secildiginde yalnizca tek bir urun degil, "
                    f"kategori cesitliligi ve fiyat dengesi de gozetilerek {row['menu_items']} kombinasyonunu oneriyor."
                ),
            }
        )
    return demos


def print_commentary_examples(
    clean_stats: Dict[str, object],
    strict_rules: pd.DataFrame,
    fallback_rules: pd.DataFrame,
    presentation_rules: pd.DataFrame,
    menu_analysis: Dict[str, object],
    total_orders: int,
) -> None:
    print_title("OTOMATIK YORUM")
    print(
        f"Temizlenmis veri setinde {clean_stats['order_count']} benzersiz siparis ve "
        f"{clean_stats['item_count']} benzersiz urun bulunuyor. "
        f"Ortalama siparis basi urun sayisi {clean_stats['avg_items_per_order']:.2f}."
    )

    if strict_rules.empty:
        print(
            "Belirlenen kati esik olan confidence >= 0.40 ve lift > 1 ile kural bulunamadi. "
            "Bu durum veri setinde urun iliskilerinin var oldugunu, ancak cok yuksek yonlu bagimliliklar olmadigini gosteriyor."
        )
        print(
            f"Bu nedenle sunum icin confidence >= 0.20 ve lift > 1 fallback mantigi ile {len(fallback_rules)} kural incelendi."
        )
    else:
        print(f"Kati esik ile {len(strict_rules)} kural elde edildi.")

    if not presentation_rules.empty:
        print("Sunuma en uygun kurallar:")
        for _, row in presentation_rules.iterrows():
            print(" - " + explain_rule_selection(row, total_orders))

    best_menus = menu_analysis["best_menus"]
    weak_menus = menu_analysis["weak_menus"]
    if not best_menus.empty:
        top_menu = best_menus.iloc[0]
        print(
            f"Menu onerileri icinde en dengeli sonuc {top_menu['menu_items']} kombinasyonudur. "
            f"Bu menu; skor={top_menu['menu_score']:.3f}, avg_lift={top_menu['avg_lift']:.3f}, "
            f"kategori cesitliligi={top_menu['category_diversity']:.2f} degerlerine sahiptir."
        )
    if not weak_menus.empty:
        print(
            "Bazi menu onerileri sunumda kullanilmamali; cunku ya lift 1'in altina dusuyor "
            "ya da ayni kategoriden tekrar iceriyor."
        )


def main() -> None:
    cleaned_df = read_csv_or_fail(CLEANED_PATH)
    rules_df = read_csv_or_fail(RULES_PATH)
    menus_df = read_csv_or_fail(MENUS_PATH)

    print_title("1. CLEANED_ORDERS ANALIZI")
    clean_stats = analyze_cleaned_orders(cleaned_df)
    print(f"Benzersiz order_id sayisi: {clean_stats['order_count']}")
    print(f"Benzersiz item_name sayisi: {clean_stats['item_count']}")
    print(f"Ortalama siparis basi urun sayisi: {clean_stats['avg_items_per_order']:.2f}")
    print(f"Tam satir duzeyinde duplicate kayit sayisi: {clean_stats['duplicate_rows']}")
    print_df("Ilk 10 urun", clean_stats["top_items"], max_rows=10)
    print_df("Kategori dagilimi", clean_stats["category_distribution"], max_rows=10)
    print_df("Eksik veri kontrolu", clean_stats["null_report"], max_rows=10)

    print_title("2. ASSOCIATION_RULES ANALIZI")
    strict_rules, fallback_rules = find_strict_and_fallback_rules(rules_df)
    print(f"Toplam rule sayisi: {len(rules_df)}")
    print(f"Confidence >= 0.40 ve lift > 1 kosulunu saglayan rule sayisi: {len(strict_rules)}")
    if strict_rules.empty:
        print(
            "Not: Bu esikle rule cikmadi. Bu nedenle akademik yorumda sunuma uygun fallback liste "
            "confidence >= 0.20 ve lift > 1 ile hazirlaniyor."
        )
    top_rules_to_show = strict_rules if not strict_rules.empty else fallback_rules
    print_df("En iyi 10 rule", top_rules_to_show[["antecedents", "consequents", "support", "confidence", "lift"]], max_rows=10)

    presentation_rules = select_presentation_rules(rules_df)
    print_df(
        "Sunuma uygun en iyi 3 rule",
        presentation_rules[["antecedents", "consequents", "support", "confidence", "lift", "presentation_score"]],
        max_rows=3,
    )
    for _, row in presentation_rules.iterrows():
        print(" - " + explain_rule_selection(row, clean_stats["order_count"]))

    weak_rules = identify_weak_rules(rules_df)
    print_df(
        "Zayif veya sunuma uygun olmayan rule ornekleri",
        weak_rules[["antecedents", "consequents", "support", "confidence", "lift", "weak_reason"]],
        max_rows=10,
    )

    print_title("3. MENU_SUGGESTIONS ANALIZI")
    menu_analysis = analyze_menus(menus_df)
    parsed_menus = menu_analysis["parsed_menus"]
    print(f"Toplam menu onerisi: {len(parsed_menus)}")
    print(f"Yuksek fiyat esigi (ust ceyrek): {menu_analysis['high_price_threshold']:.2f}")
    print_df(
        "Mantikli menu onerileri",
        menu_analysis["best_menus"][
            ["menu_items", "total_price", "avg_conditional_probability", "avg_lift", "category_diversity", "menu_score"]
        ],
        max_rows=3,
    )
    print_df(
        "Problemli menu onerileri",
        menu_analysis["weak_menus"][
            ["menu_items", "total_price", "avg_lift", "category_diversity", "quality_flag"]
        ],
        max_rows=10,
    )

    for _, menu_row in menu_analysis["best_menus"].iterrows():
        print(f"\nMenu degerlendirmesi: {menu_row['menu_items']}")
        print(
            f" - Neden mantikli: skor={menu_row['menu_score']:.3f}, avg_lift={menu_row['avg_lift']:.3f}, "
            f"fiyat={menu_row['total_price']:.2f}, kategori cesitliligi={menu_row['category_diversity']:.2f}"
        )
        supporting_rules = map_menu_to_supporting_rules(menu_row, rules_df)
        if supporting_rules.empty:
            print(" - Bu menu icin association rule bulunamadi.")
        else:
            print_df(" - Destekleyici kurallar", supporting_rules, max_rows=5)

    print_commentary_examples(
        clean_stats=clean_stats,
        strict_rules=strict_rules,
        fallback_rules=fallback_rules,
        presentation_rules=presentation_rules,
        menu_analysis=menu_analysis,
        total_orders=clean_stats["order_count"],
    )

    print_title("4. SUNUM OZETI")
    presentation_summary = build_presentation_summary(
        clean_stats=clean_stats,
        rules_df=top_rules_to_show if not top_rules_to_show.empty else rules_df,
        menus_df=parsed_menus,
    )
    for header, text in presentation_summary.items():
        print(f"\n{header}\n{text}")

    print_title("5. HOCAYA SAVUNMA CEVAPLARI")
    for question, answer in build_defense_answers().items():
        print(f"\nSoru: {question}\nCevap: {answer}")

    print_title("6. DEMO SENARYOLARI")
    demos = build_demo_scenarios(menu_analysis["best_menus"], rules_df)
    for index, demo in enumerate(demos, start=1):
        print(f"\nDemo {index}")
        for key, value in demo.items():
            print(f"{key}: {value}")

    print_title("7. IYILESTIRME ONERILERI")
    if strict_rules.empty:
        print(
            "- Mevcut veri setinde confidence >= 0.40 fazla kati kalmis. "
            "Sunuma daha dengeli kural cikarmak icin min_confidence degerini 0.20-0.25 araligina cekebilirsiniz."
        )
    print(
        "- min_support su an dusuk destekli ama anlamli kurallari yakaliyor. "
        "Daha stabil kurallar icin 0.007-0.010 araligini deneyebilirsiniz."
    )
    print(
        "- min_lift 1.0 yerine 1.10 kullanmak, rastgele birliktelige yakin kurallari temizleyerek sunum kalitesini artirir."
    )
    print(
        "- Menu skorlama tarafinda avg_lift < 1 olan menu adaylarini en basta elemek, "
        "aksam senaryolarindaki zayif kombinasyonlari otomatik disarida birakir."
    )
    print(
        "- Ayni kategoriden ikinci urun gelirse kategori cezasini biraz artirabilirsiniz; "
        "boylece Hamburger + French Fries gibi ayni kategori tekrarli menuler daha alt siraya iner."
    )


if __name__ == "__main__":
    main()
