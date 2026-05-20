# Budgetify backend

Active application entrypoint:
- `main.py`

Live backend modules:
- `api/`
- `db/`
- `src/Generation/`
- `src/models/transactions.py`

Primary API routers registered by `main.py`:
- `api.routes.profile`
- `api.routes.transactions`
- `api.routes.stats`

The repository has been cleaned to remove disconnected legacy controller/model code and stale tests that targeted removed or missing modules.

