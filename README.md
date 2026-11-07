# Restaurant Menu Optimization

A decision-support application for exploring purchase patterns in restaurant order data. It combines association-rule mining with a FastAPI backend and a React/Vite frontend to support cross-selling analysis and menu planning.

## What the project does

- Imports restaurant order data from CSV files
- Extracts item associations using Apriori and association rules
- Examines rule strength using support, confidence, lift, and a Bayesian interpretation
- Explores candidate bundles and pricing decisions
- Provides category, time-period, and monthly-trend views
- Includes CLI analysis scripts, notebooks, and backend tests

The application provides analytical recommendations; it does not establish that a proposed bundle will increase sales without subsequent testing.

## Technology

Python 3.10+, FastAPI, pandas, mlxtend, React 18, Vite 5, pytest.

## Project structure

```text
backend/    API, analysis scripts, dependencies
frontend/   React user interface
data/       Raw and sample datasets
docs/       Project documentation and reports
notebooks/  Exploratory analysis
outputs/    Generated figures and tables
tests/      Backend tests
```

## Local setup (Windows PowerShell)

From the repository root:

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python -m pip install -r backend/requirements-dev.txt
cd frontend
npm install
cd ..
```

Run the API and UI in separate terminals:

```powershell
backend/.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000
```

```powershell
cd frontend
npm run dev
```

## Tests

```powershell
backend/.venv/Scripts/python -m pytest tests/backend -q
```

## Configuration

Refer to `.env.example` and `frontend/.env.example` for supported options, including backend configuration, association-rule thresholds, CORS settings, and the frontend API base URL. Avoid committing populated `.env` files.

## Documentation and data

- `docs/project-overview.md`: additional context
- `docs/reports/Restoran_Menu_Analizi_Raporu.pdf`: project report
- `notebooks/BAYES_MENU.ipynb`: exploratory work
- `data/sample/`: sample input data

Real restaurant data should only be distributed where authorized. Keep sensitive or proprietary order records out of public commits.
