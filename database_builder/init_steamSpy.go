package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// Custom type to handle both string and number for score_rank
type FlexibleString string

// cool go magic
func (fs *FlexibleString) UnmarshalJSON(data []byte) error {
	// Try to unmarshal as string first
	var s string
	if err := json.Unmarshal(data, &s); err == nil {
		*fs = FlexibleString(s)
		return nil
	}

	// If that fails, try as number
	var n json.Number
	if err := json.Unmarshal(data, &n); err == nil {
		*fs = FlexibleString(n.String())
		return nil
	}

	// If both fail, check if it's null
	if string(data) == "null" {
		*fs = ""
		return nil
	}

	return fmt.Errorf("cannot unmarshal %s into FlexibleString", string(data))
}

type steamSPY struct {
	AppID          int            `json:"appid"`
	Name           string         `json:"name"`
	Developer      string         `json:"developer"`
	Publisher      string         `json:"publisher"`
	ScoreRank      FlexibleString `json:"score_rank"`
	Positive       int            `json:"positive"`
	Negative       int            `json:"negative"`
	Owners         string         `json:"owners"`
	AverageForever int            `json:"average_forever"`
}

func createSteamSpy() {
	// Set up SQLite database first
	db, err := sql.Open("sqlite3", "./steamspy_all_games.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	_, err = db.Exec(`
        CREATE TABLE IF NOT EXISTS all_games (
            appid INTEGER PRIMARY KEY,
            name TEXT,
            developer TEXT,
            publisher TEXT,
            score_rank TEXT,
            positive INTEGER,
            negative INTEGER,
            owners TEXT,
            average_forever INTEGER
        )
    `)
	if err != nil {
		log.Fatal(err)
	}

	totalSaved := 0
	page := 0
	maxGames := 20000

	fmt.Printf("Fetching games from SteamSpy (target: %d games)...\n", maxGames)

	for totalSaved < maxGames {
		url := fmt.Sprintf("https://steamspy.com/api.php?request=all&page=%d", page)
		fmt.Printf("Fetching page %d...\n", page)

		resp, err := http.Get(url)
		if err != nil {
			log.Printf("Error fetching page %d: %v\n", page, err)
			break
		}

		var gameMap map[string]steamSPY
		if err := json.NewDecoder(resp.Body).Decode(&gameMap); err != nil {
			resp.Body.Close()
			log.Printf("Error decoding page %d: %v\n", page, err)
			break
		}
		resp.Body.Close()

		if len(gameMap) == 0 {
			fmt.Printf("No more games on page %d\n", page)
			break
		}

		fmt.Printf("Retrieved %d games from page %d\n", len(gameMap), page)

		// transaction for this batch
		tx, err := db.Begin()
		if err != nil {
			log.Fatal(err)
		}

		stmt, err := tx.Prepare(`
            INSERT OR REPLACE INTO all_games (
                appid, name, developer, publisher, score_rank, positive, negative, owners, average_forever
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
		if err != nil {
			log.Fatal(err)
		}

		count := 0
		for _, game := range gameMap {
			if totalSaved >= maxGames {
				break
			}

			_, err := stmt.Exec(
				game.AppID, game.Name, game.Developer, game.Publisher,
				string(game.ScoreRank), game.Positive, game.Negative,
				game.Owners, game.AverageForever,
			)
			if err != nil {
				log.Printf("Error inserting game %s: %v\n", game.Name, err)
			} else {
				count++
				totalSaved++
			}
		}

		stmt.Close()

		// Commit this batch
		if err := tx.Commit(); err != nil {
			log.Fatal(err)
		}

		fmt.Printf("Saved %d games from page %d (total: %d)\n", count, page, totalSaved)

		page++
		time.Sleep(1 * time.Second) // Be nice to the API
	}

	fmt.Printf("\nSummary:\n")
	fmt.Printf("Total games saved: %d\n", totalSaved)
}
