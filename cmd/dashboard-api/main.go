package main

import (
	"log"
	"net/http"

	"github.com/Mugilan-J/billing-engine/internal/auth" // <--- Import this
	"github.com/Mugilan-J/billing-engine/internal/dashboard"
	"github.com/Mugilan-J/billing-engine/internal/storage"
)

func main() {
	db, err := storage.ConnectDB()
	if err != nil {
		log.Fatal(err)
	}

	mux := http.NewServeMux()

	// --- 1. Public Routes (Static UI + Auth) ---
	fs := http.FileServer(http.Dir("./static"))
	mux.Handle("/", fs) // Serves index.html, login.html etc.

	mux.HandleFunc("/api/login", auth.LoginHandler(db))
	mux.HandleFunc("/api/signup", auth.SignupHandler(db))
	mux.HandleFunc("/api/logout", auth.LogoutHandler())

	// --- 2. Protected Routes (Dashboard API) ---
	// We wrap these with AuthMiddleware
	mux.Handle("/dashboard/credits", auth.AuthMiddleware(dashboard.CreditsHandler(db)))
	mux.Handle("/dashboard/usage", auth.AuthMiddleware(dashboard.UsageHandler(db)))
	mux.Handle("/dashboard/usage/breakdown", auth.AuthMiddleware(dashboard.UsageBreakdownHandler(db)))
	mux.Handle("/dashboard/billing", auth.AuthMiddleware(dashboard.BillingHandler(db)))
	mux.Handle("/dashboard/api-keys", auth.AuthMiddleware(dashboard.APIKeysHandler(db)))

	log.Println("🚀 Billing Engine running on http://localhost:8090")
	log.Fatal(http.ListenAndServe(":8090", mux))
}
