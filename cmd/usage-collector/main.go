package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/Mugilan-J/billing-engine/internal/credits"
	"github.com/Mugilan-J/billing-engine/internal/events"
	"github.com/Mugilan-J/billing-engine/internal/pricing"
	"github.com/Mugilan-J/billing-engine/internal/storage"
	"github.com/google/uuid"
)

var db *sql.DB

func collector(w http.ResponseWriter, r *http.Request) {

	var e events.ChatUsageEvent
	if err := json.NewDecoder(r.Body).Decode(&e); err != nil {
		http.Error(w, "invalid request", http.StatusBadRequest)
		return
	}
	if e.UserID == "" || e.OrgID == "" || e.APIKeyID == "" {
		http.Error(w, "Missing values", http.StatusBadRequest)
		return
	}

	if e.TotalTokens != e.InputTokens+e.OutputTokens {
		http.Error(w, "Token missmatch", http.StatusBadRequest)
		return
	}

	e.EventID = uuid.NewString()
	india, _ := time.LoadLocation("Asia/Kolkata")
	if e.Timestamp.IsZero() {
		e.Timestamp = time.Now().In(india)
	} else {
		e.Timestamp = e.Timestamp.In(india)
	}

	user_id, err := storage.GetUserId(db, e.APIKeyID)
	if err != nil {
		log.Printf("❌ [Auth Error] API Key lookup failed: %v", err)
		http.Error(w, "API key invalid", 402)
		return
	}
	e.UserID = user_id

	estcost, err := pricing.GetCostForModel(db, e.Provider, e.Model, e.InputTokens, e.OutputTokens)
	if err != nil {
		log.Printf("pricing failed : %v", err)
		estcost = 0
	}
	e.Estcost = estcost

	// _, err = credits.EnsureMonthlyCredits(db, e.UserID)
	// if err != nil {
	// 	log.Printf("❌ [Credit Init Error] Failed to create credits: %v", err)
	// 	http.Error(w, "credits init failed", 500)
	// 	return
	// }
	ispayg := credits.IsPayg(db, e.UserID)

	after, err := credits.DeductCredits(db, e.UserID, e.Estcost, ispayg)

	if err != nil {
		log.Printf("❌ [Billing Error] Deduction failed: %v", err)
		http.Error(w, "Credits exhausted upgrade to pay as you go to continue", 402)
		return
	}

	if err := storage.InsertEvent(db, e); err != nil {
		log.Printf("❌ [DB Error] Insert failed: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	// switch{
	// case ingest.EventQueue <- e:
	// 	w.WriteHeader(http.StatusAccepted)
	// 	w.Write([]byte("event recived"))

	// }

	log.Printf("\nevent recived : %+v", e)
	log.Printf("\nEstimated cost : %f", estcost)
	log.Printf("\nuser's %s remaining credits : %f", e.UserID, after)

	w.Write([]byte("eventer sended sucessfully"))

}

func main() {
	fmt.Print("Server running on port 8080...")

	var err error
	db, err = storage.ConnectDB()
	if err != nil {
		log.Fatal("Database connection failed", err)
	}

	http.HandleFunc("/events", collector)
	log.Fatal(http.ListenAndServe(":8080", nil))

}
