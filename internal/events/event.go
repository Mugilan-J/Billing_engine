package events

import "time"

type ChatUsageEvent struct {
	// --- IDENTITY (Who?) ---
	EventID  string `json:"event_id"`   // UUID, dedupe key
	UserID   string `json:"user_id"`    // The end user
	OrgID    string `json:"org_id"`     // Tenant for B2B / teams
	APIKeyID string `json:"api_key_id"` // Used API key

	// --- DIMENSIONS (What?) ---
	Model    string  `json:"model"`    // "llama3", "gpt-4"
	Provider string  `json:"provider"` // "ollama", "openai"
	Type     string  `json:"type"`     // "chat", "embedding"
	Estcost  float64 `json:"estcost"`

	// --- METRICS (How much?) ---
	InputTokens  int `json:"input_tokens"`
	OutputTokens int `json:"output_tokens"`
	TotalTokens  int `json:"total_tokens"`

	// --- PERFORMANCE (Quality) ---
	DurationMs int `json:"duration_ms"`
	Status     int `json:"status"`

	// --- METADATA (When?) ---
	Timestamp time.Time `json:"timestamp"`
}
