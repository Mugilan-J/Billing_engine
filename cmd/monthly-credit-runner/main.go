package main

import (
	"log"
	"time"

	"github.com/Mugilan-J/billing-engine/internal/storage"
)

func main() {

	db, err := storage.ConnectDB()
	if err != nil {
		log.Fatal(err)
	}
	month := time.Now().Format("2006-01-01")

	_, err = db.Exec(`insert into user_credits(user_id,month,remaing_credits) select ut.user_id,$1,t.monthly_credits from user_tiers ut join tiers t on ut.tier_id = t.id on conflict do nothing`, month)
	if err != nil {
		log.Fatal("monthly credits failed", err)
	}
	log.Print("monthly credis credited sucessfully")

}
