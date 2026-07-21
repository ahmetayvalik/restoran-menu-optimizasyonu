# Restoran Menu Optimizasyonu

Bayes tabanli capraz satis analizi yapan, FastAPI backend ve React/Vite frontend iceren restoran menu optimizasyon projesi.

## Ozellikler

- CSV siparis verisini yukleyip otomatik analiz etme
- Apriori ve association rules ile capraz satis kurallari cikarma
- Bayes faktoru ile kural gucunu yorumlama
- Menu paketi ve fiyat stratejisi onerileri uretme
- Kategori ve zaman filtresi bazli inceleme
- Aylik trend analizi
- Ayrik CLI analiz scripti ve notebook destegi

## Teknolojiler

- Python 3.10+
- FastAPI
- pandas
- mlxtend
- React 18
- Vite 5
- pytest

## Kurulum

1. Ortam degiskenlerini hazirlayin.

```bash
copy .env.example .env
copy frontend\.env.example frontend\.env
```

2. Backend bagimliliklarini kurun.

```bash
python -m venv backend/.venv
backend\.venv\Scripts\activate
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

3. Frontend bagimliliklarini kurun.

```bash
cd frontend
npm install
cd ..
```

## Calistirma

Backend:

```bash
backend\.venv\Scripts\activate
uvicorn backend.app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

## Kullanim Ornekleri

API saglik kontrolu:

```bash
curl http://127.0.0.1:8000/health
```

CLI analiz scripti:

```bash
backend\.venv\Scripts\python backend/scripts/restaurant_menu_optimizer.py
```

Pytest:

```bash
backend\.venv\Scripts\pytest tests/backend -q
```

## Ortam Degiskenleri

- `BACKEND_SERVICE_NAME`: health endpoint servis adi
- `BACKEND_PORT`: backend portu
- `BACKEND_ALLOWED_ORIGINS`: CORS icin virgulle ayrilmis origin listesi
- `BACKEND_MIN_SUPPORT`: apriori minimum support esigi
- `BACKEND_MIN_LIFT`: rule minimum lift esigi
- `VITE_API_BASE_URL`: `frontend/.env` icindeki backend API adresi

## Klasor Yapisi

```text
backend/
  app/
  scripts/
  requirements.txt
  requirements-dev.txt
data/
  raw/
  sample/
docs/
  project-overview.md
  reports/
frontend/
  src/
notebooks/
outputs/
  figures/
  tables/
tests/
  backend/
```

## Buyuk Dosyalar

- Projede 50 MB ustu model agirlik dosyasi tespit edilmedi.
- `frontend/node_modules` ve `backend/.venv` altindaki buyuk binary dosyalar gelistirme bagimliliklarina ait; `.gitignore` ile haric tutuldu.
- Ileride model agirliklari eklenecekse bunlari Git yerine harici bir depoda tutun.
  Placeholder: Hugging Face / Google Drive baglantisini buraya ekleyin.
- Gerekirse Git LFS kullanin:

```bash
git lfs install
git lfs track "*.pt" "*.pth" "*.onnx" "*.h5" "*.ckpt"
```

## Test Verisi ve Dokumanlar

- Gercek veri: `data/raw/restaurant_orders.csv`
- Ornek test verileri: `data/sample/`
- Rapor: `docs/reports/Restoran_Menu_Analizi_Raporu.pdf`
- Notebook: `notebooks/BAYES_MENU.ipynb`
