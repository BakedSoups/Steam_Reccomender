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
			// fmt.Printf("%s matched with %s this is the appid%d\n", verdict.Name, match, appid)
			// GREAT we found a match we know the appid to insert now
			transactIgnScores(dbo, appid, verdict)
			for tag, ratio := range verdict.Ratio {
				fmt.Printf("Inserted %v , %v, %v, %v\n", match, appid, tag, ratio)
				transactIgbtag(dbo, appid, tag, ratio)
			}
			for _, tag := range verdict.SubjectiveTag {
				transactSubjectivetag(dbo, appid, tag)
			}

			for _, tag := range verdict.UniqueTag {
				transactUniquetag(dbo, appid, tag)
			}
		}

	}
	fmt.Printf("matches found %v\n", count)

}

func transactIgnScores(db *sql.DB, appid int, verdict Gametag) error {
	fmt.Println(verdict)
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(` 
	INSERT INTO ign_scores(steam_appid, score, genre)
	VALUES(?,?)
	`, appid, verdict.Score, verdict.MainGenre)

	if err != nil {
		tx.Rollback() // Rollback
		return err
	}

	return tx.Commit()
}

func transactIgbtag(db *sql.DB, appid int, tag string, ratio int) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(` 
	INSERT INTO ign_tags(steam_appid, tag, ratio)
	VALUES(?,?,?)
	`, appid, tag, ratio)

	if err != nil {
		tx.Rollback() // Rollback
		return err
	}

	return tx.Commit()
}

func transactUniquetag(db *sql.DB, appid int, tag string) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(` 
	INSERT INTO ign_unique_tags(steam_appid, unique_tag)
	VALUES(?,?)
	`, appid, tag)

	if err != nil {
		tx.Rollback() // Rollback
		return err
	}

	return tx.Commit()
}

func transactSubjectivetag(db *sql.DB, appid int, tag string) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(` 
	INSERT INTO ign_subjective_tags(steam_appid, subjective_tag)
	VALUES(?,?)
	`, appid, tag)

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
		score REAL NOT NULL,
		genre TEXT
	);
	`
	_, err := db.Exec(ignKey)

	if err != nil {
		log.Fatal("ERROR: ", err)
	}
	tag_tag_table := `
	CREATE TABLE IF NOT EXISTS ign_tags(
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,
		steam_appid INTERGER NOT NULL UNIQUE,
		tag TEXT NOT NULL,
		ratio INTERGER NOT NULL
	);
	`
	_, err = db.Exec(tag_tag_table)

	if err != nil {
		log.Fatal("ERROR: ", err)
	}
	unique_tag_table := `
	CREATE TABLE IF NOT EXISTS ign_unique_tags(
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,
		steam_appid INTERGER NOT NULL UNIQUE,
		unique_tag TEXT NOT NULL
	);
	`
	_, err = db.Exec(unique_tag_table)

	if err != nil {
		log.Fatal("ERROR: ", err)
	}
	subjective_tags_table := `
	CREATE TABLE IF NOT EXISTS ign_subjective_tags(
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,
		steam_appid INTERGER NOT NULL UNIQUE,
		subjective_tag TEXT NOT NULL
	);
	`
	_, err = db.Exec(subjective_tags_table)

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
