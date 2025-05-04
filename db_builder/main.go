package main

import (
	"database/sql"
	"fmt"
	"log"

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
	// create update the SteamSpy database
	fmt.Println("Initializing SteamSpy database...")
	createSteamSpy()

	//final database that will contain enriched data
	fmt.Println("Creating final database...")
	initFinalDB()

	// Get app IDs from SteamSpy database
	fmt.Println("Retrieving games from SteamSpy database...")
	appIDs := get_steamspy_appids()

	// Process each game through the enrichment pipeline
	fmt.Println("Processing games through enrichment pipeline...")
	for _, appID := range appIDs {
		fmt.Printf("Processing AppID: %d\n", appID)
		processGame(appID)
	}

	// print summary of processed data
	printSummary()
}

// Modular way of  adding to  the full enrichment pipeline for a single game
func processGame(appID int) {
	// Get base data from SteamSpy
	game, err := getBaseSteamSpyData(appID)
	fmt.Println(game)
	if err != nil {
		log.Printf("Error getting base data for AppID %d: %v", appID, err)
		return
	}

	// Enrich with Steam API
	enrichWithSteamAPI(&game)

	// examples of scaling to more api
	// enrichWithNewAPI(&game)
	// enrichWithAnotherAPI(&game)

	// Save the fully enriched game to database
	saveEnrichedGame(game)
}

// getBaseSteamSpyData retrieves the base data from SteamSpy
func getBaseSteamSpyData(appID int) (FinalGame, error) {
	var game FinalGame

	db, err := sql.Open("sqlite3", "./steamspy_top50.db")
	if err != nil {
		return game, err
	}
	defer db.Close()

	err = db.QueryRow(`
		SELECT appid, name, developer, publisher, score_rank, 
			   positive, negative, owners, average_forever
		FROM top_games
		WHERE appid = ?
	`, appID).Scan(
		&game.AppID, &game.Name, &game.Developer, &game.Publisher,
		&game.ScoreRank, &game.Positive, &game.Negative,
		&game.Owners, &game.AvgPlaytime,
	)

	return game, err
}

// saves the fully enriched game to the database
func saveEnrichedGame(game FinalGame) {
	db, err := sql.Open("sqlite3", "./steam_enriched.db")
	if err != nil {
		log.Printf("Error opening database: %v", err)
		return
	}
	defer db.Close()

	// Insert enriched data into final database
	_, err = db.Exec(`
		INSERT OR REPLACE INTO enriched_games (
			appid, name, description, developer, publisher, 
			score_rank, positive, negative, owners, 
			average_forever, price
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`,
		game.AppID, game.Name, game.Description, game.Developer,
		game.Publisher, game.ScoreRank, game.Positive, game.Negative,
		game.Owners, game.AvgPlaytime, game.Price,
	)

	if err != nil {
		log.Printf("Error saving enriched data for AppID %d: %v", game.AppID, err)
		return
	}

	fmt.Printf("Successfully saved enriched data for %s (AppID: %d)\n", game.Name, game.AppID)
}

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
