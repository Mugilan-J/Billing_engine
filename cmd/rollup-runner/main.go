package main

import (
	"log"

	rollup "github.com/Mugilan-J/billing-engine/internal/rollups"
	"github.com/Mugilan-J/billing-engine/internal/storage"
)

func main() {
	log.Println("🔄 Starting daily rollup...")

	db, err := storage.ConnectDB()
	if err != nil {
		log.Fatal("❌ DB connection failed:", err)
	}

	if err := rollup.RunDailyRollup(db); err != nil {
		log.Fatal("❌ Rollup failed:", err)
	}

	log.Println("✅ Rollup completed successfully!")
}
