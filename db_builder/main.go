package main

import (
	"database/sql"
	"fmt"

	"log"

	_ "github.com/mattn/go-sqlite3"
)

func main() {
	dbo, err := sql.Open("sqlite3", "./example.db")
	if err != nil {
		log.Fatal("Sql Error: ", err)
	}
	defer dbo.Close()
	dbo.Exec("PRAGMA foreign_keys = ON;")

	createIGNTable(dbo)

	db, err := sql.Open("sqlite3", "./steam_api.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Game verdicts from JSON
	verdicts, err := gameVerdicts()
	if err != nil {
		log.Fatal(err)
	}
	count := 0
	// Each game in verdicts, search in database
	for _, verdict := range verdicts {
		match, appid, err := searchInCardTable(db, verdict.Name)
		if err != nil {
			continue
		}

		if match != "" {
			count += 1
			fmt.Printf("%s matched with %s this is the appid%d\n", verdict.Name, match, appid)
			// GREAT we found a match we know the appid to insert now
			add_match(dbo, appid, verdict)
		}

	}
	fmt.Printf("matches found %v\n", count)

}

func add_match(db *sql.DB, appid int, verdict Gametag) error {
	fmt.Println(verdict)
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(` 
	INSERT INTO ign_tags(steam_appid)
	VALUES(?,?)`, appid)

	if err != nil {
		tx.Rollback() // Rollback
		return err
	}

	return tx.Commit()
}

func createIGNTable(db *sql.DB) {
	// for now all this will do is create a temp table
	ignKey := `
	CREATE TABLE IF NOT EXISTS ign_scores ( 
		game_id INTEGER PRIMARY KEY AUTOINCREMENT, 
		steam_appid INTEGER NOT NULL UNIQUE, 
		score REAL NOT NULL
	);
	`
	_, err := db.Exec(ignKey)

	if err != nil {
		log.Fatal("ERROR: ", err)
	}
	tagTable := `
	CREATE TABLE IF NOT EXISTS ign_tags(
		game_tags INTERGER 
	);
	`
	_, err = db.Exec(tagTable)

	if err != nil {
		log.Fatal("ERROR: ", err)
	}

}

func searchInCardTable(db *sql.DB, searchName string) (string, int, error) {
	offset := 0
	batchSize := 50

	for {
		query := "SELECT game_name, steam_appid FROM main_game LIMIT ? OFFSET ?"
		rows, err := db.Query(query, batchSize, offset)
		if err != nil {
			return "", 0, err
		}

		hasRows := false

		for rows.Next() {
			hasRows = true
			var name string
			var appid int

			if err := rows.Scan(&name, &appid); err != nil {
				rows.Close()
				return "", 0, err
			}
			if match, found := Match(name, searchName); found {
				rows.Close()
				// returns match that is IN the database
				return match, appid, nil
			}
		}
		rows.Close()

		if !hasRows {
			return "", 0, fmt.Errorf("no match found for '%s'", searchName)
		}
		// Move to next batch
		offset += batchSize
	}
}
