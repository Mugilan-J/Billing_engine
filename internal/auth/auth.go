package auth

import (
	"database/sql"
	"errors"
	"fmt"
	"regexp"
	"time"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

// --- 1. UTILS (Password Strength) ---
func validatePassword(password string) error {
	if len(password) < 8 {
		return errors.New("password must be at least 8 characters")
	}
	hasNumber := regexp.MustCompile(`[0-9]`).MatchString(password)
	hasUpper := regexp.MustCompile(`[A-Z]`).MatchString(password)
	if !hasNumber || !hasUpper {
		return errors.New("password must contain at least one number and one uppercase letter")
	}
	return nil
}

// --- 2. LOGIN LOGIC ---
func ValidateLogin(db *sql.DB, email, password string) (string, error) {
	var userID, hash string

	// Query the user
	err := db.QueryRow("SELECT id, password_hash FROM users WHERE email=$1", email).Scan(&userID, &hash)
	if err == sql.ErrNoRows {
		return "", errors.New("user not found")
	} else if err != nil {
		return "", err
	}

	// Compare Hash (Bcrypt)
	err = bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
	if err != nil {
		return "", errors.New("invalid password")
	}

	return userID, nil
}

// --- 3. SIGNUP LOGIC (Transaction) ---
func CreateUser(db *sql.DB, email, password, tierName string) (string, error) {
	// 1. Validate Password
	if err := validatePassword(password); err != nil {
		return "", err
	}

	// 2. Check if user exists
	var exists string
	err := db.QueryRow("SELECT id FROM users WHERE email=$1", email).Scan(&exists)
	if err != sql.ErrNoRows {
		return "", errors.New("user already exists")
	}

	// 3. Start Transaction (All or Nothing)
	tx, err := db.Begin()
	if err != nil {
		return "", err
	}
	defer tx.Rollback() // Rollback if we fail anywhere

	// 4. Get Tier ID
	var tierID string
	err = tx.QueryRow("SELECT id FROM tiers WHERE name=$1", tierName).Scan(&tierID)
	if err != nil {
		return "", fmt.Errorf("tier '%s' not found", tierName)
	}

	// 5. Create User
	userID := uuid.NewString()
	hashBytes, _ := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	hashedPass := string(hashBytes)

	_, err = tx.Exec(`INSERT INTO users (id, email, password_hash, created_at) VALUES ($1, $2, $3, $4)`,
		userID, email, hashedPass, time.Now())
	if err != nil {
		return "", err
	}

	// 6. Link Tier
	_, err = tx.Exec(`INSERT INTO user_tiers (user_id, tier_id, created_at) VALUES ($1, $2, $3)`,
		userID, tierID, time.Now())
	if err != nil {
		return "", err
	}

	// 7. Create API Key
	keyVal := uuid.NewString()
	_, err = tx.Exec(`INSERT INTO api_keys (id, user_id, key_value, status, created_at) VALUES ($1, $2, $3, 'active', $4)`,
		uuid.NewString(), userID, keyVal, time.Now())
	if err != nil {
		return "", err
	}

	// 8. Commit
	if err := tx.Commit(); err != nil {
		return "", err
	}

	return userID, nil
}
