import os
import sys
from pathlib import Path
from textwrap import dedent

import psycopg2


def _load_env():
    if os.getenv("BILLING_URL"):
        return

    current = Path(__file__).resolve()
    for directory in [current.parent, *current.parents]:
        env_file = directory / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
            break


_load_env()

DB_URL = os.getenv("BILLING_URL")
if not DB_URL:
    raise RuntimeError("BILLING_URL is not set. Create an .env file with the connection string.")

DDL_STATEMENTS = [
    """CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";""",
    dedent(
        """
        CREATE TABLE IF NOT EXISTS tiers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            monthly_credits NUMERIC(12,4) NOT NULL DEFAULT 25,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    ),
    dedent(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    ),
    dedent(
        """
        CREATE TABLE IF NOT EXISTS user_tiers (
            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            tier_id TEXT NOT NULL REFERENCES tiers(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    ),
    dedent(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key_value TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_used_at TIMESTAMPTZ
        );
        """
    ),
    dedent(
        """
        CREATE TABLE IF NOT EXISTS pricing_models (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            cost_input_per_1k_tokens NUMERIC(12,6) NOT NULL,
            cost_output_per_1k_tokens NUMERIC(12,6) NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(provider, model)
        );
        """
    ),
    dedent(
        """
        CREATE TABLE IF NOT EXISTS usage_events (
            event_id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            org_id TEXT,
            model TEXT NOT NULL,
            provider TEXT NOT NULL,
            type TEXT,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            duration_ms INTEGER NOT NULL,
            status INTEGER NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            estimated_cost NUMERIC(18,6) NOT NULL DEFAULT 0,
            raw_payload JSONB,
            api_key_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    ),
    """CREATE INDEX IF NOT EXISTS idx_usage_events_user_time ON usage_events (user_id, timestamp);""",
    """CREATE INDEX IF NOT EXISTS idx_usage_events_api_key ON usage_events (api_key_id);""",
    dedent(
        """
        CREATE TABLE IF NOT EXISTS usage_daily_rollups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rollup_date DATE NOT NULL,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            api_key_id UUID NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            total_tokens BIGINT NOT NULL DEFAULT 0,
            total_cost NUMERIC(18,6) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(rollup_date, api_key_id, model)
        );
        """
    ),
    """CREATE INDEX IF NOT EXISTS idx_usage_daily_rollups_user_date ON usage_daily_rollups (user_id, rollup_date);""",
    dedent(
        """
        CREATE TABLE IF NOT EXISTS billing_monthly_statements (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            month DATE NOT NULL,
            total_usage_cost NUMERIC(18,6) NOT NULL DEFAULT 0,
            credits_used NUMERIC(18,6) NOT NULL DEFAULT 0,
            overage_cost NUMERIC(18,6) NOT NULL DEFAULT 0,
            tier TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, month)
        );
        """
    ),
    dedent(
        """
        CREATE TABLE IF NOT EXISTS billing_usage_breakdown (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            month DATE NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            total_tokens BIGINT NOT NULL DEFAULT 0,
            total_cost NUMERIC(18,6) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, month, provider, model)
        );
        """
    ),
    dedent(
        """
        CREATE TABLE IF NOT EXISTS user_credits (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            month DATE NOT NULL,
            remaing_credits NUMERIC(18,6) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, month)
        );
        """
    ),
    dedent(
        """
        CREATE TABLE IF NOT EXISTS monthly_billing (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            billing_month DATE NOT NULL,
            gross_amount NUMERIC(18,6) NOT NULL DEFAULT 0,
            credits_applied NUMERIC(18,6) NOT NULL DEFAULT 0,
            net_amount NUMERIC(18,6) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, billing_month)
        );
        """
    ),
    dedent(
        """
        CREATE TABLE IF NOT EXISTS daily_rollups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            rollup_date DATE NOT NULL,
            event_count INTEGER NOT NULL DEFAULT 0,
            total_amount NUMERIC(18,6) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, rollup_date)
        );
        """
    ),
]

SEED_DATA = [
    (
        dedent(
            """
            INSERT INTO tiers (id, name, description, monthly_credits)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id)
            DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                monthly_credits = EXCLUDED.monthly_credits,
                updated_at = NOW();
            """
        ),
        ("tier-free", "free", "Free tier with pooled credits", 25.0),
    ),
    (
        dedent(
            """
            INSERT INTO tiers (id, name, description, monthly_credits)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id)
            DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                monthly_credits = EXCLUDED.monthly_credits,
                updated_at = NOW();
            """
        ),
        ("tier-payg", "payg", "Pay as you go", 25.0),
    ),
    (
        dedent(
            """
            INSERT INTO pricing_models (
                provider, model, cost_input_per_1k_tokens,
                cost_output_per_1k_tokens, currency, active
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (provider, model)
            DO UPDATE SET
                cost_input_per_1k_tokens = EXCLUDED.cost_input_per_1k_tokens,
                cost_output_per_1k_tokens = EXCLUDED.cost_output_per_1k_tokens,
                currency = EXCLUDED.currency,
                active = EXCLUDED.active,
                updated_at = NOW();
            """
        ),
        ("ollama", "smollm2", 0.08, 0.08, "USD", True),
    ),
]


def ensure_schema():
    print("Ensuring billing schema...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for ddl in DDL_STATEMENTS:
                cur.execute(ddl)
    finally:
        conn.close()
    print("Schema ready.")


def seed_defaults():
    print("Seeding default reference data...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for sql, params in SEED_DATA:
                cur.execute(sql, params)
    finally:
        conn.close()
    print("Seed data applied.")


if __name__ == "__main__":
    ensure_schema()
    if len(sys.argv) > 1 and sys.argv[1].lower() == "init":
        seed_defaults()
