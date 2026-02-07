package storage

import (
	"database/sql"
	"os"
	"sync"

	"github.com/joho/godotenv"
	_ "github.com/lib/pq"
)

var envOnce sync.Once

func dbURL() string {
	envOnce.Do(func() {
		_ = godotenv.Load()
	})

	if dsn := os.Getenv("BILLING_URL"); dsn != "" {
		return dsn
	}

	return "postgres://postgres:mugi%402005@localhost:5432/billing_engine?sslmode=disable"
}

func ConnectDB() (*sql.DB, error) {
	return sql.Open("postgres", dbURL())
}
