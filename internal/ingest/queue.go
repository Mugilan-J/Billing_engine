package ingest

import (
	"github.com/Mugilan-J/billing-engine/internal/events"
)

var EventQueue = make(chan events.ChatUsageEvent, 10000)
