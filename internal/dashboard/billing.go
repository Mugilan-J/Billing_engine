package dashboard

import (
	"database/sql"
	"encoding/json"
	"net/http"
)

func BillingHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {

		userID := r.Header.Get("X-User-ID")

		rows, err := db.Query(`
			SELECT month, total_usage_cost, credits_used, overage_cost, status
			FROM billing_monthly_statements
			WHERE user_id=$1
			ORDER BY month DESC
		`, userID)

		if err != nil {
			http.Error(w, "billing not found", 404)
			return
		}
		defer rows.Close()

		var bills []map[string]any

		for rows.Next() {
			var month, status string
			var total, credits, overage float64

			rows.Scan(&month, &total, &credits, &overage, &status)

			bills = append(bills, map[string]any{
				"month":        month,
				"total_cost":   total,
				"credits_used": credits,
				"overage_cost": overage,
				"status":       status,
			})
		}

		json.NewEncoder(w).Encode(bills)
	}
}
