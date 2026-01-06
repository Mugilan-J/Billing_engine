package auth

import (
	"net/http"
)

// AuthMiddleware checks for the cookie and passes the UserID to the next handler
func AuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

		// 1. Try to read the session cookie
		cookie, err := r.Cookie("billing_session")

		if err != nil || cookie.Value == "" {
			// No cookie? Return 401 Unauthorized
			http.Error(w, "Unauthorized: Please login", http.StatusUnauthorized)
			return
		}

		// 2. Inject UserID into Header (so your existing dashboard code works!)
		r.Header.Set("X-User-ID", cookie.Value)

		// 3. Continue to the actual dashboard handler
		next.ServeHTTP(w, r)
	})
}
