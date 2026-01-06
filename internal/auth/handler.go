package auth

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type Credentials struct {
	Email    string `json:"email"`
	Password string `json:"password"`
	Tier     string `json:"tier"` // Only for signup
}

func LoginHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var creds Credentials
		if err := json.NewDecoder(r.Body).Decode(&creds); err != nil {
			http.Error(w, "Invalid request", 400)
			return
		}

		userID, err := ValidateLogin(db, creds.Email, creds.Password)
		if err != nil {
			// 🔴 LOG THE ERROR TO CONSOLE
			fmt.Printf("❌ Login Failed for %s: %v\n", creds.Email, err)

			http.Error(w, err.Error(), 401)
			return
		}

		// Set Cookie
		setAuthCookie(w, userID)
		w.Write([]byte(`{"status":"success", "user_id":"` + userID + `"}`))
	}
}

func SignupHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var creds Credentials
		if err := json.NewDecoder(r.Body).Decode(&creds); err != nil {
			http.Error(w, "Invalid request", 400)
			return
		}

		// Default tier if empty
		if creds.Tier == "" {
			creds.Tier = "free"
		}

		userID, err := CreateUser(db, creds.Email, creds.Password, creds.Tier)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}

		// Set Cookie
		setAuthCookie(w, userID)
		w.Write([]byte(`{"status":"success", "user_id":"` + userID + `"}`))
	}
}

func LogoutHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Clear Cookie
		http.SetCookie(w, &http.Cookie{
			Name:   "billing_session",
			Value:  "",
			Path:   "/",
			MaxAge: -1,
		})
		w.Write([]byte("Logged out"))
	}
}

// --- HELPER: Set Cookie ---
// In internal/auth/handlers.go

func setAuthCookie(w http.ResponseWriter, userID string) {
	http.SetCookie(w, &http.Cookie{
		Name:  "billing_session",
		Value: userID,
		Path:  "/",

		// 🔴 CRITICAL FIXES FOR LOCALHOST:
		HttpOnly: true,                 // Keep true (Security)
		SameSite: http.SameSiteLaxMode, // MUST be Lax for localhost to work
		Secure:   false,                // MUST be false for HTTP (localhost)

		Expires: time.Now().Add(24 * time.Hour),
	})
}
