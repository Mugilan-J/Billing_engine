package storage

import (
	"database/sql"
)

func GetUserId(db *sql.DB, api_key string) (string, error) {

	var user_id string
	err := db.QueryRow(`select user_id from api_keys where key_value=$1`, api_key).Scan(&user_id)

	return user_id, err

}
