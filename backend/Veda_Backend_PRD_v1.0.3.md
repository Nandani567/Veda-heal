# Veda — Backend Product Requirements Document

> **Version:** 1.0.3 | **Status:** Draft / Phase 1 | **Classification:** Internal – Confidential

---

## Table of Contents

1. [Document Information](#1-document-information)
2. [Executive Summary](#2-executive-summary)
3. [Backend Overview](#3-backend-overview)
4. [Technology Stack](#4-technology-stack)
5. [REST Architecture & API Design](#5-rest-architecture--api-design)
6. [Application Architecture](#6-application-architecture)
7. [Data Models](#7-data-models)
8. [VedaCore AI Service](#8-vedacore-ai-service)
9. [Inventory & Vault Logic](#9-inventory--vault-logic)
10. [API Endpoint Reference](#10-api-endpoint-reference)
11. [Security Model](#11-security-model)
12. [Notification System](#12-notification-system)
13. [Success Metrics](#13-success-metrics)
14. [Phased Delivery Roadmap](#14-phased-delivery-roadmap)
15. [Risk Register](#15-risk-register)
16. [Testing Strategy](#16-testing-strategy)
17. [Open Questions & Dependencies](#17-open-questions--dependencies)
18. [Glossary](#18-glossary)

---

## 1. Document Information

| Field            | Value                                  |
|------------------|----------------------------------------|
| Project Name     | Veda                                   |
| Version          | 1.0.3                                  |
| Status           | Draft / Phase 1                        |
| Author           | Veda Engineering                       |
| Last Updated     | March 2026                             |
| Reviewers        | Product, Engineering, QA Leads         |
| Classification   | Internal – Confidential                |
| Stack            | Python (FastAPI) + PostgreSQL + SQLAlchemy + OpenAI/Gemini |

---

## 2. Executive Summary

Veda is a high-performance, asynchronous REST API backend designed to power an intelligent medication management mobile application. It serves as the cognitive and operational core, enabling users to add, track, and manage their medications through natural language conversations while ensuring accurate inventory tracking and timely reminder notifications.

### 2.1 Vision Statement

To eliminate medication non-adherence through an intelligent, conversational, and proactive backend system that understands natural language, tracks real-time inventory, and delivers habit-aware notifications — making complex medication schedules effortless for every user.

### 2.2 Core Value Propositions

- **VedaCore AI Extraction** — Convert natural language (e.g. *"I take 10mg Metformin twice daily with food"*) into fully structured medication records with zero manual form-filling.
- **Proactive Vault Inventory** — Real-time pill stock decrementation and intelligent refill forecasting based on actual consumption patterns.
- **Contextual Dose Alerts** — Habit-aware notifications that adapt to user behaviour including snooze patterns and skip history.
- **Secure & Stateless API** — JWT-based stateless authentication with layered middleware for logging, auth, and error handling.

---

## 3. Backend Overview

### 3.1 Purpose

The Veda backend provides the intelligent processing layer between the React Native mobile client and all data persistence, AI, and notification systems. It is stateless, horizontally scalable, and designed for cloud deployment behind a reverse proxy.

### 3.2 Core Objectives

1. **VedaCore Extraction** — Extract structured medication data (name, dosage, frequency, duration) from natural language using LLM function calling with strict JSON schema validation.
2. **Proactive Inventory (Vault Logic)** — Atomically decrement `current_stock` on each `TAKEN` log event, calculate days-remaining forecasts, and trigger low-stock alerts at a configurable threshold.
3. **Contextual Alerts** — Schedule and dispatch habit-aware push notifications using APScheduler, respecting user snooze and skip patterns to reduce alert fatigue.
4. **Secure Profile Management** — Multi-user support with JWT authentication and per-user medication data isolation.
5. **Observability** — Structured JSON logging, request tracing middleware, and async-compatible error handling for production diagnostics.

---

## 4. Technology Stack

| Layer            | Technology                                                                 |
|------------------|----------------------------------------------------------------------------|
| Runtime          | Python 3.12+ (Typed with Pydantic v2)                                     |
| Framework        | FastAPI (Asynchronous REST)                                                |
| Database         | PostgreSQL (Relational) with SQLAlchemy 2.0 (Async ORM)                   |
| AI / NLP         | OpenAI GPT-4o-mini via Instructor library for structured extraction        |
| Task Management  | APScheduler — automated alert triggers & scheduled jobs                    |
| Migrations       | Alembic — schema versioning and rollback support                           |
| Auth             | JWT (JSON Web Tokens) — stateless per-request authentication               |
| Testing          | Pytest (Unit & Integration) with async support                             |

### 4.1 Stack Rationale

**FastAPI** — Selected for native async support (`asyncio`), automatic OpenAPI schema generation, and first-class Pydantic v2 integration. Delivers developer velocity and production-grade performance without a separate documentation layer.

**PostgreSQL + SQLAlchemy 2.0 Async** — ACID compliance, JSONB support for flexible frequency schedules, and row-level locking (`SELECT FOR UPDATE`) for safe concurrent stock decrementation. SQLAlchemy's async engine with `asyncpg` driver handles high-concurrency mobile backends efficiently.

**OpenAI GPT-4o-mini via Instructor** — Cost-effective balance of accuracy and latency for medication extraction. Instructor enforces structured output via JSON schema function calling, eliminating free-form LLM responses and ensuring >94% parse accuracy on well-formed inputs.

---

## 5. REST Architecture & API Design

### 5.1 The Six REST Constraints

1. **Uniform Interface** — All endpoints follow consistent URI naming (`/api/v1/resource/{id}`), standardized JSON response envelopes, and uniform content negotiation headers.
2. **Client-Server** — React Native frontend and FastAPI backend are fully decoupled. The client owns UI state; the server owns business logic and data persistence.
3. **Stateless** — Every HTTP request carries all information required for processing — JWT access tokens in the `Authorization` header. No server-side session state is maintained.
4. **Cacheable** — `GET` endpoints include `Cache-Control` and `ETag` headers where appropriate. The `/vault` endpoint supports conditional requests (`If-None-Match`) to minimize redundant data transfer.
5. **Layered System** — Middleware pipeline handles cross-cutting concerns: request logging, JWT validation, rate limiting, CORS, and global error formatting — independent of business logic.
6. **Code on Demand (Optional)** — Not utilized in Phase 1. Deferred to future consideration.

### 5.2 Richardson Maturity Model

Veda targets **Level 2 (HTTP Verbs)** for Phase 1 with a defined path to **Level 3 (HATEOAS)** in Phase 4.

| Level | Description | Veda Status |
|-------|-------------|-------------|
| Level 0 | Single URI | ❌ Not used |
| Level 1 | Distinct resource URIs (`/vault`, `/veda/chat`, `/profiles`) | ✅ Implemented |
| Level 2 | Proper HTTP verbs + semantic status codes | ✅ Implemented |
| Level 3 | HATEOAS — hypermedia-driven navigation | 🔜 Phase 4 |

### 5.3 HTTP Methods & Status Codes

| Method   | Usage                        | Success          | Error              |
|----------|------------------------------|------------------|--------------------|
| `GET`    | Retrieve vault items / logs  | `200 OK`         | `404 Not Found`    |
| `POST`   | Process chat / Create entry  | `201 Created`    | `400 Bad Request`  |
| `PATCH`  | Update inventory / Status    | `200 OK`         | `422 Unprocessable`|
| `DELETE` | Remove medication            | `204 No Content` | `404 Not Found`    |

### 5.4 Standard Response Envelope

All API responses are wrapped in a consistent JSON envelope:

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-03-04T10:00:00Z",
    "version": "v1"
  }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "VAULT_NOT_FOUND",
    "message": "Medication entry not found for the given ID.",
    "details": {}
  }
}
```

---

## 6. Application Architecture

### 6.1 Layered Architecture

```
Mobile App (React Native)
        │
        ▼
┌─────────────────────────┐
│   Routes  /api/v1       │  ← HTTP request/response handling only
├─────────────────────────┤
│   Middleware            │  ← Auth, Logging, CORS, Rate Limiting
├─────────────────────────┤
│   Controllers / Schemas │  ← Pydantic v2 request validation
├─────────────────────────┤
│   Services              │  ← Business Logic (VedaCore, Inventory, Alerts)
├─────────────────────────┤
│   Models (SQLAlchemy)   │  ← ORM data representation
├─────────────────────────┤
│   PostgreSQL            │  ← Persistence layer
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│   VedaCore AI Service   │  ← OpenAI GPT-4o-mini + Instructor
└─────────────────────────┘
```

### 6.2 Directory Structure

```
/backend
├── app/
│   ├── api/
│   │   └── v1/                  # Routes & endpoint definitions
│   │       ├── auth.py
│   │       ├── vault.py
│   │       ├── veda.py
│   │       ├── alerts.py
│   │       └── profiles.py
│   ├── core/                    # Security, Config, JWT utilities
│   │   ├── config.py
│   │   ├── security.py
│   │   └── jwt.py
│   ├── db/                      # Async session factory & base
│   │   ├── session.py
│   │   └── base.py
│   ├── models/                  # SQLAlchemy ORM classes
│   │   ├── vault.py
│   │   ├── veda_log.py
│   │   ├── user_profile.py
│   │   └── alert.py
│   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── vault.py
│   │   ├── veda.py
│   │   └── auth.py
│   ├── services/                # Business logic layer
│   │   ├── veda_core.py         # AI extraction service
│   │   ├── inventory.py         # Stock decrement & forecasting
│   │   └── notifications.py     # APScheduler alert dispatch
│   └── main.py                  # FastAPI app entry point
├── migrations/                  # Alembic versioned migration files
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

### 6.3 Middleware Pipeline Order

1. **CORS Middleware** — Preflight and origin validation
2. **Request ID Injection** — Unique trace ID per request
3. **Structured Logging Middleware** — Log method, path, status, latency
4. **JWT Authentication Middleware** — Validate and decode Bearer token
5. **Rate Limiting Middleware** — Per-user request throttling
6. **Global Exception Handler** — Normalize all exceptions to standard error envelope

---

## 7. Data Models

### 7.1 Vault (Medication Cabinet)

The central entity. Each row represents one medication prescription for one user. `current_stock` is decremented atomically on every `TAKEN` log event.

| Field            | Type      | Constraint   | Description                                         |
|------------------|-----------|--------------|-----------------------------------------------------|
| `id`             | UUID      | PRIMARY KEY  | Auto-generated unique identifier                    |
| `user_id`        | UUID      | FOREIGN KEY  | Reference to the owning user profile                |
| `name`           | STRING    | NOT NULL     | Medication name (e.g., Metformin)                   |
| `dosage`         | STRING    | NOT NULL     | Strength with unit (e.g., 500mg)                    |
| `frequency`      | JSONB     | NOT NULL     | Schedule object: times, days, interval              |
| `current_stock`  | INTEGER   | DEFAULT 0    | Auto-decremented on each `TAKEN` log                |
| `total_stock`    | INTEGER   | NOT NULL     | Initial quantity dispensed                          |
| `low_stock_limit`| INTEGER   | DEFAULT 7    | Threshold count that triggers a refill alert        |
| `start_date`     | DATETIME  | NOT NULL     | ISO 8601 — first dose date                          |
| `end_date`       | DATETIME  | NULLABLE     | Optional course end date                            |
| `notes`          | TEXT      | NULLABLE     | Free-text patient / prescriber notes                |
| `deleted_at`     | DATETIME  | NULLABLE     | Soft-delete timestamp (preserves log FK integrity)  |
| `created_at`     | DATETIME  | AUTO         | Record creation timestamp                           |

**Business Rules:**
- `current_stock` must never go below `0`. Decrement operations use `SELECT FOR UPDATE` within a transaction.
- When `current_stock <= low_stock_limit`, the alert service schedules a refill notification within 24 hours.
- Soft-deletion via `deleted_at` is used instead of hard `DELETE` to preserve log referential integrity.

### 7.2 VedaLogs (Interaction History)

Records every dose interaction event. Source of truth for adherence reporting, stock reconciliation, and habit analysis.

| Field      | Type      | Constraint   | Description                                      |
|------------|-----------|--------------|--------------------------------------------------|
| `log_id`   | UUID      | PRIMARY KEY  | Unique log event identifier                      |
| `entry_id` | UUID      | FOREIGN KEY  | References `Vault.id`                            |
| `user_id`  | UUID      | FOREIGN KEY  | References `UserProfile.id`                      |
| `status`   | ENUM      | NOT NULL     | `TAKEN` \| `SKIPPED` \| `SNOOZED`               |
| `dose_time`| DATETIME  | NOT NULL     | Scheduled dose time (ISO 8601)                   |
| `logged_at`| DATETIME  | AUTO         | Actual interaction timestamp                     |
| `note`     | TEXT      | NULLABLE     | Optional patient note per event                  |

**Business Rules:**
- A `TAKEN` log always triggers an atomic decrement of the referenced Vault entry's `current_stock`.
- `SKIPPED` or `SNOOZED` logs do **not** decrement stock.
- `SNOOZED` logs must be accompanied by a re-schedule timestamp (stored in `note` JSONB in Phase 1; promoted to a dedicated column in Phase 2).
- Logs are **immutable** once created. Corrections are handled by creating a compensating log entry.

### 7.3 UserProfile

| Field                      | Type    | Constraint       | Description                              |
|----------------------------|---------|------------------|------------------------------------------|
| `id`                       | UUID    | PRIMARY KEY      | User identifier                          |
| `email`                    | STRING  | UNIQUE, NOT NULL | Login credential                         |
| `hashed_password`          | STRING  | NOT NULL         | Bcrypt hash (cost factor 12)             |
| `display_name`             | STRING  | NULLABLE         | User's preferred name                    |
| `timezone`                 | STRING  | DEFAULT: UTC     | Used for dose scheduling                 |
| `notification_preferences` | JSONB   | NULLABLE         | Push token, quiet hours, frequency prefs |
| `created_at / updated_at`  | DATETIME| AUTO             | Auto-managed timestamps                  |

---

## 8. VedaCore AI Service

### 8.1 Overview

VedaCore is the AI extraction service that transforms unstructured natural language medication descriptions into typed, validated Pydantic models ready for database insertion. It is the primary differentiator of the Veda platform.

### 8.2 Extraction Pipeline

```
User Input (NL text)
        │
        ▼
System Prompt Construction
        │
        ▼
OpenAI GPT-4o-mini (via Instructor — JSON schema enforcement)
        │
        ▼
Confidence Scoring per field (threshold: 0.80)
        │
        ▼
Pydantic VedaExtractionResult Validation
        │
        ├─── Fields below 0.80 confidence → Flagged for user confirmation
        │
        └─── All fields valid → Return to client for Vault insertion
```

**Step-by-step:**

1. **Input** — User submits free-text via `POST /veda/chat` (e.g., *"I take 500mg Metformin twice a day with breakfast and dinner"*).
2. **System Prompt Construction** — Service builds a system prompt instructing GPT-4o-mini to extract medication data strictly according to `VedaExtractionSchema`.
3. **Instructor Call** — Instructor wraps the OpenAI SDK call, enforcing the schema via function calling mode. Retries on validation failure (max 2 retries).
4. **Confidence Scoring** — Each extracted field receives a confidence score (`0.0–1.0`). Fields below `0.80` are flagged for user confirmation.
5. **Pydantic Validation** — Raw LLM output is parsed by `VedaExtractionResult`. Any type or constraint violation raises `422` with field-level details.
6. **Response** — Validated extraction result returned to mobile client for confirmation before Vault insertion.

### 8.3 VedaExtractionSchema Fields

| Field                    | Type          | Required | Description                                    |
|--------------------------|---------------|----------|------------------------------------------------|
| `medication_name`        | string        | ✅       | Canonical drug name                            |
| `dosage_value`           | float         | ✅       | Numeric dose amount                            |
| `dosage_unit`            | enum          | ✅       | `mg` \| `mcg` \| `ml` \| `g` \| `IU`         |
| `frequency_times_per_day`| integer       | ✅       | Number of daily doses                          |
| `frequency_schedule`     | list[string]  | ✅       | Time labels (e.g., `["morning", "evening"]`)   |
| `food_instructions`      | enum          | ❌       | `WITH_FOOD` \| `WITHOUT_FOOD` \| `NO_RESTRICTION` |
| `duration_days`          | integer       | ❌       | Course length in days                          |
| `prescriber_notes`       | string        | ❌       | Any additional instructions                    |

### 8.4 Error Handling

| Scenario                         | Response                                              |
|----------------------------------|-------------------------------------------------------|
| LLM timeout (> 5s)               | `503 Service Unavailable` with `Retry-After` header   |
| Schema failure after 2 retries   | `422` with partial extraction and flagged fields      |
| Ambiguous input                  | `200` with low-confidence flags; mobile prompts user  |
| OpenAI API error                 | `502 Bad Gateway` — full error context logged         |

---

## 9. Inventory & Vault Logic

### 9.1 Stock Decrement (Atomic)

Every `TAKEN` log event triggers the following atomic sequence within a single PostgreSQL transaction:

```sql
BEGIN;
  SELECT current_stock FROM vault WHERE id = :entry_id FOR UPDATE;
  -- Raise 409 Conflict if current_stock = 0
  UPDATE vault SET current_stock = current_stock - 1 WHERE id = :entry_id;
  INSERT INTO veda_logs (...) VALUES (...);
  -- If current_stock - 1 <= low_stock_limit: enqueue refill alert
COMMIT;
```

### 9.2 Refill Forecast

The inventory service calculates a projected depletion date for each medication:

```python
days_remaining = current_stock / doses_per_day
estimated_depletion_date = today + timedelta(days=days_remaining)
```

This forecast is included in `GET /veda/inventory/summary` and updated on every stock change event.

### 9.3 Low Stock Alert Logic

- **Trigger:** `current_stock <= low_stock_limit` after a `TAKEN` log.
- **Action:** Alert record created in `alerts` table with `type=LOW_STOCK`, `severity=WARNING`.
- **Dispatch:** APScheduler dispatches push notification within 1 hour of trigger.
- **Deduplication:** Only one active `LOW_STOCK` alert per vault entry at any time.

---

## 10. API Endpoint Reference

All endpoints are prefixed with `/api/v1`. Authentication is required on all endpoints except `/auth/register` and `/auth/login`.

### 10.1 Auth Endpoints

| Method | Endpoint         | Status | Description                                  |
|--------|------------------|--------|----------------------------------------------|
| `POST` | `/auth/register` | `201`  | Register new user account                    |
| `POST` | `/auth/login`    | `200`  | Authenticate user; return JWT                |
| `POST` | `/auth/refresh`  | `200`  | Refresh access token using refresh token     |

### 10.2 Vault Endpoints

| Method   | Endpoint       | Status | Description                                  |
|----------|----------------|--------|----------------------------------------------|
| `GET`    | `/vault`       | `200`  | List all medications for authenticated user  |
| `POST`   | `/vault`       | `201`  | Add medication via structured payload        |
| `GET`    | `/vault/{id}`  | `200`  | Retrieve single medication detail            |
| `PATCH`  | `/vault/{id}`  | `200`  | Update medication fields or stock            |
| `DELETE` | `/vault/{id}`  | `204`  | Remove medication and cascade logs           |

### 10.3 VedaCore Endpoints

| Method | Endpoint                   | Status | Description                                        |
|--------|----------------------------|--------|----------------------------------------------------|
| `POST` | `/veda/chat`               | `200`  | Submit NL message; receive VedaCore extraction     |
| `GET`  | `/veda/logs`               | `200`  | Retrieve dose interaction history                  |
| `POST` | `/veda/logs`               | `201`  | Manually log a dose event                          |
| `GET`  | `/veda/inventory/summary`  | `200`  | Real-time stock counts and refill forecasts        |

### 10.4 Alerts & Profile Endpoints

| Method  | Endpoint            | Status | Description                                  |
|---------|---------------------|--------|----------------------------------------------|
| `GET`   | `/alerts/pending`   | `200`  | Fetch unacknowledged notification queue      |
| `PATCH` | `/alerts/{id}/ack`  | `200`  | Acknowledge or dismiss an alert              |
| `GET`   | `/profiles/me`      | `200`  | Get authenticated user profile               |
| `PATCH` | `/profiles/me`      | `200`  | Update profile preferences                   |

### 10.5 Authentication Flow

```
1. Client POSTs credentials → /auth/login
2. Server returns access_token (15-min TTL) + refresh_token (7-day TTL)
3. Client stores tokens in secure storage (not localStorage)
4. All requests include: Authorization: Bearer {access_token}
5. On 401 → POST refresh_token to /auth/refresh for new access_token
6. On logout or 7-day expiry → both tokens invalidated
```

---

## 11. Security Model

### 11.1 Authentication & Authorization

- JWT RS256 asymmetric signing — private key on server, public key distributed to services.
- Access tokens expire after **15 minutes**. Refresh tokens expire after **7 days**.
- All database queries include `user_id = current_user.id` predicate to enforce data isolation.
- Bcrypt password hashing with cost factor **12**.

### 11.2 Input Validation

- All request bodies validated by Pydantic v2 models before reaching service layer.
- SQL injection prevention via SQLAlchemy parameterized queries — no raw SQL string interpolation.
- LLM outputs validated by Instructor schema before persistence — no raw LLM text stored directly.

### 11.3 Data Classification

- Medication data and health logs: **SENSITIVE HEALTH DATA**
- Database encryption at rest via PostgreSQL TDE or cloud provider managed encryption.
- All API communications require **TLS 1.2+** (enforced at load balancer).
- PII fields (`email`, `display_name`) excluded from application logs.

### 11.4 Rate Limiting

| Endpoint             | Limit                                                    |
|----------------------|----------------------------------------------------------|
| `/veda/chat`         | 10 requests / minute / user (AI cost protection)         |
| Auth endpoints       | 5 failed attempts / IP / 15 min → temporary block        |
| All other endpoints  | 120 requests / minute / user                             |

---

## 12. Notification System

### 12.1 APScheduler Integration

APScheduler is configured with a **persistent PostgreSQL job store**, ensuring scheduled alerts survive server restarts. Jobs are defined per medication schedule and per user.

### 12.2 Alert Types

| Alert Type        | Trigger                                                  | Behaviour                                                |
|-------------------|----------------------------------------------------------|----------------------------------------------------------|
| `DOSE_DUE`        | Each scheduled dose time                                 | Respects user quiet hours from `notification_preferences`|
| `LOW_STOCK`       | `current_stock <= low_stock_limit`                       | Sent once per refill cycle (deduplicated)                |
| `MISSED_DOSE`     | 30 min after scheduled time with no log event            | Auto-marked `SKIPPED` after 2 hours with no action       |
| `REFILL_REMINDER` | 3 days before `estimated_depletion_date`                 | Summary alert to prompt pharmacy visit                   |

### 12.3 Snooze Behaviour

- User can snooze a `DOSE_DUE` alert for **10, 20, or 30 minutes**.
- Maximum **3 snoozes** per dose event. After 3rd snooze, alert converts to `MISSED_DOSE`.
- Snooze events are logged in `VedaLogs` with `status=SNOOZED` for habit analysis.

---

## 13. Success Metrics

> All metrics must be validated in a staging environment under simulated load before production deployment is approved.

| Metric                  | Target          | Definition                                                              |
|-------------------------|-----------------|-------------------------------------------------------------------------|
| LLM Extraction Accuracy | > 94%           | Percentage of NL inputs successfully parsed into structured VedaCore output |
| VedaCore Response Time  | < 2.0 seconds   | End-to-end latency from user message receipt to structured JSON response |
| Inventory Sync Accuracy | 100%            | All `TAKEN` logs decrement `current_stock` atomically with zero drift   |
| API Uptime              | > 99.5%         | Monthly rolling uptime measured at the load-balancer level              |
| P95 Endpoint Latency    | < 300ms         | 95th-percentile response time for all non-AI endpoints under normal load|
| Auth Token Security     | Zero breaches   | No unauthorized access events; JWT rotation enforced every 24 hours     |

---

## 14. Phased Delivery Roadmap

| Phase   | Target  | Scope                                                                              |
|---------|---------|------------------------------------------------------------------------------------|
| Phase 1 | Q2 2026 | Core API: Auth, Vault CRUD, VedaCore extraction, dose logging, basic alerts        |
| Phase 2 | Q3 2026 | Proactive inventory forecasting, APScheduler push notifications, refill reminders  |
| Phase 3 | Q3 2026 | Advanced analytics dashboard, adherence trends, caregiver profile linking           |
| Phase 4 | Q4 2026 | HATEOAS (Level 3 REST), pharmacy integration APIs, exportable health reports        |
| Phase 5 | Q1 2027 | ML-powered habit analysis, personalized reminder optimization, multi-language NL   |

---

## 15. Risk Register

| Risk                                   | Severity | Mitigation                                                                      |
|----------------------------------------|----------|---------------------------------------------------------------------------------|
| LLM hallucination in drug extraction   | HIGH     | Instructor strict mode + JSON schema validation; unit-test 50+ edge cases       |
| Race condition on stock decrement      | HIGH     | Wrap decrement in `SELECT FOR UPDATE`; atomic transaction enforced              |
| JWT token leakage                      | MEDIUM   | Short-lived tokens (15 min), HTTP-only cookies, refresh token rotation          |
| APScheduler job drift under load       | MEDIUM   | Persist job state in DB; distributed lock (Redis) planned for Phase 2           |
| Unstructured NL misinterpretation      | MEDIUM   | Confidence scoring per field; user confirmation step in mobile app              |
| Database migration regression          | LOW      | All Alembic migrations require `downgrade()` method; CI gate enforced           |

---

## 16. Testing Strategy

### 16.1 Unit Tests

- Service layer functions tested in isolation with mocked database sessions.
- VedaCore extraction tested against a curated dataset of 50+ medication description inputs.
- Inventory math (decrement, forecast, alert threshold) covered with boundary-value tests.

### 16.2 Integration Tests

- Full request-response cycle tests against a test PostgreSQL instance using `pytest-asyncio`.
- Auth flow: register → login → access protected endpoint → refresh → logout.
- Vault CRUD: create, read, update, delete with cascade log verification.
- Concurrent decrement test: 10 simultaneous `TAKEN` requests on the same vault entry — verify final stock is consistent.

### 16.3 AI Extraction Tests

- Mock OpenAI API responses to test Instructor schema enforcement.
- Extraction accuracy validated against 50-entry labelled dataset — must exceed **94% field-level accuracy**.
- Retry logic tested on schema validation failure.

### 16.4 CI/CD Gate

- All tests must pass before merge to `main` branch.
- Coverage threshold: **85% line coverage** required.
- Alembic migration dry-run executed against test DB on every PR.

---

## 17. Open Questions & Dependencies

### 17.1 Open Questions

1. **Push Notification Provider** — Firebase Cloud Messaging (FCM) is assumed for Phase 1. Confirm mobile team's preference before APScheduler integration begins.
2. **Drug-Drug Interaction Detection** — Should VedaCore flag potential interactions in Phase 1 or defer to Phase 3? Requires legal/regulatory review.
3. **Caregiver Access Model** — Phase 3 plans caregiver profile linking. Data isolation model and consent flow need product design input before backend modelling begins.
4. **Offline Support** — Does the mobile app require local-first data with sync-on-reconnect? This would require a CRDT or event-sourcing approach not in current scope.

### 17.2 External Dependencies

- **OpenAI API** — Availability SLA and rate limits from OpenAI directly impact VedaCore throughput targets.
- **Mobile Team** — Push notification token registration flow must be agreed before `/profiles PATCH` endpoint is finalized.
- **DevOps / Infrastructure** — Managed PostgreSQL instance, secrets management (e.g., AWS Secrets Manager), and container orchestration must be provisioned before integration testing begins.

---

## 18. Glossary

| Term          | Definition                                                                           |
|---------------|--------------------------------------------------------------------------------------|
| Vault         | The database table and concept representing a user's medication cabinet              |
| VedaCore      | The AI extraction service that converts natural language to structured medication data|
| VedaLog       | An individual dose interaction event record (`TAKEN`, `SKIPPED`, or `SNOOZED`)      |
| Instructor    | Python library that wraps OpenAI SDK calls to enforce JSON schema output             |
| APScheduler   | Advanced Python Scheduler — used for time-based alert dispatch                       |
| Alembic       | SQLAlchemy's database schema migration tool                                           |
| JWT           | JSON Web Token — compact, URL-safe means of representing authentication claims       |
| HATEOAS       | Hypermedia As The Engine Of Application State — REST Level 3 maturity                |
| P95 Latency   | 95th-percentile response time — 95% of requests are faster than this value          |
| CRDT          | Conflict-free Replicated Data Type — for distributed offline-first data sync        |

---

*End of Document — Veda Backend PRD v1.0.3 | Veda Engineering | Internal Use Only*
