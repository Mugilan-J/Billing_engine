package credits

import (
	"database/sql"
	"fmt"
	"time"
)

func EnsureMonthlyCredits(db *sql.DB, userID string) (float64, error) {
	month := time.Now().Format("2006-01-01")

	_, err := db.Exec(`
		INSERT INTO user_credits (user_id, month, remaing_credits)
		SELECT 
			$1, 
			$2, 
			t.monthly_credits
		FROM user_tiers ut
		JOIN tiers t ON ut.tier_id = t.id
		WHERE ut.user_id = $1
		ON CONFLICT (user_id, month) DO NOTHING
	`, userID, month)
	if err != nil {
		return 0, err
	}

	var remaining float64
	err = db.QueryRow(`
		SELECT remaing_credits
		FROM user_credits
		WHERE user_id=$1 AND month=$2
	`, userID, month).Scan(&remaining)

	return remaining, err
}

func IsPayg(db *sql.DB, userID string) bool {
	var tier string
	err := db.QueryRow(`
		SELECT t.name
		FROM user_tiers ut
		JOIN tiers t ON ut.tier_id=t.id
		WHERE ut.user_id = $1
	`, userID).Scan(&tier)

	if err != nil {
		return false
	}
	return tier == "payg"
}

func DeductCredits(db *sql.DB, userID string, cost float64, allowOverage bool) (float64, error) {

	month := time.Now().Format("2006-01-01")

	var remaining float64
	err := db.QueryRow(`
		SELECT remaing_credits
		FROM user_credits
		WHERE user_id=$1 AND month=$2
	`, userID, month).Scan(&remaining)

	if err != nil {
		return 0, err
	}

	newRemaining := remaining - cost

	if !allowOverage && newRemaining < 0 {
		return remaining, fmt.Errorf("credits exhausted")
	}

	if allowOverage && newRemaining < 0 {
		newRemaining = 0
	}

	_, err = db.Exec(`
		UPDATE user_credits
		SET remaing_credits=$1
		WHERE user_id=$2 AND month=$3
	`, newRemaining, userID, month)

	return newRemaining, err
}
