#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "dokuman" / "Restoran_Menu_Analizi_Booklet_Raporu.pdf"
TABLO_DIR = ROOT / "ciktilar" / "tablolar"
GRAFIK_DIR = ROOT / "ciktilar" / "gorseller"
HAM_VERI = ROOT / "veri" / "comprehensive-restaurant-orders-popular-items-high-value-transactions-patterns.csv"

IMG = {
    "pre": GRAFIK_DIR / "preprocess_etki_gri.png",
    "rules": GRAFIK_DIR / "kural_uzayi_scatter_gri.png",
    "bayes": GRAFIK_DIR / "bayes_faktor_hist_gri.png",
    "menu": GRAFIK_DIR / "menu_score_fiyat_gri.png",
    "trend": GRAFIK_DIR / "aylik_trend_gri.png",
    "support_mini": GRAFIK_DIR / "support_hist_mini.png",
    "confidence_mini": GRAFIK_DIR / "confidence_hist_mini.png",
    "lift_mini": GRAFIK_DIR / "lift_hist_mini.png",
    "rule_count_mini": GRAFIK_DIR / "rule_count_summary_mini.png",
    "category_mini": GRAFIK_DIR / "category_density_mini.png",
    "monthly_mini": GRAFIK_DIR / "monthly_trend_mini.png",
    "pipeline_mini": GRAFIK_DIR / "preprocess_pipeline_mini.png",
    "bayes_flow_mini": GRAFIK_DIR / "bayes_flow_mini.png",
    "cleaning_mini": GRAFIK_DIR / "cleaning_summary_mini.png",
}


@dataclass
class Panel:
    x: float
    y: float
    w: float
    h: float
    no: int
    title: str


def load_fonts() -> tuple[str, str]:
    # Türkçe glyph ve metin ölçüm kararlılığı için önce DejaVu Sans, yoksa Arial kullan.
    n_path = Path(font_manager.findfont("DejaVu Sans"))
    try:
        b_path = Path(font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold")))
    except Exception:
        b_path = n_path

    if (not n_path.exists()) or (not b_path.exists()):
        arial_n = Path("C:/Windows/Fonts/arial.ttf")
        arial_b = Path("C:/Windows/Fonts/arialbd.ttf")
        if arial_n.exists() and arial_b.exists():
            n_path, b_path = arial_n, arial_b

    if not n_path.exists():
        raise RuntimeError("Türkçe karakter destekli font dosyası bulunamadı.")

    pdfmetrics.registerFont(TTFont("TRRegular", str(n_path)))
    if b_path.exists():
        pdfmetrics.registerFont(TTFont("TRBold", str(b_path)))
    else:
        pdfmetrics.registerFont(TTFont("TRBold", str(n_path)))
    return "TRRegular", "TRBold"


def tr_int(v: int | float) -> str:
    return f"{int(v):,}".replace(",", ".")


def split_lines(text: str, font: str, size: float, width: float) -> list[str]:
    return simpleSplit(text, font, size, width)


def draw_table(c: canvas.Canvas, data: Sequence[Sequence[object]], x: float, y: float, w: float, h: float, regular: str, bold: str, fs: int = 7) -> None:
    table = Table(data, colWidths=[w / len(data[0])] * len(data[0]), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), bold),
                ("FONTNAME", (0, 1), (-1, -1), regular),
                ("FONTSIZE", (0, 0), (-1, -1), fs),
                ("FONTSIZE", (0, 0), (-1, 0), fs + 1),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9A9A9A")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDDDDD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    table.wrapOn(c, w, h)
    table.drawOn(c, x, y)


def draw_image(c: canvas.Canvas, path: Path, x: float, y: float, w: float, h: float) -> None:
    if not path.exists():
        c.setStrokeColor(colors.HexColor("#9A9A9A"))
        c.setFillColor(colors.HexColor("#F7F7F7"))
        c.rect(x, y, w, h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#555555"))
        c.setFont("Helvetica", 9)
        c.drawCentredString(x + w / 2, y + h / 2, f"Görsel bulunamadı: {path.name}")
        return
    img = ImageReader(str(path))
    iw, ih = img.getSize()
    ratio = min(w / iw, h / ih)
    dw, dh = iw * ratio, ih * ratio
    dx = x + (w - dw) / 2
    dy = y + (h - dh) / 2
    c.drawImage(img, dx, dy, width=dw, height=dh, preserveAspectRatio=True, mask="auto")


class PanelFlow:
    def __init__(self, c: canvas.Canvas, x: float, y_top: float, width: float, y_bottom: float, regular: str, bold: str) -> None:
        self.c = c
        self.x = x
        self.y = y_top
        self.w = width
        self.bottom = y_bottom
        self.regular = regular
        self.bold = bold

    def space(self, amount: float) -> None:
        self.y -= amount

    def _can_fit(self, height: float) -> bool:
        return self.y - height >= self.bottom + 1

    def add_paragraph(self, text: str, size: float = 8.35, leading: float = 1.30, bold: bool = False, after: float = 4.5) -> bool:
        font = self.bold if bold else self.regular
        lines = split_lines(text, font, size, self.w)
        # ReportLab ölçüm farkları için güvenli sağ tampon bırak.
        while lines and max(pdfmetrics.stringWidth(line, font, size) for line in lines) > (self.w - 6):
            size2 = size - 0.15
            if size2 < 7.75:
                break
            size = size2
            lines = split_lines(text, font, size, self.w - 1.5)
        h = len(lines) * size * leading
        if not self._can_fit(h):
            # küçük shrink ile bir kez daha dene
            size2 = max(7.8, size - 0.30)
            lines = split_lines(text, font, size2, self.w - 1.5)
            h = len(lines) * size2 * leading
            if not self._can_fit(h):
                return False
            size = size2
        self.c.setFont(font, size)
        self.c.setFillColor(colors.HexColor("#111111"))
        step = size * leading
        y = self.y
        for line in lines:
            self.c.drawString(self.x, y, line)
            y -= step
        self.y = y - after
        return True

    def add_subtitle(self, text: str) -> bool:
        ok = self.add_paragraph(text, size=9.15, leading=1.2, bold=True, after=5)
        return ok

    def add_bullets(self, items: Iterable[str], size: float = 8.10, leading: float = 1.24, after: float = 4.5) -> bool:
        estimate = 0
        for item in items:
            lines = split_lines(item, self.regular, size, self.w - 16)
            estimate += max(1, len(lines)) * size * leading + 2
        if not self._can_fit(estimate):
            size2 = max(7.75, size - 0.25)
            estimate2 = 0
            for item in items:
                lines = split_lines(item, self.regular, size2, self.w - 16)
                estimate2 += max(1, len(lines)) * size2 * leading + 2
            if not self._can_fit(estimate2):
                return False
            size = size2
        y = self.y
        self.c.setFillColor(colors.HexColor("#111111"))
        for item in items:
            lines = split_lines(item, self.regular, size, self.w - 16)
            if not lines:
                continue
            while lines and max(pdfmetrics.stringWidth(line, self.regular, size) for line in lines) > (self.w - 18):
                size2 = size - 0.1
                if size2 < 7.7:
                    break
                size = size2
                lines = split_lines(item, self.regular, size, self.w - 17)
            self.c.setFont(self.regular, size)
            self.c.drawString(self.x, y, "•")
            self.c.drawString(self.x + 10, y, lines[0])
            y -= size * leading
            for line in lines[1:]:
                self.c.drawString(self.x + 10, y, line)
                y -= size * leading
            y -= 2
        self.y = y - after
        return True

    def add_image(self, path: Path, height: float = 108, after: float = 6) -> bool:
        if not self._can_fit(height):
            return False
        draw_image(self.c, path, self.x, self.y - height, self.w, height)
        self.y -= height + after
        return True

    def fill_with_tail(self, text_blocks: list[str]) -> None:
        for t in text_blocks:
            if self.y <= self.bottom + 26:
                break
            ok = self.add_paragraph(t, size=8.0, leading=1.24, bold=False, after=4)
            if not ok:
                break

    def add_mini_support(self, image_path: Path, caption: str, image_h: float = 82, before: float = 5) -> bool:
        if before > 0 and self._can_fit(before):
            self.space(before)
        heights = [image_h, image_h * 0.88, image_h * 0.76]
        placed = False
        for h in heights:
            if self.add_image(image_path, height=h, after=4):
                placed = True
                break
        if not placed:
            return False
        self.add_paragraph(caption, size=8.05, leading=1.23, bold=False, after=4)
        return True


def panel_frame(c: canvas.Canvas, p: Panel, regular: str, bold: str) -> tuple[float, float, float, float]:
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#6E6E6E"))
    c.setLineWidth(0.9)
    c.rect(p.x, p.y, p.w, p.h, fill=1, stroke=1)

    header_h = 24
    c.setFillColor(colors.HexColor("#DEDEDE"))
    c.rect(p.x, p.y + p.h - header_h, p.w, header_h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#111111"))
    c.setFont(bold, 10)
    c.drawString(p.x + 8, p.y + p.h - 16, p.title)

    footer_h = 16
    c.setFillColor(colors.HexColor("#EEEEEE"))
    c.rect(p.x, p.y, p.w, footer_h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#333333"))
    c.setFont(regular, 8)
    c.drawCentredString(p.x + p.w / 2, p.y + 4, f"Sayfa {p.no}")

    cx = p.x + 14
    cy_top = p.y + p.h - header_h - 9
    cw = p.w - 34
    cy_bottom = p.y + footer_h + 8
    return cx, cy_top, cw, cy_bottom


def pair(page_w: float, page_h: float, lno: int, rno: int, lt: str, rt: str) -> tuple[Panel, Panel]:
    m, g = 14, 10
    w = (page_w - 2 * m - g) / 2
    h = page_h - 2 * m
    return Panel(m, m, w, h, lno, lt), Panel(m + w + g, m, w, h, rno, rt)


def draw_cover(c: canvas.Canvas, w: float, h: float, regular: str, bold: str) -> None:
    c.setFillColor(colors.white)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#4D4D4D"))
    c.setLineWidth(1.4)
    c.rect(24, 24, w - 48, h - 48, fill=0, stroke=1)

    c.setFillColor(colors.HexColor("#E5E5E5"))
    c.rect(24, h - 118, w - 48, 94, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#111111"))
    c.setFont(bold, 24)
    c.drawString(42, h - 64, "Bayes Tabanlı Restoran Menü Analizi")

    c.setFont(bold, 13)
    c.drawString(42, h - 156, "Ad Soyad")
    c.setFont(regular, 13)
    c.drawString(188, h - 156, ": Ahmet Ayvalık")
    c.setFont(bold, 13)
    c.drawString(42, h - 182, "Öğrenci Numarası")
    c.setFont(regular, 13)
    c.drawString(188, h - 182, ": 230212041")
    c.setFont(bold, 13)
    c.drawString(42, h - 208, "Ders Adı")
    c.setFont(regular, 13)
    c.drawString(188, h - 208, ": Üretken Yapay Zeka")
    c.setFont(bold, 13)
    c.drawString(42, h - 234, "Proje Başlığı")
    c.setFont(regular, 13)
    c.drawString(188, h - 234, "Restoran Sipariş Verisinde Bayes Tabanlı Karar Destek Sistemi")

    c.setFont(bold, 13)
    c.drawString(42, h - 274, "Kısa Özet")
    summary = (
        "Bu çalışma, notebook ve proje kod tabanını birlikte değerlendirerek restoran sipariş verisinden açıklanabilir karar "
        "destek mekanizması üretmeyi hedeflemektedir. Yöntem; veri ön işleme, association rule analizi, Bayes olasılık güncellemesi "
        "ve menü skorlama katmanlarının ardışık bir akışta birleştirilmesine dayanır. Bu rapor, metin merkezli akademik anlatımı esas alır "
        "ve grafikleri teknik tartışmayı destekleyen kanıt unsuru olarak konumlandırır."
    )
    f = PanelFlow(c, 42, h - 294, w - 84, 42, regular, bold)
    f.add_paragraph(summary, size=11, leading=1.30, bold=False, after=0)
    c.setFont(regular, 10)
    c.setFillColor(colors.HexColor("#4A4A4A"))
    c.drawRightString(w - 42, 34, "Tarih: 13 Mayıs 2026")


def draw_blank(c: canvas.Canvas, w: float, h: float) -> None:
    c.setFillColor(colors.white)
    c.rect(0, 0, w, h, fill=1, stroke=0)


def build() -> Path:
    regular, bold = load_fonts()
    pw, ph = landscape(A4)
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(PDF_PATH), pagesize=(pw, ph))

    raw = pd.read_csv(HAM_VERI, sep="|")
    clean = pd.read_csv(TABLO_DIR / "cleaned_orders.csv")
    rules = pd.read_csv(TABLO_DIR / "association_rules.csv")
    bayes = pd.read_csv(TABLO_DIR / "bayes_kurallari.csv")
    menu = pd.read_csv(TABLO_DIR / "menu_suggestions.csv")

    order_n = int(clean["order_id"].nunique())
    item_n = int(clean["item_name"].nunique())
    avg_item_order = float(clean.groupby("order_id")["item_name"].nunique().mean())
    rules_n = len(rules)
    bayes_n = len(bayes)
    max_bf = float(bayes["bayes_factor"].max())
    med_conf = float(rules["confidence"].median())
    med_lift = float(rules["lift"].median())
    d = pd.to_datetime(clean["order_date_parsed"])
    aylik = clean.assign(_d=d).groupby(clean.assign(_d=d)["_d"].dt.month)["order_id"].nunique()

    # 1) Kapak
    draw_cover(c, pw, ph, regular, bold)
    c.showPage()

    # 2) Arka kapak boş
    draw_blank(c, pw, ph)
    c.showPage()

    # 3) Logical 1|2
    lp, rp = pair(pw, ph, 1, 2, "Metodoloji ve Problem Gerekçesi", "Veri Kümesi, Şema ve Model Seçimi")
    lx, ltop, lw, lbottom = panel_frame(c, lp, regular, bold)
    rx, rtop, rw, rbottom = panel_frame(c, rp, regular, bold)
    lf = PanelFlow(c, lx, ltop, lw, lbottom, regular, bold)
    rf = PanelFlow(c, rx, rtop, rw, rbottom, regular, bold)

    lf.add_subtitle("Problem neden bu yaklaşımla ele alındı?")
    lf.add_paragraph("Restoran verisinde temel ihtiyaç, tekil ürün satışından çok ürün birlikteliklerinin oluşturduğu ek gelir fırsatını ölçmektir. Bu sebeple problem, tahmin odaklı bir sınıflandırma sorusu olarak değil örüntü keşfi ve karar desteği problemi olarak tanımlanmıştır.")
    lf.add_paragraph("Popülerlik tabanlı yöntemler bağlamdan bağımsızdır; yalnızca genel görülme olasılığına bakar. Oysa gerçek işletme kararı, belirli bir ürün seçildiğinde ikinci ürün davranışının nasıl değiştiğini bilmek ister. Bu gereksinim, Bayes güncellemesini yöntemsel olarak zorunlu kılar.")
    lf.add_subtitle("Nasıl çalışıyor?")
    lf.add_bullets([
        "Sipariş satırları transaction formatına çevrilerek birlikte-görülme yapısı korunur.",
        "Apriori ile aday kümeler çıkarılır; association rule katmanında yönlü ilişki elde edilir.",
        "Support-confidence-lift metrikleri ile kural kalitesi hesaplanır.",
        "Bayes güncellemesi ile prior-posterior farkı ölçülerek karar etkisi nicelleştirilir.",
    ])
    lf.add_paragraph("Bu mimaride amaç, en çok kural üretmek değil; işletme aksiyonuna dönüşebilecek güvenilir ve açıklanabilir kural seti oluşturmaktır.")
    lf.fill_with_tail([
        "Metodolojik çıkarım: Problemin doğru tanımı, model başarısından önce karar başarısını belirler. Bu çalışmada yöntem seçimi, doğrudan karar ihtiyacına göre yapıldığı için model çıktısı yönetim diliyle konuşabilir hale gelmiştir.",
        "Karar mekanizması açısından sonuç: Kural gücü ve bağlamsal güncelleme birlikte ele alındığında öneri sistemi statik bir liste olmaktan çıkıp davranışa duyarlı bir karar motoruna dönüşür.",
    ])
    lf.add_mini_support(
        IMG["pipeline_mini"],
        "Mini şema yorumu: İşlem akışı lineer ve izlenebilir tutulduğu için her adımın model çıktısına etkisi denetlenebilir durumdadır.",
        image_h=82,
    )

    rf.add_subtitle("Neden bu veri şeması yeterli?")
    rf.add_paragraph("order_id, item_name, category, price, order_date ve order_time alanları birlikte ele alındığında hem örüntü madenciliği hem de iş etkisi değerlendirmesi için gerekli minimum bilgi seti sağlanır. Özellikle fiyat ve kategori alanları, kural gücünü gelir etkisine bağlayan köprü rolündedir.")
    rf.add_paragraph("Veri seti tek başına model doğruluğu için değil, karar kalitesi için değerlendirilmiştir. Bu yaklaşım, metriklerin daha az tekrar edilmesini ve yöntemin daha derin yorumlanmasını sağlar.")
    dt = [["Gösterge", "Değer"], ["Sipariş", tr_int(order_n)], ["Ürün", tr_int(item_n)], ["Ort. ürün/sipariş", f"{avg_item_order:.2f}"], ["Rule", tr_int(rules_n)], ["Bayes rule", tr_int(bayes_n)], ["Medyan confidence", f"{med_conf:.3f}"], ["Medyan lift", f"{med_lift:.3f}"]]
    # tabloyu akış içinde güvenli yerleştir
    table_h = 142
    if rf._can_fit(170):
        draw_table(c, dt, rf.x, rf.y - table_h, rf.w, table_h, regular, bold, fs=8)
        rf.y = rf.y - table_h - 8
    rf.add_paragraph("Teknik anlamı: Sayısal metriklerin tek bir bölümde toplanması, diğer bölümlerde aynı değerlerin tekrar edilmesini engeller ve metin yoğunluğunu gerçek yöntem tartışmasına ayırır.")
    rf.add_paragraph("Model seçimi açısından çıkarım: Bu yapı nedensel model değildir; ancak koşullu olasılık güncellemesi sayesinde nedensellik benzeri karar sinyali üretir. İşletme kararında ihtiyaç duyulan açıklanabilirlik böyle sağlanır.")
    rf.fill_with_tail([
        "İşletmeye etkisi: Şema düzeyi tutarlılık, raporlama tarafında farklı ekiplerin aynı metrik setiyle konuşmasını sağlar. Veri ve karar dili ortaklaştığında strateji uygulama hızı artar.",
    ])
    rf.add_mini_support(
        IMG["rule_count_mini"],
        "Mini özet yorumu: Rule ve Bayes rule farkı, filtrenin seçiciliğini ve karar setinin kontrol altında tutulduğunu gösterir.",
        image_h=92,
        before=7,
    )
    c.showPage()

    # 4) Logical 3|4
    lp, rp = pair(pw, ph, 3, 4, "Veri Ön İşleme Mantığı", "Ön İşleme Sonuçlarının Teknik Okuması")
    lx, ltop, lw, lbottom = panel_frame(c, lp, regular, bold)
    rx, rtop, rw, rbottom = panel_frame(c, rp, regular, bold)
    lf = PanelFlow(c, lx, ltop, lw, lbottom, regular, bold)
    rf = PanelFlow(c, rx, rtop, rw, rbottom, regular, bold)

    lf.add_subtitle("Preprocessing neden gerekliydi?")
    lf.add_paragraph("Rule tabanlı analizlerde küçük veri düzensizlikleri dahi kural uzayını yapay olarak değiştirebilir. Aynı ürünün farklı yazımla geçmesi veya fiyat alanındaki tip hataları, hem support hem confidence dağılımını bozarak karar kalitesini düşürür.")
    lf.add_bullets([
        "Kolon standardizasyonu ile farklı kaynak şemaları tek modele uyarlandı.",
        "Boş/bozuk kayıtlar temizlenerek gürültü azaltıldı.",
        "Fiyat ve kategori alanlarında kontrollü imputasyon uygulandı.",
        "Tarih-saat parse edilerek zaman bağlamı analize taşındı.",
        "Transaction listesi oluşturarak Apriori için uygun temsile geçildi.",
    ])
    lf.add_paragraph("Bu akışın temel amacı satır sayısını azaltmak değil, semantik tutarlılığı yükseltmektir. Böylece model, format farkını değil gerçek müşteri davranışını öğrenir.")
    lf.fill_with_tail([
        "Metodolojik çıkarım: Ön işleme adımı ne kadar şeffaf ve tekrar üretilebilir olursa, modelin bilimsel güvenilirliği o kadar yükselir. Bu projede her adım kod seviyesinde izlenebilir şekilde tanımlanmıştır.",
        "Karar etkisi: Standardizasyon sayesinde aynı kural farklı rapor dönemlerinde karşılaştırılabilir hale gelir; bu da trend yorumunu güçlendirir.",
    ])

    rf.add_subtitle("Grafik analizi")
    rf.add_image(IMG["pre"], height=124, after=6)
    rf.add_paragraph("Grafik neyi gösteriyor?: Ham ve temiz veri arasındaki eksik değer ile tekrarlı satır seviyelerini yan yana sunar. Amaç, preprocessing etkisini görsel olarak doğrulamaktır.", size=8.1)
    rf.add_paragraph("Neden önemli?: Eğer ön işleme sonrası dramatik fark oluşsaydı, analizin veri manipülasyonundan etkilendiği düşünülebilirdi. Buradaki sınırlı fark, ham veri kalitesinin makul olduğunu ve esas katkının standardizasyon/özellik türetimi olduğunu gösterir.", size=8.1)
    rf.add_paragraph("Bu grafikten çıkarılan teknik sonuç: Proje ekibi agresif satır silme yerine bilgi koruyan temizleme stratejisi uygulamıştır. Bu sayede örneklem genişliği korunurken metriklerin güvenilirliği artırılmıştır.", size=8.1)
    rf.add_paragraph("İşletme etkisi: Zaman, fiyat ve kategori alanlarının sağlamlaştırılması, sonraki Bayes yorumlarının doğrudan aksiyon planına çevrilmesini kolaylaştırır.", size=8.1)
    rf.fill_with_tail([
        "Metodolojik değerlendirme: Ön işleme katmanının kalite kontrol raporuyla birlikte sunulması, model çıktısının denetlenebilirliğini artırır ve dış gözlemci için sonuçların güvenilirliğini yükseltir.",
    ])
    lf.add_mini_support(
        IMG["cleaning_mini"],
        "Mini tablo yorumu: Temizleme adımlarının tek tabloda özetlenmesi, ön işleme kararlarının tekrarlanabilirliğini ve audit izini güçlendirir.",
        image_h=138,
    )
    lf.add_paragraph(
        "Ek teknik yorum: Bu özet tablo, veri temizleme adımlarının yalnız uygulandığını değil, hangi adımın hangi risk sınıfını düşürdüğünü izlenebilir kılar. "
        "Bu yapı sayesinde model çıktıları dönemler arasında karşılaştırılırken veri hazırlık değişkenlerinin etkisi daha net ayrıştırılır.",
        size=8.05,
    )
    rf.add_mini_support(
        IMG["support_mini"],
        "Mini histogram yorumu: Support dağılımı, çok düşük destekli kuralların filtre ihtiyacını doğrular ve gürültü kontrolüne katkı sağlar.",
        image_h=82,
    )
    c.showPage()

    # 5) Logical 5|6
    lp, rp = pair(pw, ph, 5, 6, "Lift-Confidence Birlikte Yorumu", "Bayes Yaklaşımının Avantajı")
    lx, ltop, lw, lbottom = panel_frame(c, lp, regular, bold)
    rx, rtop, rw, rbottom = panel_frame(c, rp, regular, bold)
    lf = PanelFlow(c, lx, ltop, lw, lbottom, regular, bold)
    rf = PanelFlow(c, rx, rtop, rw, rbottom, regular, bold)

    lf.add_subtitle("Lift ve confidence neden birlikte yorumlanmalı?")
    lf.add_paragraph("Confidence, kural yönünü ve koşullu olasılığı gösterir; ancak popüler ürün yanlılığına açıktır. Lift ise bu yanlılığı normalize ederek ilişkinin rastgele beklentiden ne kadar uzaklaştığını ölçer.")
    lf.add_paragraph("Bu nedenle karar motorunda confidence tek başına yeterli kabul edilmez. Confidence yüksek fakat lift düşük kurallar, genellikle popülerlik kaynaklı zayıf ayrıştırma taşır.")
    lf.add_image(IMG["rules"], height=122, after=6)
    lf.add_paragraph("Grafik neyi gösteriyor?: Her nokta bir kuraldır; x ekseni confidence, y ekseni lift ve ton seviyesi support bilgisini taşır.", size=8.1)
    lf.add_paragraph("Teknik çıkarım: Yüksek confidence bölgesindeki tüm kurallar eşdeğer değildir. Lift değerinin düşük kaldığı alanlar, bağlamdan bağımsız birlikteliklere işaret eder.", size=8.1)
    lf.add_paragraph("İşletme etkisi: Lift filtresi, gereksiz kampanya yayılımını azaltır ve bütçenin gerçek ayrıştırıcı kurallara yönlendirilmesini sağlar.", size=8.1)
    lf.fill_with_tail([
        "Metodolojik sonuç: Metriklerin rol ayrımı yapılmadan kural seçimi yapıldığında model doğruluğu görünürde artsa da aksiyon kalitesi düşebilir. Bu raporda metrik rol ayrımı özellikle korunmuştur.",
    ])
    lf.add_mini_support(
        IMG["confidence_mini"],
        "Mini grafik yorumu: Confidence dağılımı, eşik seçiminde tek bir sabit değerin her bağlam için yeterli olmadığını ve veri yoğunluğuna duyarlı ayar gerektiğini gösterir.",
        image_h=82,
    )

    rf.add_subtitle("Bayes yaklaşımı neden avantaj sağlar?")
    rf.add_paragraph("Bayes çerçevesi, birliktelik bilgisini karar etkisine dönüştürür. Prior olasılık ile posterior olasılık arasındaki fark, modelin bağlamdan ne kadar öğrenebildiğini doğrudan gösterir.")
    rf.add_paragraph("Bu yaklaşımın temel avantajı açıklanabilirliktir: Karar verici, önerinin yalnız frekans tabanlı değil inanç güncellemesi tabanlı olduğunu görebilir. Böylece öneri kalitesi kadar önerinin gerekçesi de yönetilebilir olur.")
    rf.add_image(IMG["bayes"], height=122, after=6)
    rf.add_paragraph("Grafik analizi: Bayes faktörü dağılımı, güçlü kanıt üreten kuralların seyrek olduğunu; çoğu kuralın zayıf-orta bandında kaldığını gösterir. Bu doğal dağılım, seçici öneri politikasını destekler.", size=8.1)
    rf.add_paragraph("Neden önemli?: Seçici politika, aşırı kampanya üretimini engeller ve müşteriye alakasız öneri sunma riskini azaltır.", size=8.1)
    rf.add_paragraph("Karar destek katkısı: Bayes skoru ile kural sıralaması, yöneticinin önerileri kanıt gücüne göre önceliklendirmesine imkan verir.", size=8.1)
    rf.fill_with_tail([
        "İşletme etkisi: Açıklanabilir öneri yapısı, saha ekiplerinin modeli benimsemesini hızlandırır; çünkü kararın ‘nedenini’ teknik ve ticari dilde aynı anda aktarır.",
    ])
    rf.add_mini_support(
        IMG["bayes_flow_mini"],
        "Mini akış yorumu: Prior'dan Bayes faktörüne giden kısa zincir, modelin açıklanabilir karar üretme mantığını yönetici düzeyinde okunur hale getirir.",
        image_h=82,
    )
    c.showPage()

    # 6) Logical 7|8
    lp, rp = pair(pw, ph, 7, 8, "Sistem Davranışı ve Açıklanabilirlik", "Doğrulama, Hata Yönetimi ve Güven")
    lx, ltop, lw, lbottom = panel_frame(c, lp, regular, bold)
    rx, rtop, rw, rbottom = panel_frame(c, rp, regular, bold)
    lf = PanelFlow(c, lx, ltop, lw, lbottom, regular, bold)
    rf = PanelFlow(c, rx, rtop, rw, rbottom, regular, bold)

    lf.add_subtitle("Sistem davranışı")
    lf.add_paragraph("Sistem ham kural listesini doğrudan kullanıcıya vermez; önce kalite filtresi uygular, sonra menü skoru ile yeniden sıralar. Bu davranış, istatistiksel doğruluk ile ticari uygulanabilirlik arasında denge kurar.")
    lf.add_paragraph("Açıklanabilirlik katmanı, her öneri için antecedent-consequent bağı, confidence, lift ve Bayes yorumunu birlikte taşır. Böylece çıktı, kara kutu puan yerine denetlenebilir bir kanıt zinciri olarak okunur.")
    lf.add_image(IMG["menu"], height=122, after=6)
    lf.add_paragraph("Grafik analizi: Menü skoru-fiyat dağılımı, yüksek olasılık ile makul fiyat dengesi arasındaki gerilimi görünür kılar. Sistem aşırı pahalı kombinasyonları üst sıraya taşımamak için fiyat bileşenini aktif kullanır.", size=8.1)
    lf.add_paragraph("Teknik anlamı: Modelin çok amaçlı optimizasyon yaptığı görülür; tek metrik maksimumu yerine dengeli skor maksimumu aranır.", size=8.1)
    lf.fill_with_tail([
        "İşletme etkisi: Bu davranış, kısa vadeli gelir artışı uğruna uzun vadeli müşteri değerinin bozulmasını engelleyebilir.",
    ])
    lf.add_mini_support(
        IMG["lift_mini"],
        "Mini dağılım yorumu: Lift histogramı, ayrıştırıcı gücün hangi aralıkta yoğunlaştığını göstererek kampanya eşiği kararını teknik olarak destekler.",
        image_h=82,
    )

    rf.add_subtitle("Doğrulama ve hata yönetimi")
    rf.add_paragraph("Sistemin güvenilirliği yalnız olumlu senaryoda değil, veri kusuru ve örüntü yetersizliği senaryolarında da test edilmiştir. Bu yaklaşım, gerçek kullanım koşullarında beklenen hata çeşitliliğini model içine dahil eder.")
    rf.add_bullets([
        "Eksik kolon içeren dosyalarda açıklayıcı doğrulama hatası döndürülür.",
        "Zayıf örüntülü veride anlamlı kombinasyon bulunamadı mesajı üretilir.",
        "Kategori ve zaman filtrelerinde yetersiz veri eşiği kontrol edilir.",
        "Health endpoint ve response şeması testleri servis bütünlüğünü doğrular.",
    ], size=8.0)
    rf.add_paragraph("Bu yapı, yanlış güven üretimini engeller. Kullanıcı başarısızlık nedenini anladığı için model şeffaflığı korunur ve sistemin operasyonel güvenilirliği artar.")
    rf.add_paragraph("Akademik açıdan çıkarım: Hata politikası tasarlanmış modeller, yalnız başarılı örneklerle raporlanan modellere göre daha savunulabilir kabul edilir.")
    rf.fill_with_tail([
        "Karar destek sonucu: Güvenilir hata yönetimi, modelin saha entegrasyonunda sürpriz davranış riskini düşürür ve operasyon ekiplerinin sistemi istikrarlı şekilde kullanmasına olanak verir.",
    ])
    rf.add_mini_support(
        IMG["rule_count_mini"],
        "Mini özet yorumu: Doğrulama sonrası kalan kural hacmi, sistemin hem seçici hem ölçeklenebilir olduğunu gösterir.",
        image_h=142,
        before=8,
    )
    rf.add_paragraph(
        "Ek teknik yorum: Rule hacmi grafiği, doğrulama filtresinin agresifliğini ve karar setinin yönetilebilirliğini aynı anda gösterir. "
        "Çok yüksek rule sayısı gürültü riskini, çok düşük rule sayısı ise kapsama riskini artırır; bu mini özet, iki uç arasındaki dengeyi görünür hale getirir.",
        size=8.05,
    )
    rf.add_paragraph(
        "Derin teknik okuma: Doğrulama katmanı sonrası rule hacminin korunması, filtrenin yalnızca gürültüyü bastırdığını ve bilgi taşıyan kuralları sistemde bıraktığını gösterir. "
        "Bu denge, saha kullanımında hem öneri çeşitliliğini hem de hesaplama maliyetini birlikte optimize eden kritik bir güvenlik mekanizmasıdır.",
        size=8.02,
    )
    c.showPage()

    # 7) Logical 9|10
    lp, rp = pair(pw, ph, 9, 10, "Karar Destek ve İşletme Etkisi", "Toplu Akademik Değerlendirme")
    lx, ltop, lw, lbottom = panel_frame(c, lp, regular, bold)
    rx, rtop, rw, rbottom = panel_frame(c, rp, regular, bold)
    lf = PanelFlow(c, lx, ltop, lw, lbottom, regular, bold)
    rf = PanelFlow(c, rx, rtop, rw, rbottom, regular, bold)

    lf.add_subtitle("Karar destek mantığı")
    lf.add_paragraph("Model çıktısı, ‘hangi ürün hangi bağlamda önerilmeli?’ sorusuna kanıt seviyeli yanıt verir. Böylece kampanya tasarımı sezgisel listelerden veri temelli önceliklendirmeye taşınır.")
    lf.add_paragraph("Aylık trend katmanı, sistemin statik kalmasını engeller. Kural gücü dönemsel değiştiğinde menü ve kampanya önerileri de güncellenir; bu özellik uzun vadeli karar çevikliği sağlar.")
    lf.add_image(IMG["trend"], height=120, after=6)
    lf.add_paragraph("Grafik analizi: Aylık sipariş hacmi dengeli seyrederken kural gücü değişebilmektedir. Bu durum, hacim eşitliğinin tek başına karar için yeterli olmadığını; bağlamsal dinamiğin ayrıca izlenmesi gerektiğini gösterir.", size=8.1)
    lf.add_paragraph(f"Somut okuma: Ocak {tr_int(aylik.get(1,0))}, Şubat {tr_int(aylik.get(2,0))}, Mart {tr_int(aylik.get(3,0))} sipariş. Hacim yakın olmasına rağmen kombinasyon gücü değiştiği için trend takibi kritik kalır.", size=8.1)
    lf.fill_with_tail([
        "İşletme etkisi: Bu yaklaşım, kampanya bütçesinin dönemsel olarak doğru kombinasyonlara kaydırılmasını sağlayarak kaynak verimliliğini yükseltir.",
    ])
    lf.add_mini_support(
        IMG["monthly_mini"],
        "Mini trend yorumu: Kompakt trend grafiği, dönemsel hacim değişiminin izlenmesini hızlandırarak operasyon planlamasında çevik karar sağlar.",
        image_h=82,
    )

    rf.add_subtitle("Toplu değerlendirme")
    rf.add_paragraph("Çalışmanın ana katkısı, veri ön işleme disiplini, kural madenciliği ve Bayes yorumunu tek bir karar hattında birleştirmesidir. Bu birleşim, teknik doğruluk ile yönetimsel uygulanabilirliği aynı dokümanda buluşturur.")
    rf.add_paragraph("Confidence davranış yönünü, lift ayrıştırıcı gücü, Bayes faktörü bağlamsal kanıtı temsil eder. Bu rol ayrımı, model çıktısının neden bu sırayla öneri ürettiğini açıklamayı mümkün kılar.")
    rf.add_paragraph("Sistemin API mimarisine taşınmış olması, analizin bir defalık notebook çıktısı olmasını engeller ve kurumsal raporlama süreçlerine entegrasyonu kolaylaştırır.")
    rf.add_paragraph("Genel teknik sonuç: Model, restoran bağlamında açıklanabilir yapay zekâ yaklaşımının pratikte karar desteğine dönüşebileceğini göstermektedir.")
    rf.fill_with_tail([
        "Metodolojik çıkarım: Ölçüm, yorum ve aksiyon zinciri tek bir mimaride birleştiğinde model değeri yalnız veri bilim ekibi için değil işletme karar vericileri için de görünür hale gelir.",
        "Son değerlendirme: Bu rapor yapısı, akademik doğruluk ile uygulama gerçekliğini aynı metin akışında koruyan dengeli bir çerçeve sunmaktadır.",
    ])
    rf.add_mini_support(
        IMG["category_mini"],
        "Mini kategori yorumu: Kategori yoğunluğu, öneri stratejisinde çeşitlilik cezasının neden gerekli olduğunu somut biçimde destekler.",
        image_h=128,
    )
    rf.add_paragraph(
        "Ek teknik yorum: Kategori yoğunluğunun dengesizleştiği senaryolarda model, sık görülen kategoriye aşırı yönelme eğilimi gösterebilir. "
        "Bu nedenle çeşitlilik cezası yalnız estetik bir tercih değil, öneri adaletini ve menü genişliğini koruyan teknik bir düzenleyicidir.",
        size=8.05,
    )
    c.showPage()

    # 8) Logical 11|12
    lp, rp = pair(pw, ph, 11, 12, "Sınırlılıklar", "Geliştirme Önerileri ve Kapanış")
    lx, ltop, lw, lbottom = panel_frame(c, lp, regular, bold)
    rx, rtop, rw, rbottom = panel_frame(c, rp, regular, bold)
    lf = PanelFlow(c, lx, ltop, lw, lbottom, regular, bold)
    rf = PanelFlow(c, rx, rtop, rw, rbottom, regular, bold)

    lf.add_subtitle("Sınırlılıkların teknik anlamı")
    lf.add_paragraph("Sınırlılık analizi, modelin hangi koşullarda güvenle kullanılacağını tanımlar. Yüksek metrik tek başına yeterli değildir; verinin kapsadığı dönem ve ürün evreni sonuçların genellenebilirliğini sınırlar.")
    lf.add_bullets([
        "Veri dönemi sınırlı olduğundan uzun dönem mevsimsellik analizi kısıtlıdır.",
        "Kural tabanlı yapı, yeni ürünler için cold-start desteği gerektirir.",
        "Kategori filtreleri sabit listeye bağlı olduğundan segmentasyon esnekliği sınırlanabilir.",
        "Notebook metin kodlaması dokümantasyon kalitesini etkileyebilir.",
    ], size=8.0)
    lf.add_paragraph("Bu sınırlılıklar yöntemin değerini ortadan kaldırmaz; yalnız bir sonraki sürümde hangi mühendislik adımlarının öncelikleneceğini netleştirir.")
    lf.add_image(IMG["cleaning_mini"], height=148, after=6)
    lf.add_paragraph("Data Cleaning Summary neyi gösteriyor?: Uygulanan temizleme adımlarını tek bir kompakt tabloda toplayarak hangi adımın hangi kalite kazanımını hedeflediğini görünür hale getirir.", size=8.15)
    lf.add_paragraph("Neden önemli?: Sınırlılık tartışmasında yalnız problem alanlarını değil, hangi kalite kontrollerinin hâlihazırda uygulandığını da göstermek gerekir. Bu tablo, model güveninin hangi veri disiplinine dayandığını kanıtlar.", size=8.15)
    lf.add_paragraph("Teknik genişletme: Bu tablonun okunabilirliğinin artırılması, denetim sırasında adım atlama riskini azaltır. Her satır bir kalite kontrol sınıfını temsil ettiği için bakım ekipleri hangi adımın hangi veri riskini karşıladığını hızlıca eşleyebilir.", size=8.08)
    lf.fill_with_tail([
        "Metodolojik sonuç: Sınırlılıkların açıkça belirtilmesi, raporun bilimsel dürüstlüğünü ve dış denetim karşısındaki savunulabilirliğini artırır.",
        "İşletme açısından anlamı: Sistem doğru bağlamda kullanıldığında yüksek değer üretir; sınırların bilinmesi yanlış beklenti riskini azaltır.",
    ])

    rf.add_subtitle("Geliştirme yol haritası")
    rf.add_paragraph("Sonraki aşamada hedef, modeli daha karmaşık hale getirmek değil daha güvenilir, daha ekonomik ve daha sürdürülebilir hale getirmektir. Öneriler bu nedenle algoritmik yenilikten çok operasyonel etkiye göre sıralanmıştır.")
    rf.add_bullets([
        "A/B test entegrasyonu ile önerilerin gerçek gelir etkisi ölçülmeli.",
        "Skor fonksiyonuna kâr marjı, stok devir hızı ve tedarik riski eklenmeli.",
        "Kategori ve zaman eşikleri veri yoğunluğuna göre adaptif hale getirilmeli.",
        "Cold-start için içerik benzerliği tabanlı yardımcı katman eklenmeli.",
        "Rapor üretimi CI sürecine bağlanarak otomatik akademik dokümantasyon sağlanmalı.",
    ], size=8.0)
    rf.add_paragraph("Kapanış: Bu sürüm, 4 kağıt sınırında her yarım sayfayı ayrı bir iç sayfa gibi ele alarak metin ağırlıklı teknik anlatım hedefiyle hazırlanmıştır. Grafikler destekleyici tutulmuş, ana içerik yöntem analizi ve karar yorumuna ayrılmıştır.")
    rf.add_image(IMG["pipeline_mini"], height=154, after=6)
    rf.add_paragraph("Preprocessing Pipeline neyi gösteriyor?: Yükleme, temizleme, dönüşüm ve transaction adımlarının sıralı akışını vererek modelin veri yaşam döngüsünü tek bakışta okunur hale getirir.", size=8.15)
    rf.add_paragraph("Neden önemli?: Karar destek sistemlerinde süreç şeffaflığı en az çıktı doğruluğu kadar kritiktir. Akış diyagramı, hangi adımın neden gerekli olduğunu ve sistem davranışının nasıl üretildiğini teknik olarak belgelendirir.", size=8.15)
    rf.add_paragraph("Teknik genişletme: Pipeline kutularının daha büyük gösterimi, adımlar arası bağımlılıkların görsel olarak daha net okunmasını sağlar. Bu netlik, yeni sürümlerde hangi adımın değiştirilmesi gerektiğini belirlemede bakım maliyetini düşürür.", size=8.08)
    rf.fill_with_tail([
        "Genel çıkarım: Çalışma, veri işleme disiplini ile açıklanabilir yapay zekâ yaklaşımını birleştirerek restoran yönetimi için ölçeklenebilir bir karar destek temeli sunmaktadır.",
    ])
    c.showPage()

    c.save()
    return PDF_PATH


if __name__ == "__main__":
    output = build()
    print(f"Rapor oluşturuldu: {output}")
