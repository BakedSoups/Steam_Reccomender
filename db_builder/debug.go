package main

import (
	"database/sql"
	"fmt"
	"log"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

// summary of all the fused data
func printSummary() {
	db, err := sql.Open("sqlite3", "./steam_enriched.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	var count int
	err = db.QueryRow("SELECT COUNT(*) FROM enriched_games").Scan(&count)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("\nETL Pipeline completed successfully!\n")
	fmt.Printf("Total games enriched: %d\n", count)

	// Show sample of enriched data
	rows, err := db.Query(`
		SELECT appid, name, price 
		FROM enriched_games 
		LIMIT 5
	`)
	if err != nil {
		log.Fatal(err)
	}
	defer rows.Close()

	fmt.Println("\nSample of enriched data:")
	fmt.Printf("%-10s %-30s %s\n", "AppID", "Name", "Price")
	fmt.Println(strings.Repeat("-", 50))

	for rows.Next() {
		var appID int
		var name, price string
		if err := rows.Scan(&appID, &name, &price); err != nil {
			log.Fatal(err)
		}
		fmt.Printf("%-10d %-30s %s\n", appID, name, price)
	}
}
