package main

import (
	"database/sql"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

// creating the final db
func initFinalDB() {
	db, err := sql.Open("sqlite3", "./steam_enriched.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// update this scheme when adding more api infromation
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS enriched_games (
			appid INTEGER PRIMARY KEY,
			name TEXT,
			description TEXT,
			developer TEXT,
			publisher TEXT,
			score_rank TEXT,
			positive INTEGER,
			negative INTEGER,
			owners TEXT,
			average_forever INTEGER,
			price TEXT
			-- Add new columns for future APIs here
		)
	`)
	if err != nil {
		log.Fatal(err)
	}
}
