# Restoran Menu Optimizasyonu ve Capraz Satis Oneri Sistemi

CSV siparis verilerini analiz ederek association rules, confidence ve lift metrikleri ile en guclu capraz satis kombinasyonlarini bulan mini full-stack demo uygulamasi.

## Proje Yapisi

```text
backend/
  __init__.py
  main.py
  requirements.txt
  requirements-dev.txt
  tests/
    test_api.py
frontend/
  index.html
  package.json
  vite.config.js
  src/
    App.jsx
    main.jsx
    styles.css
    components/
      Header.jsx
      UploadPanel.jsx
      ResultsSection.jsx
      InfoSection.jsx
      ErrorAlert.jsx
      LoadingSpinner.jsx
test_data/
  valid_test_orders.csv
  invalid_missing_columns.csv
  weak_patterns.csv
README.md
```

## Teknoloji Yigini

- Backend: FastAPI
- Frontend: React + Vite
- Veri isleme: pandas
- Analiz: mlxtend apriori + association_rules
- Test: pytest + httpx

## Backend Nasil Calistirilir

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend adresi:

```text
http://127.0.0.1:8000
```

## Frontend Nasil Calistirilir

```bash
cd frontend
npm install
npm run dev
```

Frontend adresi:

```text
http://127.0.0.1:5173
```

## Health Endpoint Nasil Test Edilir

Tarayici veya curl ile:

```text
http://127.0.0.1:8000/health
```

Beklenen yanit:

```json
{
  "status": "ok",
  "service": "backend",
  "port": 8000
}
```

## Swagger

```text
http://127.0.0.1:8000/docs
```

## Analiz Endpoint

```text
POST http://127.0.0.1:8000/upload-and-analyze
```

Basarili yanit:

```json
{
  "status": "success",
  "rules_found": 3,
  "results": [
    {
      "ana_urunler": ["Chicken Tacos"],
      "yaninda_satilacak_urun": ["Hamburger"],
      "guven_orani_yuzde": 23.9,
      "satis_artirma_carpani": 1.585,
      "support": 0.008
    }
  ]
}
```

Hata yaniti:

```json
{
  "status": "error",
  "message": "Aciklayici hata mesaji"
}
```

## Ornek CSV Formati

```csv
order_id,item_name
1,Hamburger
1,Fries
1,Cola
2,Chicken Tacos
2,Hamburger
```

## Ornek Test CSV Dosyalari

### `test_data/valid_test_orders.csv`
- Dogru formatta calisir.
- Backend basarili JSON dondurur.
- Frontend sonuc kartlarini gosterir.

### `test_data/invalid_missing_columns.csv`
- Kolonlar bilerek yanlistir.
- Beklenen hata: `Dosyada order_id ve item_name sutunlari bulunmalidir.`

### `test_data/weak_patterns.csv`
- Format dogrudur ama iliskiler zayiftir.
- Beklenen hata: `Bu veri setinde anlamli capraz satis kombinasyonu bulunamadi.`

## Demo Sirasinda Hangi Dosya Ile Ne Beklenir

1. `valid_test_orders.csv`
Sonuc kartlari gelir, backend bagli etiketi yesil gorunur.

2. `invalid_missing_columns.csv`
Frontend hata kutusunda eksik kolon mesaji gorunur.

3. `weak_patterns.csv`
Frontend hata kutusunda anlamli kombinasyon bulunamadi mesaji gorunur.

## Manuel Test Komutlari

Backend calistirma:

```bash
uvicorn main:app --reload --port 8000
```

Frontend calistirma:

```bash
npm install
npm run dev
```

Health kontrol:

```text
http://127.0.0.1:8000/health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Pytest Testleri

Root klasorden:

```bash
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
pytest backend/tests -q
```

Test kapsami:
- valid CSV testi
- missing columns testi
- no rules testi
- health endpoint testi

## Kullanim Notlari

- Sistem supervised learning modeli degildir.
- Association rules, confidence ve lift ile calisan capraz satis analiz sistemi kullanir.
- Backend loglari terminalde okunabilir sekilde yazilir.
- Frontend uygulama acilisinda backend baglantisini otomatik kontrol eder.
