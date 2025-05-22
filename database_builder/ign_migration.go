package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

type Gametag struct {
	Name          string         `json:"Name"`
	SteamAppid    int            `json:"SteamAppid"`
	Score         float64        `json:"Score"`
	MainGenre     string         `json:"MainGenre"`
	Ratio         map[string]int `json:"Ratio"`
	UniqueTag     []string       `json:"UniqueTag"`
	SubjectiveTag []string       `json:"SubjectiveTag"`
}

func steamReviewVerdicts() ([]Gametag, error) {
	data, err := ioutil.ReadFile("steam_verdicts.json")
	if err != nil {
		return nil, err
	}

	var verdicts []Gametag
	err = json.Unmarshal(data, &verdicts)
	if err != nil {
		return nil, err
	}

	return verdicts, nil
}

func migrateSteamReview(db *sql.DB) {
	verdicts, err := steamReviewVerdicts()
	if err != nil {
		log.Fatal(err)
	}
	count := 0

	for _, verdict := range verdicts {
		appid := verdict.SteamAppid

		// check if this appid exists in main_game table
		var exists bool
		err := db.QueryRow("SELECT EXISTS(SELECT 1 FROM main_game WHERE steam_appid = ?)", appid).Scan(&exists)
		if err != nil || !exists {
			fmt.Printf("steam_appid %d not found in main_game table, skipping %s\n", appid, verdict.Name)
			continue
		}

		count++
		fmt.Printf("processing %s (appid: %d)\n", verdict.Name, appid)

		transactSteamReviewScores(db, appid, verdict)

		for tag, ratio := range verdict.Ratio {
			fmt.Printf("inserted %s, %d, %s, %d\n", verdict.Name, appid, tag, ratio)
			transactSteamReviewTag(db, appid, tag, ratio)
		}

		for _, tag := range verdict.SubjectiveTag {
			transactSteamReviewSubjectiveTag(db, appid, tag)
		}

		for _, tag := range verdict.UniqueTag {
			transactSteamReviewUniqueTag(db, appid, tag)
		}
	}
	fmt.Printf("steam review matches processed: %d\n", count)
}

func transactSteamReviewScores(db *sql.DB, appid int, verdict Gametag) error {
	fmt.Println(verdict)
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(`
	INSERT INTO SteamReview_scores(steam_appid, score, genre)
	VALUES(?,?,?)
	`, appid, verdict.Score, verdict.MainGenre)

	if err != nil {
		tx.Rollback()
		return err
	}

	return tx.Commit()
}

func transactSteamReviewTag(db *sql.DB, appid int, tag string, ratio int) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(`
	INSERT INTO SteamReview_tags(steam_appid, tag, ratio)
	VALUES(?,?,?)
	`, appid, tag, ratio)

	if err != nil {
		tx.Rollback()
		return err
	}

	return tx.Commit()
}

func transactSteamReviewUniqueTag(db *sql.DB, appid int, tag string) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(`
	INSERT INTO SteamReview_unique_tags(steam_appid, unique_tag)
	VALUES(?,?)
	`, appid, tag)

	if err != nil {
		tx.Rollback()
		return err
	}

	return tx.Commit()
}

func transactSteamReviewSubjectiveTag(db *sql.DB, appid int, tag string) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(`
	INSERT INTO SteamReview_subjective_tags(steam_appid, subjective_tag)
	VALUES(?,?)
	`, appid, tag)

	if err != nil {
		tx.Rollback()
		return err
	}

	return tx.Commit()
}

func createSteamReviewTable(db *sql.DB) {
	steamReviewKey := `
	CREATE TABLE IF NOT EXISTS SteamReview_scores ( 
		game_id INTEGER PRIMARY KEY AUTOINCREMENT, 
		steam_appid INTEGER NOT NULL, 
		score REAL NOT NULL,
		genre TEXT
	);
	`
	_, err := db.Exec(steamReviewKey)
	if err != nil {
		log.Fatal("ERROR: ", err)
	}

	tagTable := `
	CREATE TABLE IF NOT EXISTS SteamReview_tags(
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,
		steam_appid INTEGER NOT NULL,
		tag TEXT NOT NULL,
		ratio INTEGER NOT NULL
	);
	`
	_, err = db.Exec(tagTable)
	if err != nil {
		log.Fatal("ERROR: ", err)
	}

	uniqueTagTable := `
	CREATE TABLE IF NOT EXISTS SteamReview_unique_tags(
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,
		steam_appid INTEGER NOT NULL,
		unique_tag TEXT NOT NULL
	);
	`
	_, err = db.Exec(uniqueTagTable)
	if err != nil {
		log.Fatal("ERROR: ", err)
	}

	subjectiveTagsTable := `
	CREATE TABLE IF NOT EXISTS SteamReview_subjective_tags(
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,
		steam_appid INTEGER NOT NULL,
		subjective_tag TEXT NOT NULL
	);
	`
	_, err = db.Exec(subjectiveTagsTable)
	if err != nil {
		log.Fatal("ERROR: ", err)
	}

	fmt.Println("steam review tables created successfully")
}
