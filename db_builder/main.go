package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/mattn/go-sqlite3"
)

// FinalGame contains all fields from all data sources
type FinalGame struct {
	// Base fields from SteamSpy
	AppID       int    `json:"appid"`
	Name        string `json:"name"`
	Developer   string `json:"developer"`
	Publisher   string `json:"publisher"`
	ScoreRank   string `json:"score_rank"`
	Positive    int    `json:"positive"`
	Negative    int    `json:"negative"`
	Owners      string `json:"owners"`
	AvgPlaytime int    `json:"average_forever"`

	// Fields from Steam API
	Description string `json:"description"`
	Price       string `json:"price"`

	// Fields from future APIs can be added here
	// GenreList    string `json:"genre_list"`
	// ReleaseDate  string `json:"release_date"`
	// Etc...
}

func main() {

	fmt.Println("running..")

	// create update the SteamSpy database
	// fmt.Println("Initializing SteamSpy database...")
	// createSteamSpy()

	// //final database that will contain enriched data
	// fmt.Println("Creating final database...")
	// initFinalDB()

	// //app IDs from SteamSpy database
	// fmt.Println("Retrieving games from SteamSpy database...")
	// appIDs := get_steamspy_appids()

	// //from that we now process each game through the enrichment pipeline
	// fmt.Println("Processing games through enrichment pipeline...")
	// for _, appID := range appIDs {
	// 	fmt.Printf("Processing AppID: %d\n", appID)
	processGame(100, "name")
	// }

	// print summary of processed data
}

func createDB(db *sql.DB) {
	createKey := `
	CREATE TABLE IF NOT EXISTS main_game (
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,
		game_name     TEXT,
		steam_appid   INTEGER
	);
	`

	_, err := db.Exec(createKey)
	if err != nil {
		log.Fatal("Failed to create users table:", err)
	}

	createSteamspy := `
	CREATE TABLE IF NOT EXISTS steam_spy (
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,  
		steam_appid   INTEGER
		positive_reviews  INTEGER, 
		negative_reviews  INTEGER, 
		owners            INTEGER, 
		FOREIGN KEY(steam_appid) REFERENCES main_game(steam_appid) ON DELETE CASCADE
	);
	`

	_, err = db.Exec(createSteamspy)
	if err != nil {
		log.Fatal("Failed to create users table:", err)
	}

	createSteamapi := `
	CREATE TABLE IF NOT EXISTS game_details (
		detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
		game_id INTEGER,
		genre TEXT,
		description TEXT,
		website TEXT,
		header_image TEXT,
		background TEXT,
		icon TEXT,
		screenshot TEXT,
		steam_url TEXT,
		pricing TEXT,
		achievements TEXT,
		FOREIGN KEY(game_id) REFERENCES main_game(game_id) ON DELETE CASCADE
	);
	`

	_, err = db.Exec(createSteamapi)
	if err != nil {
		log.Fatal("Failed to create users table:", err)
	}

}

// Modular way of  adding to  the full enrichment pipeline for a single game
func processGame(appID int, name string) {

	if err := os.Remove("./steam_api.db"); err != nil && !os.IsNotExist(err) {
		log.Fatal("Failed to delete existing steam_api.db file:", err)
	} else {
		fmt.Println("Existing steam_api.db file deleted.")
	}

	fmt.Println(appID)
	// first lets create a table with the app id

	db, err := sql.Open("sqlite3", "./steam_api.db")
	if err != nil {
		log.Fatal(err)
	}

	// creates the empty tables
	createDB(db)

	defer db.Close()
}
