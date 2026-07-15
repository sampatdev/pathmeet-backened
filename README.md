# Pathmeet

A real-time friend-finder backend — two users create a meetup session, share their live location until they meet, and get AI-generated status updates along the way ("Alex is 200m away, arriving in ~3 minutes").

Built as a hands-on learning project covering FastAPI, PostgreSQL, Redis, Kafka, WebSockets, background job processing (arq), an LLM integration, and full Docker/CI-CD deployment.

## Tech Stack

| Layer | Tech | Purpose |
|---|---|---|
| API | FastAPI (Python 3.12, async) | REST endpoints + WebSocket |
| Database | PostgreSQL 17 + SQLAlchemy (async) + Alembic | Users, sessions, location history |
| Cache / Rate limiting | Redis | Last-known-location cache, rate limiting, JWT blocklist |
| Event streaming | Apache Kafka (KRaft mode) | Durable location event log, decoupled from live path |
| Background jobs | arq | Scheduled cron (session expiry) + on-demand jobs (arrival notifications) |
| Real-time | WebSocket + in-memory connection manager | Live location broadcast between two users |
| AI | Anthropic API (Claude) | Natural-language status updates, meeting spot suggestions |
| Auth | JWT (python-jose) + bcrypt (passlib) | Stateless auth with a Redis-backed revocation list |
| Containerization | Docker + Docker Compose | One-command local stack |
| CI/CD | GitHub Actions | Automated build/test on every push, image publish to GHCR on merge to `main` |

## Architecture

```
Client (WebSocket) ──▶ FastAPI ──┬──▶ Redis (last-known location cache)
                                  ├──▶ Kafka (location-updates topic) ──▶ location_consumer worker ──▶ Postgres (location_history)
                                  ├──▶ In-memory ConnectionManager ──▶ other connected client (live push)
                                  └──▶ arq (proximity check) ──▶ arq_worker ──▶ notification job

arq_worker also runs a cron job every 5 min: expire_stale_sessions (Postgres)
```

Three independent services run from the same codebase/image, each with its own container: the API (`api`), the Kafka consumer (`location_consumer`), and the background job worker (`arq_worker`). This means a crash or slowdown in any one of them doesn't affect the others — the live WebSocket path never blocks on Postgres writes, Kafka publishes, or LLM calls.

## Prerequisites

- Docker Desktop or Colima (with Docker CLI)
- An Anthropic API key with available credits ([console.anthropic.com](https://console.anthropic.com)) — only required for the `/ai-status` endpoint; everything else works without it

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/sampatdev/pathmeet-backened.git
   cd pathmeet-backened
   ```

2. **Create your `.env` file** in the project root:
   ```
   SECRET_KEY=<any long random string>
   ANTHROPIC_API_KEY=<your Anthropic API key>
   ```
   These are the only two values Docker Compose needs from `.env` — database/Redis/Kafka connection strings are already set correctly for the containerized network inside `docker-compose.yml`.

3. **Start the full stack**
   ```bash
   docker compose up --build
   ```
   This starts Postgres, Redis, Kafka, the API, the Kafka consumer worker, and the arq worker — six containers, one command. First run will take a few minutes (pulling base images); subsequent runs are much faster.

4. **Run database migrations** (in a new terminal, once the stack is up):
   ```bash
   docker compose exec api alembic upgrade head
   ```

5. **Verify it's running:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return `{"status":"ok"}`.

## Using the API

Interactive API docs (Swagger UI) are available at **http://localhost:8000/docs** once the stack is running — every endpoint below can be tried directly from there.

### Auth
- `POST /auth/signup` — create an account (email, password, display_name)
- `POST /auth/login` — OAuth2 password flow (form fields: `username` = your email, `password`) → returns a JWT
- `GET /auth/me` — current user info (requires Bearer token)
- `POST /auth/logout` — revokes the current token (adds it to a Redis blocklist)

### Meetups
- `POST /meetups/` — create a meetup session, invite a friend by email
- `GET /meetups/{session_id}/location` — poll the other participant's last known location (HTTP alternative to WebSocket)
- `GET /meetups/{session_id}/ai-status` — AI-generated natural-language status update + distance/ETA (rate-limited: 10 requests/minute)

### Live location (WebSocket)
```
ws://localhost:8000/ws/meetup/{session_id}?token=<your JWT>
```
Send: `{"lat": <float>, "lng": <float>}`
Receive: the other participant's location updates, live, as JSON. On connect, you also immediately receive their last cached location if available.

## Rate Limiting

Login and the AI-status endpoint are rate-limited via a Redis-backed sliding window (`app/core/rate_limit.py`) — reusable on any route via `dependencies=[Depends(rate_limiter(max_requests, window_seconds))]`.

## Running Tests / Manual Verification

There's no automated test suite yet — verification during development was done via manual WebSocket test scripts and `curl`/Swagger UI. CI (`.github/workflows/ci.yml`) runs a smoke test on every push: builds the full stack, waits for it to become healthy, runs migrations, and verifies the schema.

## CI/CD

- **Every push / PR to `main`** → builds the full Docker Compose stack, waits for health, runs migrations, verifies tables exist.
- **Every push to `main`** (after tests pass) → builds and publishes the API image to GitHub Container Registry, tagged `latest` and with the commit SHA:
  ```bash
  docker pull ghcr.io/sampatdev/pathmeet-backend:latest
  ```

## Environment Variables Reference

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Yes | JWT signing key |
| `ANTHROPIC_API_KEY` | Only for `/ai-status` | Get from console.anthropic.com |
| `DATABASE_URL` | Set automatically in Compose | `postgresql+asyncpg://...` |
| `REDIS_URL` | Set automatically in Compose | `redis://redis:6379/0` |
| `KAFKA_BOOTSTRAP_SERVERS` | Set automatically in Compose | `kafka:9092` |

## Project Structure

```
app/
├── main.py              # FastAPI app, lifespan, WebSocket endpoint
├── core/                # config, security, redis, kafka producer, arq pool, rate limiting, AI assistant
├── db/                  # SQLAlchemy async session setup
├── models/               # SQLAlchemy ORM models
├── schemas/              # Pydantic request/response schemas
└── routers/              # auth and meetup route handlers
worker/
├── location_consumer.py  # standalone Kafka consumer → writes location_history to Postgres
├── tasks.py               # arq job definitions (cron + on-demand)
└── settings.py            # arq WorkerSettings
alembic/                  # database migrations
docker-compose.yml         # full local stack definition
Dockerfile                 # shared image for api / location_consumer / arq_worker
.github/workflows/ci.yml   # CI/CD pipeline
```