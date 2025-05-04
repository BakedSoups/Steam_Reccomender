package main

import (
	"fmt"
	"strconv"

	_ "github.com/mattn/go-sqlite3"
)

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
