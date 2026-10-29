# College Website

A responsive React + TypeScript frontend and FastAPI REST API scaffold for a college website. Institutional identity fields and sample academic material are intentionally placeholders; verify and replace them before public launch. No accreditation, affiliation, ranking, faculty, or placement claims are asserted.

## What is implemented

- Public routes for home, about, academics, admissions, faculty, campus, careers, news/events, contact, and policies.
- Responsive navigation, labeled forms, keyboard focus treatment, reduced-motion support, page titles/meta description, and not-found route.
- Configurable institution details and CSS brand variables in `src/config.ts` and `src/styles.css`.
- Versioned API under `/api/v1`, interactive OpenAPI docs at `/docs` outside production.
- PostgreSQL/SQLAlchemy schema and Alembic migrations; SQLite is used for isolated unit/API tests.
- Applicant-only self-registration with Argon2 password hashing, email verification, one-time password recovery, short-lived bearer tokens, server-side role checks, and separately provisioned administrator access.
- Applicant application drafts/status tracking, duplicate prevention, private owner/admin document access, upload size/type/signature checks, and ClamAV scanning.
- Docker Compose development, HTTPS production, and disposable PostgreSQL integration-test profiles.

Attendance, grades, student records, automated email, verified faculty data, official policy content, and institution-specific application eligibility rules are not fabricated or connected.

## Requirements

- Node.js 20+ and npm
- Python 3.11+ (tested with Python 3.13)
- PostgreSQL 15+ or Docker Desktop with Compose

## Configure the college

1. Copy `.env.example` to `.env` in the repository root. Compose requires this file.
2. Replace `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, and `JWT_SECRET_KEY` with unique, randomly generated values (at least 32 characters for the JWT key). For example, generate a value with `py -c "import secrets; print(secrets.token_urlsafe(48))"`. Do not reuse production credentials in tests or commit `.env`.
3. Configure trusted `CORS_ORIGINS` and `PUBLIC_APP_URL`.
4. Configure the college identity and verified public content in `src/config.ts`.
5. Replace the sample email, phone, address, dates, programs, and images; review policies and accessibility with the institution.
6. Set `VITE_API_URL` to the API base URL. Never put server secrets in a `VITE_` variable.

## Local development

### Frontend

```powershell
npm install
npm run dev
```

### API (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r backend\requirements.txt
Push-Location backend
Copy-Item ..\.env.example .env
py -m alembic upgrade head
py -m uvicorn app.main:app --reload
```

Edit `backend\.env` for a reachable PostgreSQL instance and set a strong `JWT_SECRET_KEY`. For quick local API work without PostgreSQL, set `DATABASE_URL=sqlite:///./college.db` there before running Alembic. To use verification and password recovery locally, configure SMTP; the development Compose profile supplies Mailpit instead. Use `Pop-Location` after stopping the API.

When running the API without Compose, set `RATE_LIMIT_STORAGE_URI=memory://` unless Redis is running, and configure SMTP and `CLAMAV_HOST` to match services that are actually available. Email-dependent routes return an explicit service-unavailable error if SMTP is not configured; document uploads fail closed if malware scanning is unavailable.

To load clearly fictional development content into a local development database:

```powershell
$env:LOAD_DEMO_DATA = "true"
py -m app.seed_demo
Remove-Item Env:\LOAD_DEMO_DATA
```

### Docker Compose

```powershell
Copy-Item .env.example .env
# Edit .env and replace all placeholder secrets before starting Compose.
docker compose --profile development up --build
```

The development profile runs PostgreSQL, Redis-backed rate limiting, ClamAV, Mailpit, the API, and the Vite frontend. The API and database ports bind to loopback; Mailpit's inbox is available at `http://127.0.0.1:8025`. Verification and password-reset links are captured there. The API applies Alembic migrations at startup. Compose has no default production signing key or database/Redis credential: replace all placeholders before starting.

For the production profile, configure `.env` with:

```powershell
$env:ENVIRONMENT = "production"
$env:PUBLIC_DOMAIN = "college.example.edu"
$env:PUBLIC_APP_URL = "https://college.example.edu"
$env:CORS_ORIGINS = '["https://college.example.edu"]'
$env:SMTP_HOST = "smtp.example.edu"
$env:SMTP_PORT = "587"
$env:SMTP_USERNAME = "college-mail"
$env:SMTP_PASSWORD = "provider-secret"
$env:SMTP_SENDER = "noreply@example.edu"
$env:SMTP_STARTTLS = "true"
docker compose --profile production up --build
```

The `ENVIRONMENT` and other values above must be saved in `.env` (PowerShell process variables are shown only as examples; Compose reads the root `.env`). Caddy obtains and renews HTTPS certificates for the configured public domain; point DNS to the host and allow inbound ports 80/443. Production configuration requires HTTPS origins and application URL, matching public domain, PostgreSQL, authenticated TLS SMTP, ClamAV, and authenticated shared Redis. The API and database are not exposed publicly; the API host mapping is loopback-only.

Create the first administrator after the API is up:

```powershell
docker compose exec api python -m app.create_admin
```

The command prompts for an administrator email and password; it cannot be performed through public registration. This role must only be granted to a designated institutional operator.

## Tests

```powershell
py -m pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
py -m pytest backend\tests -q
npm test
npm run build
```

Backend unit/API tests use an isolated in-memory SQLite database. PostgreSQL integration tests use a separate disposable `*_test` database and run migrations before truncating test tables. Start the isolated integration profile and run it with:

```powershell
docker compose --profile integration run --build --rm postgres-tests
```

This profile uses a tmpfs-backed test database. Do not point `TEST_DATABASE_URL` at a database containing real data. Frontend tests cover the homepage, mobile navigation, API error presentation, and password recovery form validation. Run both against the actual deployment environment before launch.

## Manual browser checklist

- Check home, about, academics, admissions, faculty, campus, careers, news, contact, and policy routes at desktop and mobile widths.
- Tab through navigation and forms; confirm visible focus, labels, validation, and reduced-motion behavior.
- Confirm sample/placeholder notices remain visible until official details are supplied.
- With the API running, submit a contact inquiry and verify that an unavailable API produces an error rather than a success message.
- Register an applicant, verify the email using Mailpit or the configured provider, sign in, request a password reset, and confirm the one-time reset link can only be used once.
- Create a draft for a published program, upload an approved and malware-free document, verify another applicant cannot list or download it, and submit the draft.
- Provision an administrator through the CLI; review applications, update permitted roles, approve faculty profiles, and publish reviewed content.
- Confirm applicant/student/faculty users cannot perform administrator actions and that student results remain unavailable without an authorized integration.

Latest local verification: 20 backend tests passed and 2 PostgreSQL integration tests were skipped because no `TEST_DATABASE_URL`/PostgreSQL service is available; all 5 frontend tests passed; the frontend production build succeeded; `npm audit --audit-level=low` reported zero vulnerabilities; and a fresh SQLite Alembic upgrade/downgrade round-trip succeeded. Docker/Compose builds, container startup, and PostgreSQL migrations/integration were not verified in this environment.

## API overview

- `POST /api/v1/auth/register` — create applicant account only
- `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- `GET /api/v1/programs`, `/news`, `/events`, `/notices`
- `POST /api/v1/contact`
- `POST /api/v1/applications`, `GET /api/v1/applications/mine`, `POST /api/v1/applications/{id}/submit`, document uploads
- `/api/v1/admin/*` — administrator-protected content, application status, contact review, and audit-log endpoints

Interactive request/response definitions are generated at `/docs` and `/openapi.json` in non-production environments. Access tokens are short-lived bearer tokens held in tab-scoped session storage; production deployment must use HTTPS. Authentication uses an Authorization header rather than cookies, and CORS credentials are disabled. The API applies request-body and file-size limits. Configure additional trusted origins explicitly.

## Data, migrations, and backups

Run schema changes through Alembic (`alembic upgrade head`) and review migrations before deployment. `docker-compose.yml` persists the PostgreSQL data volume and uploaded document volume; separately back up both using encrypted, access-controlled storage, regularly test restoration, and define retention/deletion policies with the institution. Database backup commands depend on the target hosting provider and are not automated here. Protect backup keys separately from the backups and test recovery procedures against an isolated environment.

Note: the original `0001_initial` migration builds tables from the current SQLAlchemy metadata, rather than representing an immutable historical schema snapshot. The later migrations are designed to tolerate fields/tables already present on a fresh install. Treat migration history carefully when changing models; test both clean installs and upgrades from real supported database revisions before deployment.

Uploaded application files are stored under the configured upload directory, not served as public static files. The implementation validates request size, extension, MIME type, file signature, and scans files through ClamAV; uploads fail closed if the scanner is unavailable. Download routes authorize the applicant who owns the application or a permitted administrator. Production still needs retention controls and a documented document-access workflow; malware scanning does not replace operational incident handling.

## Before production

- Supply verified institutional details, approved images, policy text, program information, and official copy.
- Generate strong unique secrets; configure production PostgreSQL, trusted HTTPS CORS origins, Caddy/domain TLS, secure hosting, monitoring, authenticated Redis rate limits shared across workers, and backup retention.
- Configure authenticated TLS email delivery and ClamAV. Account verification and recovery flows are implemented, but provider deliverability, domain authentication (SPF/DKIM/DMARC), support processes, and brute-force controls suitable for distributed deployments must be verified operationally.
- Review role assignment, audit retention, accessibility, legal requirements, and security with qualified institutional staff.
- Implement and verify faculty/student workflows against authorized systems; this scaffold does not expose attendance, grades, or results.
- Review current dependency advisories and run deployment-specific security, accessibility, and load testing.

Docker Engine/Compose and a PostgreSQL service are required to verify container builds, startup, migrations, and the PostgreSQL integration profile. SQLite test success is not evidence that PostgreSQL or Docker deployment works. This is a functional development starting point, not a certified secure or production-approved institutional system.
