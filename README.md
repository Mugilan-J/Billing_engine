# Billing Engine

Billing Engine is a production-minded reference stack for tracking LLM/API usage, deducting credits, and generating monthly invoices. It consists of Go microservices for ingestion and billing plus Python tooling for developer onboarding and optional chat experiences.

## Features
- **Usage ingestion:** `/events` collector validates API keys and records token counts.
- **Daily + monthly rollups:** background runners aggregate usage and produce billing statements.
- **Developer tooling:** Python CLI to sign up, manage tiers, and mint API keys.
- **LLM chat client:** optional Ollama-powered assistant that reports usage back to the billing API.
- **Custom bot support:** Ship your own chatbot (see `chat/bot.py`) or integrate any client that authenticates with generated API keys.

## Repository Layout
- `cmd/usage-collector`: HTTP server (port 8080) that receives usage events and deducts credits.
- `cmd/rollup-runner`: aggregates raw events into `usage_daily_rollups` (run daily).
- `cmd/monthly-credit-runner`: allocates monthly credits to every active user (run monthly/cron).
- `cmd/monthly-billing-runner`: builds statements + per-model breakdown from daily rollups.
- `internal/*`: shared Go packages (auth, billing, credits, pricing, rollups, storage).
- `chat/`: Python CLI (`noauth.py`), optional bot sample (`bot.py`), and Ollama chat client (`brick.py`).
- `testing/setup_db.py`: database bootstrapper (schema + optional seed data).
- `testing/setup_billing.go`: installs Go module dependencies defined in `go.mod`.

## Prerequisites
- **Go** 1.24+
- **Python** 3.11+
- **PostgreSQL** 14+ with credentials able to create databases
- **Ollama** (optional, for `chat/brick.py`): https://ollama.com/download
- **Pip/virtualenv** and **Git**

## 1. Configure Environment Variables
All services read `BILLING_URL` from an `.env` file at the repo root.

```bash
cp .env.example .env
# edit BILLING_URL to match your Postgres instance
```

Example value:

```
BILLING_URL=postgres://postgres:mypassword@localhost:5432/billing_engine
```

Guidelines:
- Keep `.env` out of version control (already listed in `.gitignore`).
- Percent-encode special characters (e.g., `@` → `%40`).
- Use separate `.env` files per environment (local, staging, prod) and inject them via your process manager/CI.

## 2. Initialize the Database
Create the database once (adjust the name if desired):

```bash
createdb billing_engine
```

Run the schema migrator:

```bash
python testing/setup_db.py
# add "init" to also seed base tiers + sample pricing
python testing/setup_db.py init
```

The script uses `BILLING_URL`; ensure the .env file (or your shell) is configured before running it.

## 3. Install Dependencies

### Go modules
Install/verify modules by running either command from the repo root:

```bash
go mod tidy
# or
go run testing/setup_billing.go
```

### Python (chat module)

```bash
cd chat
python -m venv .venv
source .venv/Scripts/activate   # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 4. Running the Go Services

1. **Usage Collector (port 8080)**
	```bash
	go run ./cmd/usage-collector
	```

2. **Daily Rollup (cron/daily job)**
	```bash
	go run ./cmd/rollup-runner
	```

3. **Monthly Credit Allocation**
	```bash
	go run ./cmd/monthly-credit-runner
	```

4. **Monthly Billing Statements**
	```bash
	go run ./cmd/monthly-billing-runner
	```

Place the runner commands in your task scheduler (cron, Windows Task Scheduler, etc.) according to the cadence you need.

## 5. Creating Accounts and API Keys
Use the Python CLI to manage developers and tiers:

```bash
python chat/noauth.py
```

Workflow inside the CLI:
1. Choose **Signup** and enter your email/password (Tier defaults to `free`; choose option 2 for `payg`).
2. On success, the tool prints an API key and opens the dashboard menu.
3. From the dashboard you can list keys, mint new ones, revoke, change password, or delete the account.

The same credentials work in any client that talks to the billing API.

## 6. Ollama + Chat Client (Optional)

1. Install Ollama from https://ollama.com/download and start the service (`ollama serve` runs automatically on most systems).
2. Pull the model used by `BrickClient`:
	```bash
	ollama pull smollm2
	```
3. Configure `BILLING_URL` (same as the rest of the repo) and start the chat client:
	```bash
	python chat/brick.py
	```
4. Provide an API key (from the CLI) when prompted; the client validates it via Postgres, talks to Ollama locally, and reports usage events back to the billing API (`/events`).
5. Customize the model by editing `model="smollm2"` inside [chat/brick.py](chat/brick.py) to any Ollama model you have installed.

> **Optional bot implementation:** [chat/bot.py](chat/bot.py) showcases how to wire the billing client into a bespoke assistant. You can delete it and build your own bot—the only requirement is to authenticate with an API key from `noauth.py` and POST usage metrics to `/events`.

## 7. Sending Usage Events Manually
Once `usage-collector` is running you can test ingestion:

```bash
curl -X POST http://localhost:8080/events \
  -H "Content-Type: application/json" \
  -d '{
		  "org_id": "default_org",
		  "api_key_id": "<YOUR_API_KEY>",
		  "model": "smollm2",
		  "provider": "ollama",
		  "type": "chat",
		  "input_tokens": 120,
		  "output_tokens": 55,
		  "total_tokens": 175,
		  "duration_ms": 1400,
		  "status": 200
		}'
```

`usage-collector` looks up the `user_id` from `api_keys`, deducts credits via `internal/credits`, transacts the event, and logs remaining credits.

## 8. Scheduling Rollups & Billing
- Run `rollup-runner` daily (after usage data is ingested) to keep `usage_daily_rollups` current.
- Run `monthly-credit-runner` on the first of each month to provision tier credits.
- Run `monthly-billing-runner` at month end (or on demand) to refresh statements and per-model breakdowns.

## 9. Troubleshooting
- **Missing BILLING_URL:** confirm `.env` exists or export the variable before running any script.
- **No tables after migration:** double-check that the connection string targets the expected database (pgAdmin screenshot + `psql -c "SELECT current_database();"`).
- **Ollama connection issues:** ensure `ollama serve` is active and the `smollm2` model is pulled.
- **Collector rejects events:** verify `api_key_id` matches a key generated via `noauth.py` and that `total_tokens = input_tokens + output_tokens`.

Happy billing! Contributions via pull requests or issues are welcome.
