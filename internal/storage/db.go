package storage

import (
	"database/sql"

	_ "github.com/lib/pq"
)

func ConnectDB() (*sql.DB, error) {
	connStr := "postgres://postgres:mugi%402005@localhost:5432/billing_engine?sslmode=disable"
	return sql.Open("postgres", connStr)
}
