package dashboard

import (
	"database/sql"
	"encoding/json"
	"net/http"
)

func UsageBreakdownHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {

		userID := r.Header.Get("X-User-ID")
		month := r.URL.Query().Get("month")

		rows, err := db.Query(`
			SELECT provider, model, total_tokens, total_cost
			FROM billing_usage_breakdown
			WHERE user_id=$1 AND to_char(month,'YYYY-MM')=$2
		`, userID, month)

		if err != nil {
			http.Error(w, "breakdown not found", 404)
			return
		}
		defer rows.Close()

		var result []map[string]any

		for rows.Next() {
			var provider, model string
			var tokens int64
			var cost float64

			rows.Scan(&provider, &model, &tokens, &cost)

			result = append(result, map[string]any{
				"provider": provider,
				"model":    model,
				"tokens":   tokens,
				"cost":     cost,
			})
		}

		json.NewEncoder(w).Encode(result)
	}
}
