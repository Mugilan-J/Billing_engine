package dashboard

import (
	"database/sql"
	"encoding/json"
	"net/http"
)

func UsageHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {

		userID := r.Header.Get("X-User-ID")
		month := r.URL.Query().Get("month") // YYYY-MM

		var totalCost, creditsUsed, overage float64

		err := db.QueryRow(`
			SELECT total_usage_cost, credits_used, overage_cost
			FROM billing_monthly_statements
			WHERE user_id=$1 AND to_char(month,'YYYY-MM')=$2
		`, userID, month).Scan(&totalCost, &creditsUsed, &overage)

		if err != nil {
			http.Error(w, "usage not found", 404)
			return
		}

		json.NewEncoder(w).Encode(map[string]any{
			"total_cost":   totalCost,
			"credits_used": creditsUsed,
			"overage_cost": overage,
		})
	}
}
