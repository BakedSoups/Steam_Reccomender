package main

import (
	"database/sql"
	"fmt"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

func main() {
	// Open the database
	db, err := sql.Open("sqlite3", "./steam_api.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	searchName := "dota 2"

	match, err := searchInCardTable(db, searchName)
	if err != nil {
		log.Fatal(err)
	}

	if match != "" {
		fmt.Printf("Found match: %s\n", match)
	} else {
		fmt.Printf("No match found for: %s\n", searchName)
	}
}

func searchInCardTable(db *sql.DB, searchName string) (string, error) {
	offset := 0
	batchSize := 50

	for {
		query := "SELECT game_name FROM main_game LIMIT ? OFFSET ?"
		rows, err := db.Query(query, batchSize, offset)
		if err != nil {
			return "", err
		}

		hasRows := false

		for rows.Next() {
			hasRows = true
			var name string
			if err := rows.Scan(&name); err != nil {
				rows.Close()
				return "", err
			}
			fmt.Printf("Found %v with %v\n", name, searchName)
			if match, found := Match(name, searchName); found {
				rows.Close()
				return match, nil
			}
		}
		rows.Close()

		if !hasRows {
			return "", fmt.Errorf("no match found for '%s'", searchName)
		}
		// Move to next batch
		offset += batchSize
	}
}
