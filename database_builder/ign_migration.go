package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

type SteamGameData struct {
	GameID         int            `json:"game_id"`
	Name           string         `json:"name"`
	SteamAppid     int            `json:"steam_appid"`
	TagRatios      map[string]int `json:"tag_ratios"`
	MainGenre      string         `json:"main_genre"`
	UniqueTags     []string       `json:"unique_tags"`
	SubjectiveTags []string       `json:"subjective_tags"`
	Status         string         `json:"status"`
}

func readSteamGamesData() (map[string]SteamGameData, error) {
	data, err := ioutil.ReadFile("tag_builder/steam_games_with_tags.json")
	if err != nil {
		return nil, err
	}

	var gamesData map[string]SteamGameData
	err = json.Unmarshal(data, &gamesData)
	if err != nil {
		return nil, err
	}

	return gamesData, nil
}

func migrateSteamReview(db *sql.DB) {
	gamesData, err := readSteamGamesData()
	if err != nil {
		log.Fatal(err)
	}

	count := 0
	processed := 0

	for _, gameData := range gamesData {
		// only process games with status "processed"
		if gameData.Status != "processed" {
			fmt.Printf("skipping %s - status: %s\n", gameData.Name, gameData.Status)
			continue
		}

		processed++
		appid := gameData.SteamAppid

		// verify appid exists in main_game table
		var exists bool
		err := db.QueryRow("SELECT EXISTS(SELECT 1 FROM main_game WHERE steam_appid = ?)", appid).Scan(&exists)
		if err != nil || !exists {
			fmt.Printf("steam_appid %d not found in main_game table, skipping %s\n", appid, gameData.Name)
			continue
		}

		count++
		fmt.Printf("processing %s (appid: %d)\n", gameData.Name, appid)

		// insert scores
		err = transactSteamReviewScores(db, appid, gameData)
		if err != nil {
			fmt.Printf("error inserting scores for %s: %v\n", gameData.Name, err)
			continue
		}

		// insert ratio tags
		for tag, ratio := range gameData.TagRatios {
			err = transactSteamReviewTag(db, appid, tag, ratio)
			if err != nil {
				fmt.Printf("error inserting tag %s for %s: %v\n", tag, gameData.Name, err)
			} else {
				fmt.Printf("inserted ratio tag: %s, %d, %s, %d\n", gameData.Name, appid, tag, ratio)
			}
		}

		// insert unique tags
		for _, tag := range gameData.UniqueTags {
			err = transactSteamReviewUniqueTag(db, appid, tag)
			if err != nil {
				fmt.Printf("error inserting unique tag %s for %s: %v\n", tag, gameData.Name, err)
			} else {
				fmt.Printf("inserted unique tag: %s, %d, %s\n", gameData.Name, appid, tag)
			}
		}

		// insert subjective tags
		for _, tag := range gameData.SubjectiveTags {
			err = transactSteamReviewSubjectiveTag(db, appid, tag)
			if err != nil {
				fmt.Printf("error inserting subjective tag %s for %s: %v\n", tag, gameData.Name, err)
			} else {
				fmt.Printf("inserted subjective tag: %s, %d, %s\n", gameData.Name, appid, tag)
			}
		}
	}

	fmt.Printf("\nsteam review migration summary:\n")
	fmt.Printf("total games in file: %d\n", len(gamesData))
	fmt.Printf("games with processed status: %d\n", processed)
	fmt.Printf("games successfully migrated: %d\n", count)
}

func transactSteamReviewScores(db *sql.DB, appid int, gameData SteamGameData) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	_, err = tx.Exec(`
	INSERT INTO SteamReview_scores(steam_appid, score, genre)
	VALUES(?,?,?)
	`, appid, 0.0, gameData.MainGenre)

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
		log.Fatal("ERROR creating SteamReview_scores: ", err)
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
		log.Fatal("ERROR creating SteamReview_tags: ", err)
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
		log.Fatal("ERROR creating SteamReview_unique_tags: ", err)
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
		log.Fatal("ERROR creating SteamReview_subjective_tags: ", err)
	}

	fmt.Println("steam review tables created successfully")
}
