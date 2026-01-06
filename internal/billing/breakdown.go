package billing

import (
	"database/sql"
	"time"
)

func GenerateUsageBreakdown(db *sql.DB, month time.Time) error {

	_, err := db.Exec(`
		INSERT INTO billing_usage_breakdown
		(user_id, month, provider, model, total_tokens, total_cost)
		SELECT
			user_id,
			date_trunc('month', $1::date),
			provider,
			model,
			SUM(total_tokens),
			SUM(total_cost)
		FROM usage_daily_rollups
		WHERE rollup_date >= date_trunc('month', $1::date)
		  AND rollup_date <  date_trunc('month', $1::date) + interval '1 month'
		GROUP BY user_id, provider, model
		ON CONFLICT (user_id, month, provider, model)
		DO UPDATE SET
			total_tokens = EXCLUDED.total_tokens,
			total_cost   = EXCLUDED.total_cost
	`, month)

	return err
}
