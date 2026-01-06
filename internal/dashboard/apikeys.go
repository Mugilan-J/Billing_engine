package dashboard

import (
	"database/sql"
	"encoding/json"
	"net/http"
)

func APIKeysHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {

		userID := r.Header.Get("X-User-ID")

		rows, err := db.Query(`
			SELECT id, created_at, status
			FROM api_keys
			WHERE user_id=$1
		`, userID)

		if err != nil {
			http.Error(w, "keys not found", 404)
			return
		}
		defer rows.Close()

		var keys []map[string]any

		for rows.Next() {
			var id, status string
			var created sql.NullTime

			rows.Scan(&id, &created, &status)

			keys = append(keys, map[string]any{
				"key_id":     id,
				"created_at": created.Time,
				"status":     status,
			})
		}

		json.NewEncoder(w).Encode(keys)
	}
}
