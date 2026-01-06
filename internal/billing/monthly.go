package billing

import (
	"database/sql"
	"time"

	// 1. Add the import for your credits package
	"github.com/Mugilan-J/billing-engine/internal/credits"
)

func GenerateMonthlyBilling(db *sql.DB, month time.Time) error {

	rows, err := db.Query(`
		SELECT user_id, SUM(total_cost)
		FROM usage_daily_rollups
		WHERE rollup_date >= date_trunc('month', $1::date)
		  AND rollup_date <  date_trunc('month', $1::date) + interval '1 month'
		GROUP BY user_id
	`, month)
	if err != nil {
		return err
	}
	defer rows.Close()

	for rows.Next() {
		var userID string
		var totalCost float64
		if err := rows.Scan(&userID, &totalCost); err != nil {
			return err
		}

		creditsAmt := 25.0
		creditsUsed := min(totalCost, creditsAmt)
		overage := max(0, totalCost-creditsAmt)

		tier := "free"
		if credits.IsPayg(db, userID) {
			tier = "payg"
		}

		_, err := db.Exec(`
			INSERT INTO billing_monthly_statements
			(user_id, month, total_usage_cost, credits_used, overage_cost, tier)
			VALUES ($1, date_trunc('month', $2::date), $3, $4, $5, $6)
			ON CONFLICT (user_id, month)
			DO UPDATE SET
				total_usage_cost = EXCLUDED.total_usage_cost,
				credits_used     = EXCLUDED.credits_used,
				overage_cost     = EXCLUDED.overage_cost,
				tier             = EXCLUDED.tier,
				updated_at       = NOW()
		`,
			userID,
			month,
			totalCost,
			creditsUsed,
			overage,
			tier,
		)
		if err != nil {
			return err
		}
	}
	return nil
}
