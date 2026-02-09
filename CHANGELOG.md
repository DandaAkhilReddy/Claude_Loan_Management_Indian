# Changelog

All notable changes to this project are documented here.

## [1.2.0] - 2026-02-09

### Added

- **80+ new tests** across 12 test files (627 total: 464 backend + 163 frontend)
  - Frontend: useAuth hook, API interceptors, LoginPage, ProtectedRoute, ErrorBoundary, Firebase config, auth store
  - Backend: auth integration, loans integration, EMI integration, scanner integration, optimizer integration
- MIT LICENSE file

### Fixed

- i18n locize promotional console message — inline script in `index.html` patches `console.log` before ES module chunks load
- TypeScript build excluding test files via `tsconfig.app.json`

### Removed

- `docs/reference/` — 24MB of planning PDFs (kept repo lean)

## [1.1.0] - 2026-02-09

### Added

- Firebase Email/Password authentication + Google Sign-In
- `LoginPage` with sign-in, sign-up, and forgot-password views
- `ProtectedRoute` component with loading spinner
- `ErrorBoundary` with retry functionality
- Zustand auth store (`useAuthStore`)
- API request interceptor (auto-attach Firebase token)
- API response interceptor (401 redirect, 429/500 toast, network error handling)
- COOP header (`same-origin-allow-popups`) for Firebase popup sign-in
- i18n locize console message suppression
- Offline detection banner (`OfflineBanner`)

### Fixed

- `asyncpg` SSL parameter: use `?ssl=require` not `?sslmode=require`
- Azure Container Registry managed identity (AcrPull role) replacing password auth
- CI/CD pipeline: fallback DATABASE_URL for tests, `npm install` over `npm ci`
- nginx proxy `Host` header + SSL for Azure backend

## [1.0.0] - 2026-02-06

### Added

- **Smart Optimizer** — 4 repayment strategies (Avalanche, Snowball, Smart Hybrid, Proportional) with freed-EMI relay race cascade
- **Document Scanner** — Azure Document Intelligence for loan document extraction (PDF/PNG/JPG)
- **EMI Calculator** — calculate, reverse-calculate, and affordability endpoints (public, no auth)
- **AI Advisor** — Azure OpenAI loan explanations, strategy explanations, and Q&A
- **Trilingual support** — English, Hindi, Telugu (+ Spanish) with i18next
- **Tax-aware optimization** — India tax deductions (80C, 24b, 80E, 80EEA) under old and new regimes
- **USA market support** — federal tax brackets, mortgage/student loan deductions, filing status
- **Full REST API** — 25+ endpoints for loans, optimizer, scanner, EMI, AI, auth
- **Database** — PostgreSQL 16 + pgvector with 7 SQLAlchemy models, Alembic migrations
- **Azure deployment** — ACR, App Service (backend + frontend), PostgreSQL Flexible Server
- **CI/CD** — GitHub Actions: test → build → deploy on push to main
- **CTO architecture review** — 8.2/10 score, all critical issues resolved
- 409 backend tests + 66 frontend tests
- Docker Compose for local development and production
- Azure provisioning script (`infra/azure-deploy.sh`)
- Smoke test script (`scripts/smoke-test.sh`)
