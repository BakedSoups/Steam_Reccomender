package main

import (
	"database/sql"
	"fmt"
	"log"
	"strconv"
	"strings"

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

	// Create a final database that will contain enriched data
	fmt.Println("Creating final database...")
	setupFinalDB()

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

// processGame handles the full enrichment pipeline for a single game
func processGame(appID int) {
	// Get base data from SteamSpy
	game, err := getBaseSteamSpyData(appID)
	if err != nil {
		log.Printf("Error getting base data for AppID %d: %v", appID, err)
		return
	}

	// Enrich with Steam API
	enrichWithSteamAPI(&game)

	// Enrich with other APIs (commented out for now)
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

// enrichWithSteamAPI adds data from the Steam API
func enrichWithSteamAPI(game *FinalGame) {
	// Convert int to string for API call
	appIDStr := strconv.Itoa(game.AppID)

	// Get data from Steam API
	name, description, price := steamApiPull(appIDStr)

	// Update game with new data (if available)
	if name != "" {
		game.Name = name
	}
	game.Description = description
	game.Price = price

	fmt.Printf("Enriched %s with Steam API data\n", game.Name)
}

// example of how to scale to a new API enrichment function
// func enrichWithNewAPI(game *FinalGame) {
//     // Get data from new API
//     genreList, releaseDate := newApiPull(strconv.Itoa(game.AppID))
//
//     // Update game with new data
//     game.GenreList = genreList
//     game.ReleaseDate = releaseDate
//
//     fmt.Printf("Enriched %s with New API data\n", game.Name)
// }

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
func setupFinalDB() {
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

// summary of all the fused data
func printSummary() {
	db, err := sql.Open("sqlite3", "./steam_enriched.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	var count int
	err = db.QueryRow("SELECT COUNT(*) FROM enriched_games").Scan(&count)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("\nETL Pipeline completed successfully!\n")
	fmt.Printf("Total games enriched: %d\n", count)

	// Show sample of enriched data
	rows, err := db.Query(`
		SELECT appid, name, price 
		FROM enriched_games 
		LIMIT 5
	`)
	if err != nil {
		log.Fatal(err)
	}
	defer rows.Close()

	fmt.Println("\nSample of enriched data:")
	fmt.Printf("%-10s %-30s %s\n", "AppID", "Name", "Price")
	fmt.Println(strings.Repeat("-", 50))

	for rows.Next() {
		var appID int
		var name, price string
		if err := rows.Scan(&appID, &name, &price); err != nil {
			log.Fatal(err)
		}
		fmt.Printf("%-10d %-30s %s\n", appID, name, price)
	}
}
