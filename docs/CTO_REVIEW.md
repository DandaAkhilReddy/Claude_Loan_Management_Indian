# CTO Architecture Review -- Indian Loan Analyzer

**Reviewer:** TL9 -- CTO / Final Architecture Judge
**Date:** 2026-02-06
**Branch:** `feat/pais-thesis-framework`
**Verdict:** **PASS (Conditional)**
**Production Readiness Score: 8.2 / 10**

---

## 1. Overall Assessment

The Indian Loan Analyzer codebase demonstrates strong architectural maturity across all six review domains. The separation of concerns is clean (routes -> repos -> services -> core math), security fundamentals are sound, and the India-specific financial logic is correctly implemented. The project is conditionally production-ready with a small number of items requiring attention before a launch to real users.

---

## 2. Critical Issues (Must Fix Before Production)

### CRITICAL-1: Alembic `target_metadata` is `None`
**File:** `backend/alembic/env.py` (line 14)
```python
target_metadata = None  # Will be set to Base.metadata by Team 2
```
**Impact:** Alembic autogenerate (`alembic revision --autogenerate`) will produce empty migrations. No schema changes will ever be detected. This is a blocking issue for any database migration workflow.
**Fix:** Import `Base` from `app.db.models` and set `target_metadata = Base.metadata`.

### CRITICAL-2: Docker Compose uses default Postgres credentials
**File:** `docker-compose.yml` (lines 9-10)
```yaml
POSTGRES_USER: postgres
POSTGRES_PASSWORD: postgres
```
**Impact:** Hardcoded default credentials in the orchestration file. While `.env` is correctly gitignored, the `docker-compose.yml` itself is committed with `postgres:postgres`. Any exposed port 5432 is immediately vulnerable.
**Fix:** Use `${POSTGRES_PASSWORD}` environment variable substitution referencing `.env`.

### CRITICAL-3: Rate limiter is in-memory only -- not production-safe
**File:** `backend/app/api/middleware.py` (lines 26-53)
```python
self.requests: dict[str, list[float]] = defaultdict(list)
```
**Impact:** In a multi-worker/multi-container deployment, each process maintains its own rate limit state. An attacker can exceed the limit by a factor equal to the number of workers. The `requests` dict also grows unboundedly if client IPs are not cleaned up (though cleanup does exist per-request, the dict keys themselves are never pruned).
**Fix:** Use Redis-backed rate limiting (e.g., `slowapi` with Redis) or Azure API Management rate policies for production.

---

## 3. Minor Issues (Nice to Fix)

### MINOR-1: `Loan.delete()` is a hard delete, not soft delete
**File:** `backend/app/api/routes/loans.py` (line 80 docstring says "soft delete")
**File:** `backend/app/db/repositories/loan_repo.py` (lines 54-60)
The docstring says "soft delete by marking as closed" but the implementation calls `session.delete(loan)` -- a hard delete. Either the docstring is wrong or the implementation needs to set `loan.status = "closed"` instead.

### MINOR-2: Scanner service `analyze_document` is synchronous-blocking
**File:** `backend/app/services/scanner_service.py` (lines 137-142)
```python
poller = self.client.begin_analyze_document(...)
result = poller.result()  # Blocks the event loop
```
`DocumentIntelligenceClient` is the sync client. The `poller.result()` call blocks the async event loop. For production, use `DocumentIntelligenceAsyncClient` or run in `asyncio.to_thread()`.

### MINOR-3: TTS SSML input not sanitized
**File:** `backend/app/services/tts_service.py` (line 53)
```python
<prosody rate='0.9'>{text}</prosody>
```
User-controlled text is interpolated directly into SSML XML. If the AI-generated text contains XML special characters (`<`, `>`, `&`), the SSML will break or potentially be exploited. The text should be XML-escaped before interpolation.

### MINOR-4: `scan_repo.update_status` lacks user_id scoping
**File:** `backend/app/db/repositories/scan_repo.py` (lines 32-42)
The `update_status` method queries by `job_id` only, without `user_id` filtering. While the calling code in `scanner.py` first validates ownership via `get_by_id(job_id, user_id)`, the repository method itself is unscoped. A defense-in-depth fix would add `user_id` to the WHERE clause.

### MINOR-5: `financial_math.reverse_emi_tenure` uses `math.log(float())` -- breaks Decimal precision chain
**File:** `backend/app/core/financial_math.py` (line 218)
The function converts Decimal to float for `math.log()`, which is acceptable for this reverse-engineering use case but breaks the otherwise strict Decimal discipline. Consider documenting this as an intentional precision tradeoff.

### MINOR-6: Proportional strategy rounding remainder allocation
**File:** `backend/app/core/strategies.py` (lines 234-237)
Remainder from rounding is assigned to the largest-balance loan, which is correct but could theoretically result in a tiny overpayment if `remainder + existing allocation > outstanding_principal`. The `min()` cap is missing on the remainder addition.

### MINOR-7: Frontend locales missing scanner and loan-detail keys
**File:** `frontend/src/locales/en.json`
The locales file has keys for `app`, `nav`, `common`, `dashboard`, `optimizer`, and `emi` sections but is missing dedicated sections for `scanner` (upload, processing, confirm steps) and `loanDetail` (amortization labels). These strings may be hardcoded in components.

---

## 4. Architecture Strengths

### 4.1 Security -- STRONG
| Check | Status | Notes |
|-------|--------|-------|
| Firebase server-side token validation | PASS | `auth_service.py` uses `firebase_admin.auth.verify_id_token()` correctly |
| Bearer token extraction in `deps.py` | PASS | Proper `Authorization: Bearer` parsing with 401 on failure |
| User scoping on loan queries | PASS | Every repo method takes `user_id` and includes it in WHERE clause |
| File upload type validation | PASS | Whitelist of `application/pdf`, `image/png`, `image/jpeg`, `image/jpg` |
| File upload size validation | PASS | 10MB hard limit with content read + length check |
| Rate limiting on upload endpoint | PASS | In-memory rate limiter present (see CRITICAL-3 for production caveat) |
| No hardcoded secrets in `config.py` | PASS | All secrets sourced from env vars via `pydantic-settings` |
| `.gitignore` coverage | PASS | Covers `.env`, `node_modules/`, `__pycache__/`, `.venv/`, `.claude/` |
| Optional auth for public endpoints | PASS | `get_optional_user` dependency for unauthenticated access |

### 4.2 Financial Math Engine -- STRONG
| Check | Status | Notes |
|-------|--------|-------|
| EMI formula correctness | PASS | Standard reducing-balance: `P * r * (1+r)^n / ((1+r)^n - 1)` |
| Decimal precision throughout | PASS | `getcontext().prec = 28`, all monetary values use `Decimal` with `ROUND_HALF_UP` |
| PAISA-level rounding | PASS | `Decimal("0.01")` constant used for quantization |
| Zero-rate edge case | PASS | Handled in `calculate_emi()` with simple division |
| Amortization with prepayments | PASS | Supports both monthly and lump-sum prepayments |
| Final month adjustment | PASS | Handles case where balance < EMI in last month |
| Reverse EMI (rate from EMI) | PASS | Binary search with configurable precision |
| Affordability calculator | PASS | Correct inverse EMI formula |

### 4.3 Multi-Loan Optimization -- STRONG
| Check | Status | Notes |
|-------|--------|-------|
| 4 strategies implemented | PASS | Avalanche, Snowball, SmartHybrid, Proportional |
| SmartHybrid post-tax effective rates | PASS | Accounts for 24(b), 80E, 80C with configurable tax bracket |
| 3-EMI quick-win bump | PASS | Loans within 3 months of closure promoted to top priority |
| Foreclosure charge penalty | PASS | Added as friction factor to effective rate |
| Freed-EMI rollover (relay race) | PASS | `freed_emi_pool += loan.emi_amount` on payoff, added to budget each month |
| Prepayment penalty handling | PASS | Net payment computed after percentage penalty deduction |
| Baseline comparison | PASS | All strategies compared against minimum-payment-only baseline |
| Max simulation cap | PASS | 600 months (50 years) prevents infinite loops |

### 4.4 Database Design -- STRONG
| Check | Status | Notes |
|-------|--------|-------|
| All 7 tables present | PASS | `users`, `loans`, `scan_jobs`, `repayment_plans`, `document_embeddings`, `consent_records`, `audit_logs` |
| pgvector column | PASS | `Vector(1536)` on `document_embeddings.embedding` -- matches `text-embedding-3-small` |
| Composite indexes | PASS | `ix_loans_user_status`, `ix_loans_user_type`, `ix_embeddings_source` |
| UUID primary keys | PASS | `uuid.uuid4` defaults on all tables |
| JSONB for flexible data | PASS | Used for `extracted_fields`, `confidence_scores`, `config`, `results`, `details` |
| Async session with cleanup | PASS | `try/commit/except rollback/finally close` pattern in `get_db()` |
| Cascade deletes | PASS | `ondelete="CASCADE"` on foreign keys, `cascade="all, delete-orphan"` on relationships |
| Tax benefit columns on Loan | PASS | `eligible_80c`, `eligible_24b`, `eligible_80e`, `eligible_80eea` |
| Consent/Audit tables | PASS | DPDP Act compliance infrastructure present |
| pgvector Docker image | PASS | `pgvector/pgvector:pg16` |

### 4.5 Frontend Architecture -- STRONG
| Check | Status | Notes |
|-------|--------|-------|
| Code-splitting with lazy imports | PASS | All 7 pages use `React.lazy()` with `Suspense` fallback |
| Indian numbering format | PASS | Custom `formatINR()` produces `1,00,000` (not `100,000`) |
| Compact format (Cr/L/K) | PASS | `formatINRCompact()` for dashboard cards |
| 4-step optimizer wizard | PASS | Select Loans -> Set Budget -> Choose Strategy -> Results |
| i18n infrastructure | PASS | `react-i18next` with `en.json` locale file |
| Error boundary | PASS | Top-level `ErrorBoundary` wrapping entire app |
| Protected routes | PASS | `ProtectedRoute` component guards authenticated pages |
| TanStack Query mutations | PASS | `useMutation` for optimizer API call with loading state |

### 4.6 Azure Integration -- STRONG
| Check | Status | Notes |
|-------|--------|-------|
| Document Intelligence: Layout model | PASS | Uses `"prebuilt-layout"` (NOT `prebuilt-bankStatement.us`) |
| Indian bank regex patterns | PASS | 10 major Indian banks + 6 loan types with normalization maps |
| GPT-4o-mini deployment | PASS | `azure_openai_deployment = "gpt-4o-mini"` with Hinglish system prompt |
| Indian TTS voices | PASS | `en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`, `te-IN-ShrutiNeural` |
| Central India region | PASS | Both TTS and Translator configured for `centralindia` |
| Translator with region header | PASS | `Ocp-Apim-Subscription-Region` header correctly set |
| Graceful degradation | PASS | All Azure services return fallback values when unconfigured |
| RAG with pgvector | PASS | Cosine similarity search in `embedding_repo.py` with context injection |

---

## 5. Detailed File-by-File Findings

### `backend/app/api/deps.py`
- Firebase token verified server-side via `verify_firebase_token()` -- PASS
- Bearer prefix check before extraction -- PASS
- User upsert on every authenticated request (idempotent) -- PASS
- Optional auth dependency for public routes -- PASS

### `backend/app/api/routes/loans.py`
- All 5 endpoints (list, create, get, update, delete) require `get_current_user` -- PASS
- Every repo call includes `user.id` for scoping -- PASS
- Amortization endpoint converts to `Decimal` for math engine -- PASS
- Proper 404 handling on missing resources -- PASS

### `backend/app/api/routes/scanner.py`
- File type whitelist (`ALLOWED_TYPES`) -- PASS
- File size limit (10MB, `MAX_FILE_SIZE`) -- PASS
- Content read before size check (reads entire file into memory) -- acceptable for 10MB limit
- User scoping on scan job retrieval -- PASS
- Confirm endpoint creates loan with `source="scan"` linkage -- PASS

### `backend/app/api/middleware.py`
- Request logging with timing -- PASS
- Rate limiting on `/api/scanner/upload` only -- PASS (scoped correctly)
- Global error handler prevents stack trace leakage -- PASS
- In-memory rate limiter -- see CRITICAL-3

### `backend/app/config.py`
- All secrets loaded from environment via `pydantic-settings` -- PASS
- No hardcoded API keys or passwords -- PASS
- Sensible defaults (centralindia region, gpt-4o-mini deployment) -- PASS

### `backend/app/core/financial_math.py`
- EMI formula mathematically verified -- PASS
- Full Decimal pipeline with 28-digit precision -- PASS
- Edge cases (zero rate, zero principal, zero tenure) handled -- PASS
- Amortization schedule with cumulative tracking -- PASS

### `backend/app/core/strategies.py`
- 4 strategies with clean ABC interface -- PASS
- SmartHybrid: `effective_rate = nominal_rate - (nominal_rate * tax_bracket)` -- PASS
- 80C gets 50% weight (principal deduction, not interest) -- correctly differentiated
- Factory function with validation -- PASS

### `backend/app/core/optimization.py`
- Month-by-month simulation with freed-EMI pool -- PASS
- Deep copy of loan snapshots prevents mutation -- PASS
- Prepayment penalty deducted from net payment -- PASS
- Baseline comparison for savings calculation -- PASS
- Lump-sum support per month -- PASS

### `backend/app/db/models.py`
- 7 tables with full column definitions -- PASS
- pgvector `Vector(1536)` column -- PASS
- Composite indexes for query performance -- PASS
- DPDP-ready consent and audit tables -- PASS

### `backend/app/db/session.py`
- Async engine with connection pooling (5+10) -- PASS
- Session lifecycle: commit on success, rollback on error, close always -- PASS
- `expire_on_commit=False` for detached object access -- PASS

### `backend/app/services/scanner_service.py`
- Uses `"prebuilt-layout"` model -- PASS
- Regex extraction with Indian bank/loan patterns -- PASS
- Bank and loan type normalization -- PASS
- Table text extraction alongside content text -- PASS

### `backend/app/services/ai_service.py`
- AsyncAzureOpenAI client -- PASS
- Hinglish system prompt with Indian numbering instruction -- PASS
- Relay race metaphor in strategy explanation -- PASS
- RAG Q&A with context injection -- PASS

### `backend/app/services/tts_service.py`
- Indian voice names (Neerja, Swara, Shruti) -- PASS
- SSML with prosody rate control -- PASS
- Base64 audio response -- PASS

### `backend/app/services/translator_service.py`
- Central India region -- PASS
- EN/HI/TE support -- PASS
- Language detection endpoint -- PASS
- Graceful fallback to original text on failure -- PASS

### `docker-compose.yml`
- pgvector image (`pgvector/pgvector:pg16`) -- PASS
- Persistent volume for data -- PASS
- Init scripts directory mounted -- PASS

### `backend/alembic/env.py`
- Async migration support -- PASS
- `target_metadata = None` -- CRITICAL-1

### `.env.example` files
- Backend: all 13 vars documented -- PASS
- Frontend: all 6 Firebase vars documented -- PASS

### `.gitignore`
- `.env`, `node_modules/`, `__pycache__/`, `.venv/`, `.claude/` -- PASS
- IDE files, build artifacts, logs -- PASS

---

## 6. Production Readiness Scorecard

| Domain | Score | Weight | Weighted |
|--------|-------|--------|----------|
| Security & Auth | 9/10 | 25% | 2.25 |
| Financial Math Accuracy | 10/10 | 20% | 2.00 |
| Database Design | 9/10 | 15% | 1.35 |
| Azure Integration | 9/10 | 15% | 1.35 |
| Frontend Architecture | 8/10 | 10% | 0.80 |
| Infrastructure & DevOps | 7/10 | 10% | 0.70 |
| Code Quality & Patterns | 8/10 | 5% | 0.40 |
| **Total** | | **100%** | **8.85** |

**Adjusted Score (accounting for CRITICAL issues): 8.2 / 10**

---

## 7. Summary

### What must happen before production launch:
1. Fix Alembic `target_metadata` to enable migration autogeneration
2. Externalize Docker Compose Postgres credentials to `.env`
3. Replace in-memory rate limiter with Redis-backed solution for multi-worker deployment

### What should happen soon after launch:
4. Fix soft-delete vs hard-delete inconsistency on loans
5. Use async Document Intelligence client to avoid event loop blocking
6. Sanitize TTS SSML input for XML special characters
7. Add user_id scoping to `scan_repo.update_status` for defense-in-depth
8. Add missing i18n keys for scanner and loan detail pages

### Architecture verdict:
The codebase is well-engineered for an India-focused financial application. The financial math engine is precise to the paisa, the multi-loan optimizer with freed-EMI rollover is a genuine product differentiator, and the Azure service integration is thoughtfully designed with graceful degradation. The security posture is strong with proper Firebase token validation, user scoping, and file upload controls. The three critical issues identified are straightforward to fix and do not indicate systemic architectural problems.

**Recommendation: APPROVED for production with the 3 critical fixes applied.**

---

*Report generated by TL9 Architecture Review on 2026-02-06*
