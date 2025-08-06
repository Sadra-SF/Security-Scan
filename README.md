# Security Scanner Backend

Django + DRF API with Celery, PostgreSQL, Redis, and ZAP container scaffold.

Services:
- api: Django/DRF app served by Gunicorn+Uvicorn worker on port 8000
- worker: Celery worker
- beat: Celery beat
- db: PostgreSQL (internal only)
- redis: Redis broker/result backend (internal only)
- zap: OWASP ZAP (internal, unused for now)

## Prerequisites
- Docker and Docker Compose

## Quick start

1) Copy environment template:
```
cp .env.example .env
```

2) Build and start:
```
docker compose up --build
```

The first run will apply migrations automatically.

### Run a test scan
1) Create minimal records via Django shell or admin:
   - Asset: name="Example Web", type="web", url_or_cidr="http://example.com"
   - ScanProfile: name="Static Only", enabled_scanners=["static"] or explicitly ["static.deps","static.config"]
2) Start a scan:
```
curl -X POST http://localhost:8000/api/scans/ \
  -H "Content-Type: application/json" \
  -d "{\"asset_id\": 1, \"profile_id\": 1}"
```
Response:
```
{"scan_run_id": 1, "status": "queued"}
```
3) List scans:
```
curl http://localhost:8000/api/scans/
```

Reports are written under a shared volume:
- /app/var/reports/scan_{id}.txt (inside containers)
- This path is mounted via a named volume `reports_data` to api/worker/beat.

#### Enabled scanners values
- "static.deps": static dependency scanner (no external execution yet). In DEBUG, emits deterministic examples for pypi:requests@2.0.0 and npm:lodash@4.17.0.
- "static.config": static headers/config heuristic scanner reading ScanContext.config only.
- "static": legacy/convenience selector that includes both of the above adapters.
- "dynamic.zap": dynamic scanner placeholder for OWASP ZAP. Placeholder-only, no external calls. In DEBUG, emits one synthetic finding per mode:
  - mode="baseline": medium severity, category "missing_header", title "[dynamic.zap] ZAP baseline simulated missing security header", owasp_tag "A05:2021".
  - mode="active": high severity, category "injection", title "[dynamic.zap] ZAP active simulated SQLi", owasp_tag "A03:2021".
- "network.nmap": network scanner placeholder for nmap. Placeholder-only, no subprocess calls. In DEBUG, emits one synthetic open port finding:
  - category "open_port", low severity, title "[network.nmap] open port detected 443/tcp", remediation "Verify service exposure".
- Type-level enables:
  - "static", "dynamic", "network" select all adapters of that type. Order is preserved and duplicates removed.

Examples:
- Static only: `["static"]` or `["static.deps","static.config"]`
- Dynamic only: `["dynamic","dynamic.zap"]`
- Network only: `["network","network.nmap"]`
- Mixed types (demo): `["static","dynamic","network"]`

#### Passing config for scanners (placeholder)
POST /api/scans/ uses the ScanRun.profile and Asset. For now, config is read from `ScanRun.meta.config` (temporary mechanism; future API may accept it directly). Structure:

Dynamic ZAP (ScanContext.config.zap):
```
{
  "zap": {
    "mode": "baseline|active",
    "url": "http://example.com",
    "context_name": "Default Context",
    "auth": {"type": "basic", "username": "user", "password": "pass"},
    "exclude_patterns": ["*/logout", "*/ignore*"],
    "timeout": 600
  }
}
```
Notes: All keys are optional for the placeholder. If `url` is missing, adapter returns [] and, in DEBUG, emits a LOW-severity configuration finding noting invalid config.

Network nmap (ScanContext.config.nmap):
```
{
  "nmap": {
    "targets": ["10.0.0.1", "10.0.0.0/24"],
    "top_ports": 100,
    "scripts": ["safe"],
    "timing": "T3",
    "timeout": 600
  }
}
```
Notes: If `targets` is omitted and the Asset type is one of host/network/cidr/ip and `url_or_cidr` is present, the adapter defaults to that asset value as the single target. Otherwise returns [] and, in DEBUG, emits a LOW-severity configuration finding.

All integrations are placeholders and do not perform real network or subprocess calls. Behavior is gated by DJANGO_DEBUG.

#### Example curl invocations
Dynamic baseline-only:
```
# Create Asset (web) and Profile (enable dynamic)
curl -X POST http://localhost:8000/api/scans/ \
  -H "Content-Type: application/json" \
  -d "{\"asset_id\": 1, \"profile_id\": 2}"
```
Profile.enabled_scanners should include `["dynamic","dynamic.zap"]`. To attach config via a temporary mechanism, store it in the ScanRun meta prior to orchestration in future; for now defaults and DEBUG simulation will produce a baseline synthetic finding if a url is provided in `meta.config.zap.url`.

Network-only:
```
# Asset type=network with url_or_cidr=10.0.0.1, Profile enabled_scanners=["network","network.nmap"]
curl -X POST http://localhost:8000/api/scans/ \
  -H "Content-Type: application/json" \
  -d "{\"asset_id\": 3, \"profile_id\": 4}"
```
In DEBUG, the report should include an "open port" line and aggregates should count at least one LOW severity.


## Endpoints

- Health: http://localhost:8000/api/health/  (now includes celery_broker status)
- OpenAPI schema: http://localhost:8000/api/schema/
- Swagger UI: http://localhost:8000/api/docs/
- JWT obtain: POST http://localhost:8000/api/auth/jwt/create
- JWT refresh: POST http://localhost:8000/api/auth/jwt/refresh
- Scans:
  - POST http://localhost:8000/api/scans/  body: {"asset_id": int, "profile_id": int}
  - GET  http://localhost:8000/api/scans/

Example auth payload:
```
{
  "username": "admin",
  "password": "admin"
}
```
Note: No users are created by default in this scaffold. Scans endpoints are temporarily open (AllowAny).

## Environment variables (.env)
- DJANGO_SECRET_KEY
- DJANGO_DEBUG
- ALLOWED_HOSTS
- POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
- REDIS_URL
- CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- ZAP_HOST, ZAP_PORT, ZAP_API_KEY

Defaults suitable for local docker compose are provided in .env.example.

## Service commands

- api: `gunicorn api_server.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`
- worker: `celery -A api_server worker --loglevel=INFO --concurrency=2`
- beat: `celery -A api_server beat --loglevel=INFO`

## Implementation notes (current step)
- Implemented static scanners and selection:
  - `static.deps`: accepts pre-supplied JSON payload via `ScanContext.config.deps_payload` and normalizes into FindingRecord instances. In DEBUG, emits deterministic examples (requests 2.0.0 CVE-XXXX-YYYY; lodash 4.17.0).
  - `static.config`: heuristic checks for missing security headers, debug mode, and weak cookie flags using `ScanContext.config`. In DEBUG with no config, emits a single missing_header(CSP) finding.
- Added aggregation enhancements: `core.tasks.aggregate_results` computes `by_severity` and `by_category` and stores under `ScanRun.meta.aggregate`.
- Report now lists findings titles with `category:` lines when a snapshot is available; otherwise includes a placeholder. Snapshot is saved in `ScanRun.meta.last_results`.
- Selection logic enhanced in `core.tasks.prepare_scan` to support explicit names "static.deps", "static.config", legacy "static", and by-type values.
- Added TODO placeholder for persisting findings in a later subtask.

## Limitations
- No subprocess or network calls; findings are synthetic in DEBUG or derived purely from provided config payloads.
- No Finding model yet; results are not persisted individually, only aggregates and a text report are produced.
- Future work: integrate real pip-audit/npm-audit ingestion and optional CI ingestion endpoint for static deps.