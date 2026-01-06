package dashboard

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"time"
)

func CreditsHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {

		userID := r.Header.Get("X-User-ID") // mocked auth

		var remaining float64
		var tier string

		err := db.QueryRow(`
	SELECT 
		c.remaing_credits,
		COALESCE(t.name, 'free')
	FROM user_credits c
	LEFT JOIN user_tiers ut ON ut.user_id = c.user_id
	LEFT JOIN tiers t ON t.id = ut.tier_id
	WHERE c.user_id=$1
	ORDER BY c.month DESC
	LIMIT 1
`, userID).Scan(&remaining, &tier)

		if err != nil {
			http.Error(w, "credits not found", 404)
			return
		}

		resetDate := time.Now().AddDate(0, 1, -time.Now().Day()+1)

		json.NewEncoder(w).Encode(map[string]any{
			"tier":              tier,
			"monthly_credits":   25.0,
			"remaining_credits": remaining,
			"reset_date":        resetDate.Format("2006-01-02"),
		})
	}
}
