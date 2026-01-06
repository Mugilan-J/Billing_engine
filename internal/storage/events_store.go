package storage

import (
	"database/sql"
	"encoding/json"

	"github.com/Mugilan-J/billing-engine/internal/events"
)

func InsertEvent(db *sql.DB, e events.ChatUsageEvent) error {
	raw, _ := json.Marshal(e)

	// UPDATE THIS QUERY
	_, err := db.Exec(`
        INSERT INTO usage_events(
            event_id, user_id, org_id, model, provider,
            input_tokens, output_tokens, total_tokens,
            duration_ms, status, timestamp, estimated_cost, raw_payload,
            api_key_id  
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13, $14) -- <--- 2. ADD THIS PLACEHOLDER
        ON CONFLICT (event_id) DO NOTHING;
    `,
		e.EventID, e.UserID, e.OrgID, e.Model, e.Provider,
		e.InputTokens, e.OutputTokens, e.TotalTokens,
		e.DurationMs, e.Status, e.Timestamp, e.Estcost, raw,
		e.APIKeyID,
	)

	return err
}
