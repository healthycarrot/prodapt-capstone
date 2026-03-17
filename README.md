# prodapt-capstone

## Backend Run Commands

Run all commands from repository root (`prodapt-capstone`).

### 1) Prepare environment

```powershell
Copy-Item .\backend\.env.example .\backend\.env
```

### 2) Install dependencies (example)

```powershell
pip install -r script/pipeline_mongo/requirements.txt
pip install fastapi uvicorn
```

### 3) Prepare keyword search prerequisites (one-time / idempotent)

```powershell
python .\script\pipeline_mongo\backfill_candidate_search_text.py --db-name prodapt_capstone --collection normalized_candidates --create-text-index --summary-out .\script\pipeline_mongo\backfill_candidate_search_text_report.json
```

### 4) Run retrieval pipeline smoke test

```powershell
python -c "from backend.app.core import get_retrieval_pipeline_service; from backend.app.domain import SearchQueryInput; p=get_retrieval_pipeline_service(); out=p.run(SearchQueryInput(query_text='backend engineer with python and fastapi, 3+ years')); print({'retry_required': out.retry_required, 'result_count': len(out.results)})"
```

### 5) Start API server (FR-06-01 partial)

```powershell
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`
