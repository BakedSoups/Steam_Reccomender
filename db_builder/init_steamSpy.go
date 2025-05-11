package main

// this pulls the top 50 games from steaspy and uploads it into the sqilte3 file "steamspy_top50.db"

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sort"

	_ "github.com/mattn/go-sqlite3"
)

type steamSPY struct {
	AppID          int    `json:"appid"`
	Name           string `json:"name"`
	Developer      string `json:"developer"`
	Publisher      string `json:"publisher"`
	ScoreRank      string `json:"score_rank"`
	Positive       int    `json:"positive"`
	Negative       int    `json:"negative"`
	Owners         string `json:"owners"`
	AverageForever int    `json:"average_forever"`
}

func createSteamSpy() {
	resp, err := http.Get("https://steamspy.com/api.php?request=top100in2weeks")
	if err != nil {
		log.Fatal(err)
	}
	defer resp.Body.Close()

	var gameMap map[string]steamSPY
	if err := json.NewDecoder(resp.Body).Decode(&gameMap); err != nil {
		log.Fatal(err)
	}

	//convert map to slice and sort (SteamSpy does not guarantee order)
	games := make([]steamSPY, 0, len(gameMap))
	for _, game := range gameMap {
		games = append(games, game)
	}

	// sort descending
	sort.Slice(games, func(i, j int) bool {
		return games[i].AverageForever > games[j].AverageForever
	})

	top50 := games
	if len(games) > 50 {
		top50 = games[:50]
	}

	//set up SQLite database
	db, err := sql.Open("sqlite3", "./init_steamspy.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	_, err = db.Exec(`
        CREATE TABLE IF NOT EXISTS top_games (
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

	stmt, err := db.Prepare(`
        INSERT OR REPLACE INTO top_games (
            appid, name, developer, publisher, score_rank, positive, negative, owners, average_forever
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `)
	if err != nil {
		log.Fatal(err)
	}
	defer stmt.Close()

	for _, game := range top50 {
		_, err := stmt.Exec(
			game.AppID, game.Name, game.Developer, game.Publisher,
			game.ScoreRank, game.Positive, game.Negative,
			game.Owners, game.AverageForever,
		)
		if err != nil {
			log.Printf("Error inserting game %s: %v\n", game.Name, err)
		}
	}

	fmt.Println("Top 50 games have been saved to SQLite")

}
