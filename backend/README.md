# Backend

## Run `/search` API tests

Run from `backend/` directory.

1. Install dependencies

```powershell
pip install -r requirements.txt
```

2. Execute tests

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

If you use the project virtual environment, run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

This runs the `/search` API tests in `tests/test_search_api.py`.
