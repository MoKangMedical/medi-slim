# MediSlim Final Merge Notes

Generated: 2026-05-09

## Final Directory

`/Users/apple/Desktop/OPC/MediSlim-final`

This directory uses the production-running MediSlim app as the base, then adds the newer GitHub/main-side modules and documents from `/Users/apple/Desktop/OPC/medi-slim`.

## Sources

- Production base: `/Users/apple/Desktop/OPC/MediSlim/medi-slim-main`
- Incoming main-side project: `/Users/apple/Desktop/OPC/medi-slim`

## Merge Policy

The production app remains authoritative for files that power the current live site:

- `app.py`
- `admin.py`
- `mimo_client.py`
- `storage.py`
- `templates/index.html`
- `templates/assess.html`
- `templates/constitution.html`
- `templates/client.html`
- `templates/product_hub.html`
- `static/app.css`
- `scripts/server/*`

Newer main-side modules were added when they did not overwrite production-critical files:

- `consumer/`
- `enterprise-b2b/`
- `src/`
- `tests/`
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `smart_marketing.py`
- `decision_checkpoint.py`
- `vector_memory.py`
- additional docs and content assets

## Conflicting Incoming Files

Incoming versions of same-name core files were preserved under `_incoming-main/` for manual review:

- `_incoming-main/app.py`
- `_incoming-main/admin.py`
- `_incoming-main/README.md`
- `_incoming-main/.gitignore`
- `_incoming-main/content_engine/ab_testing.py`
- `_incoming-main/content_engine/preview_server.py`
- `_incoming-main/content_engine/scheduler.py`
- `_incoming-main/content_engine/tracking.py`
- `_incoming-main/docs/BUSINESS-MODEL.md`
- `_incoming-main/templates/index.html`
- `_incoming-main/templates/assess.html`
- `_incoming-main/templates/flow.html`
- `_incoming-main/templates/admin2.html`

## Validation

The production core files compile successfully:

```bash
python3 -m py_compile app.py admin.py mimo_client.py storage.py
```

The final directory still contains the local ignored `.env` for the current machine. Do not commit `.env`.
