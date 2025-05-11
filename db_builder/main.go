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

	// Get all game verdicts from JSON
	verdicts, err := gameVerdicts()
	if err != nil {
		log.Fatal(err)
	}
	count := 0
	// For each game in verdicts, search in database
	for _, verdict := range verdicts {
		match, err := searchInCardTable(db, verdict.Name)
		if err != nil {
			// log.Printf("Error searching for %s: %v\n", verdict.Name, err)
			continue
		}

		if match != "" {
			count += 1
			fmt.Printf("%s matched with %s\n", verdict.Name, match)
		} else {
			fmt.Printf("%s no match\n", verdict.Name)
		}
	}
	fmt.Printf("matches found %v\n", count)

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
