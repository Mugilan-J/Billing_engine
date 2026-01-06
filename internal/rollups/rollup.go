package rollup

import (
	"database/sql"
	"time"
)

func RunDailyRollup(db *sql.DB) error {
	// target: yesterday
	rollupDate := time.Now().Format("2006-01-02")

	// core aggregation SQL
	_, err := db.Exec(`
        INSERT INTO usage_daily_rollups (
    id, 
    rollup_date, 
    user_id, 
    api_key_id, 
    provider,
    model, 
    total_tokens, 
    total_cost,
    created_at,
    updated_at
)
SELECT 
    gen_random_uuid(),              -- Generate new ID for the rollup row
    DATE(e.timestamp) as rollup_date,
    
    k.user_id,                      -- 1. Get the official UUID user_id from api_keys table
    e.api_key_id,
    e.provider,                   -- 2. Keep the API Key UUID
    e.model,
    
    SUM(e.total_tokens),            -- 3. Sum up the metrics
    SUM(e.estimated_cost),
    NOW(),
    NOW()
FROM usage_events e
JOIN api_keys k 
  -- 4. CRITICAL FIX: Cast the UUID to TEXT to match the key_value column
  ON e.api_key_id::text = k.key_value 
WHERE DATE(e.timestamp) = $1        -- The date passed from Go (e.g., '2025-12-29')
GROUP BY 
    DATE(e.timestamp), 
    k.user_id, 
    e.api_key_id, 
    e.provider,
    e.model
ON CONFLICT (rollup_date, api_key_id, model) -- 5. If run twice, update instead of duplicate
DO UPDATE SET
    total_tokens = EXCLUDED.total_tokens,
    total_cost = EXCLUDED.total_cost,
    updated_at = NOW();
    `, rollupDate)

	return err
}
