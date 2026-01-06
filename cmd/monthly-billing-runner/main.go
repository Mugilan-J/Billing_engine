package main

import (
	"log"
	"time"

	"github.com/Mugilan-J/billing-engine/internal/billing"
	"github.com/Mugilan-J/billing-engine/internal/storage"
)

func main() {
	log.Println("🔥 Starting monthly billing runner")

	// 1️⃣ Connect DB
	db, err := storage.ConnectDB()
	if err != nil {
		log.Fatal("DB connection failed:", err)
	}
	defer db.Close()

	// 2️⃣ Target month (current month)
	// Billing is always month-based, not day-based
	month := time.Now().UTC()

	log.Printf("📆 Generating billing for month: %s",
		month.Format("2006-01"))

	// 3️⃣ Generate monthly billing statements
	if err := billing.GenerateMonthlyBilling(db, month); err != nil {
		log.Fatal("❌ Monthly billing generation failed:", err)
	}

	// 4️⃣ Generate model-wise usage breakdown
	if err := billing.GenerateUsageBreakdown(db, month); err != nil {
		log.Fatal("❌ Usage breakdown generation failed:", err)
	}

	log.Println("✅ Monthly billing completed successfully")
}
