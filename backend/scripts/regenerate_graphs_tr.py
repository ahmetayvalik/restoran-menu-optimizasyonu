#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager, rcParams
from matplotlib.font_manager import FontProperties


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ciktilar" / "gorseller"
OUT.mkdir(parents=True, exist_ok=True)


def set_font() -> str:
    # Tek stabil font dosyasına kilitle: fallback kaynaklı glyph/render çakışmalarını azalt.
    dv_path = Path(font_manager.findfont("DejaVu Sans"))
    candidates = ["DejaVu Sans", "Arial", "Liberation Sans", "Noto Sans"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((name for name in candidates if name in available), "DejaVu Sans")

    rcParams["font.family"] = "sans-serif"
    rcParams["font.sans-serif"] = [chosen, "DejaVu Sans", "Arial", "Liberation Sans"]
    rcParams["font.weight"] = "normal"
    rcParams["axes.unicode_minus"] = False
    rcParams["axes.titlesize"] = 16
    rcParams["axes.labelsize"] = 13
    rcParams["xtick.labelsize"] = 12
    rcParams["ytick.labelsize"] = 12
    rcParams["figure.dpi"] = 180
    rcParams["savefig.dpi"] = 520
    rcParams["text.antialiased"] = True
    rcParams["path.simplify"] = False
    rcParams["axes.linewidth"] = 0.9
    rcParams["lines.antialiased"] = True
    return str(dv_path if dv_path.exists() else font_manager.findfont(chosen))


def main() -> None:
    font_path = set_font()
    fp = FontProperties(fname=font_path)

    raw = pd.read_csv(ROOT / "veri" / "comprehensive-restaurant-orders-popular-items-high-value-transactions-patterns.csv", sep="|")
    clean = pd.read_csv(ROOT / "ciktilar" / "tablolar" / "cleaned_orders.csv")
    rules = pd.read_csv(ROOT / "ciktilar" / "tablolar" / "association_rules.csv")
    bayes = pd.read_csv(ROOT / "ciktilar" / "tablolar" / "bayes_kurallari.csv")
    menus = pd.read_csv(ROOT / "ciktilar" / "tablolar" / "menu_suggestions.csv")

    # Preprocessing: missing and duplicate comparison
    fig, ax = plt.subplots(1, 2, figsize=(11.6, 5.3))
    raw_missing = int(raw.isna().sum().sum())
    clean_missing = int(clean.isna().sum().sum())
    raw_dup = int(raw.duplicated().sum())
    clean_dup = int(clean.duplicated().sum())

    ax[0].bar(["Raw", "Clean"], [raw_missing, clean_missing], color=["#5f5f5f", "#9a9a9a"])
    ax[0].set_title("Preprocessing: Missing Value Comparison", fontproperties=fp)
    ax[0].set_ylabel("Total missing cells", fontproperties=fp)

    ax[1].bar(["Raw", "Clean"], [raw_dup, clean_dup], color=["#4f4f4f", "#8b8b8b"])
    ax[1].set_title("Preprocessing: Duplicate Row Comparison", fontproperties=fp)
    ax[1].set_ylabel("Duplicate row count", fontproperties=fp)

    plt.tight_layout()
    plt.savefig(OUT / "preprocess_etki_gri.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.06)
    plt.close()

    # Rule space
    fig, ax = plt.subplots(figsize=(11.6, 5.3))
    sc = ax.scatter(rules["confidence"], rules["lift"], c=rules["support"], cmap="cividis", s=58, alpha=0.92, edgecolors="#2f2f2f", linewidths=0.2)
    ax.set_title("Rule Space: Confidence - Lift - Support", fontproperties=fp)
    ax.set_xlabel("Confidence", fontproperties=fp)
    ax.set_ylabel("Lift", fontproperties=fp)
    cb = plt.colorbar(sc)
    cb.set_label("Support", fontproperties=fp)
    plt.tight_layout()
    plt.savefig(OUT / "kural_uzayi_scatter_gri.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.06)
    plt.close()

    # Bayes factor distribution
    fig, ax = plt.subplots(figsize=(11.6, 5.3))
    ax.hist(bayes["bayes_factor"], bins=8, color="#6b6b6b", edgecolor="black")
    ax.axvline(1.3, color="#1f1f1f", linestyle="--", linewidth=1.2)
    ax.axvline(1.8, color="#1f1f1f", linestyle=":", linewidth=1.2)
    ax.set_title("Bayes Factor Distribution", fontproperties=fp)
    ax.set_xlabel("Bayes factor", fontproperties=fp)
    ax.set_ylabel("Rule count", fontproperties=fp)
    plt.tight_layout()
    plt.savefig(OUT / "bayes_faktor_hist_gri.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.06)
    plt.close()

    # Menu score and price balance
    fig, ax = plt.subplots(figsize=(11.6, 5.3))
    sc2 = ax.scatter(menus["total_price"], menus["menu_score"], c=menus["avg_lift"], cmap="cividis", s=75, alpha=0.9, edgecolors="#2f2f2f", linewidths=0.2)
    ax.set_title("Menu Score and Price Balance", fontproperties=fp)
    ax.set_xlabel("Total price ($)", fontproperties=fp)
    ax.set_ylabel("Menu score", fontproperties=fp)
    cb2 = plt.colorbar(sc2)
    cb2.set_label("Average lift", fontproperties=fp)
    plt.tight_layout()
    plt.savefig(OUT / "menu_score_fiyat_gri.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.06)
    plt.close()

    # Monthly trend
    clean["order_date_parsed"] = pd.to_datetime(clean["order_date_parsed"])
    monthly = clean.groupby(clean["order_date_parsed"].dt.month)["order_id"].nunique().reindex([1, 2, 3])
    months = ["January", "February", "March"]

    fig, ax = plt.subplots(figsize=(11.6, 5.3))
    ax.plot(months, monthly.values, marker="o", linewidth=2.3, color="#444444")
    ax.fill_between(months, monthly.values, color="#bcbcbc", alpha=0.35)
    ax.set_title("Monthly Order Trend", fontproperties=fp)
    ax.set_ylabel("Unique order count", fontproperties=fp)
    plt.tight_layout()
    plt.savefig(OUT / "aylik_trend_gri.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.06)
    plt.close()

    # --- Mini supportive visuals (enlarged for readability) ---
    # 1) Support histogram mini
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.hist(rules["support"], bins=10, color="#6a6a6a", edgecolor="black")
    ax.set_title("Support Distribution", fontproperties=fp)
    ax.set_xlabel("Support", fontproperties=fp)
    ax.set_ylabel("Count", fontproperties=fp)
    plt.tight_layout()
    plt.savefig(OUT / "support_hist_mini.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    # 2) Confidence histogram mini
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.hist(rules["confidence"], bins=10, color="#707070", edgecolor="black")
    ax.set_title("Confidence Distribution", fontproperties=fp)
    ax.set_xlabel("Confidence", fontproperties=fp)
    ax.set_ylabel("Count", fontproperties=fp)
    plt.tight_layout()
    plt.savefig(OUT / "confidence_hist_mini.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    # 3) Lift histogram mini
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.hist(rules["lift"], bins=10, color="#5f5f5f", edgecolor="black")
    ax.set_title("Lift Distribution", fontproperties=fp)
    ax.set_xlabel("Lift", fontproperties=fp)
    ax.set_ylabel("Count", fontproperties=fp)
    plt.tight_layout()
    plt.savefig(OUT / "lift_hist_mini.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    # 4) Rule count summary mini (larger and more readable)
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    rule_total = len(rules)
    bayes_total = len(bayes)
    ax.bar(["Rules", "Bayes Rules"], [rule_total, bayes_total], color=["#666666", "#9b9b9b"])
    for idx, val in enumerate([rule_total, bayes_total]):
        ax.text(idx, val + max(1, val * 0.01), str(val), ha="center", va="bottom", fontsize=12, fontproperties=fp)
    ax.set_title("Rule Count Summary", fontproperties=fp, fontsize=20, pad=10)
    ax.set_ylabel("Count", fontproperties=fp, fontsize=14)
    ax.tick_params(axis="x", labelsize=12)
    ax.tick_params(axis="y", labelsize=12)
    plt.tight_layout()
    plt.savefig(OUT / "rule_count_summary_mini.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    # 5) Category order density mini (larger and clearer)
    cat_counts = clean.groupby("category")["order_id"].nunique().sort_values(ascending=False).head(6).sort_values()
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    cat_counts.plot(kind="barh", ax=ax, color="#767676")
    ax.set_title("Category Order Density", fontproperties=fp, fontsize=18, pad=8)
    ax.set_xlabel("Unique orders", fontproperties=fp)
    ax.set_ylabel("Category", fontproperties=fp)
    plt.tight_layout()
    plt.savefig(OUT / "category_density_mini.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    # 6) Monthly mini trend
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.plot(months, monthly.values, marker="o", linewidth=2.0, color="#505050")
    ax.fill_between(months, monthly.values, color="#bcbcbc", alpha=0.3)
    ax.set_title("Mini Monthly Trend", fontproperties=fp, fontsize=18, pad=8)
    ax.set_ylabel("Orders", fontproperties=fp)
    plt.tight_layout()
    plt.savefig(OUT / "monthly_trend_mini.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    # 7) Preprocessing pipeline diagram mini (larger)
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    ax.axis("off")
    boxes = [
        (0.03, 0.50, 0.23, 0.35, "Load"),
        (0.285, 0.50, 0.23, 0.35, "Clean"),
        (0.54, 0.50, 0.23, 0.35, "Transform"),
        (0.795, 0.50, 0.19, 0.35, "Transaction"),
    ]
    for x, y, w, h, label in boxes:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="#d9d9d9", edgecolor="#4f4f4f", linewidth=1.15))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=13.5, fontproperties=fp)
    for x1, x2 in [(0.26, 0.285), (0.515, 0.54), (0.77, 0.795)]:
        ax.annotate("", xy=(x2, 0.675), xytext=(x1, 0.675), arrowprops=dict(arrowstyle="->", color="#3f3f3f", lw=2.0))
    ax.set_title("Preprocessing Pipeline", fontproperties=fp, fontsize=22, pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "preprocess_pipeline_mini.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    # 8) Bayes flow diagram mini
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.axis("off")
    nodes = [
        (0.04, 0.52, 0.24, 0.33, "Prior P(B)"),
        (0.35, 0.52, 0.29, 0.33, "Posterior P(B|A)"),
        (0.71, 0.52, 0.25, 0.33, "Bayes Factor"),
    ]
    for x, y, w, h, label in nodes:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="#dfdfdf", edgecolor="#4f4f4f", linewidth=1.1))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=12.5, fontproperties=fp)
    for x1, x2 in [(0.28, 0.35), (0.64, 0.71)]:
        ax.annotate("", xy=(x2, 0.685), xytext=(x1, 0.685), arrowprops=dict(arrowstyle="->", color="#3f3f3f", lw=1.9))
    ax.set_title("Bayes Update Flow", fontproperties=fp, fontsize=20, pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "bayes_flow_mini.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    # 9) Data cleaning summary mini table (larger)
    fig, ax = plt.subplots(figsize=(10.2, 6.2))
    ax.axis("off")
    summary = [
        ["Step", "Status"],
        ["Column normalization", "Applied"],
        ["Type conversion", "Applied"],
        ["Missing handling", "Applied"],
        ["Dedup control", "Checked"],
        ["Time features", "Generated"],
    ]
    table = ax.table(cellText=summary, loc="center", cellLoc="center", colWidths=[0.66, 0.34])
    table.auto_set_font_size(False)
    table.set_fontsize(13)
    table.scale(1.42, 2.1)
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#cfd8e3")
            cell.set_text_props(fontproperties=fp, weight="bold")
        else:
            if c == 1 and r > 0 and summary[r][1] == "Applied":
                cell.set_facecolor("#dcefdc")
            elif c == 1 and r > 0 and summary[r][1] == "Checked":
                cell.set_facecolor("#e6ebf2")
            elif c == 1 and r > 0 and summary[r][1] == "Generated":
                cell.set_facecolor("#efe7d7")
            else:
                cell.set_facecolor("#f6f6f6" if r % 2 == 0 else "#ececec")
            cell.set_text_props(fontproperties=fp)
        cell.set_edgecolor("#666666")
        cell.set_linewidth(0.5)
    ax.set_title("Data Cleaning Summary", fontproperties=fp, fontsize=22, pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "cleaning_summary_mini.png", facecolor="white", transparent=False, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    print(f"Graphs regenerated. Font file: {font_path}")


if __name__ == "__main__":
    main()
