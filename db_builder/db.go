package main

import (
	"bufio"
	"database/sql"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// creates a new DB, migrates steam spy pull ( steam spy needs to pull before this runs)
// gathers steam spy ids, populates add_steam_Api
func initDB() {
	os.Remove("./steam_api.db")

	db, err := sql.Open("sqlite3", "./steam_api.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	db.Exec("PRAGMA foreign_keys = ON;")

	createDB(db)
	migrateTop50ToSteamAPI(db)

	// Track progress to allow resuming
	processedFile := "./processed_apps.txt"
	processedApps := loadProcessedApps(processedFile)

	rows, err := db.Query(`SELECT steam_appid FROM main_game ORDER BY steam_appid`)
	if err != nil {
		log.Fatal("Failed to retrieve appIDs:", err)
	}
	defer rows.Close()

	var appIDs []int
	for rows.Next() {
		var appID int
		if err := rows.Scan(&appID); err != nil {
			log.Println("Scan failed:", err)
			continue
		}
		if !processedApps[appID] {
			appIDs = append(appIDs, appID)
		}
	}

	log.Printf("Found %d apps to process", len(appIDs))

	// Process in larger batches with less waiting
	batchSize := 25  // Increased from 10
	saveEvery := 100 // Save every 100 apps
	processedCount := 0

	for i := 0; i < len(appIDs); i += batchSize {
		end := i + batchSize
		if end > len(appIDs) {
			end = len(appIDs)
		}

		batch := appIDs[i:end]
		log.Printf("Processing batch %d-%d of %d", i+1, end, len(appIDs))

		tx, err := db.Begin()
		if err != nil {
			log.Fatal("Failed to begin transaction:", err)
		}

		for _, appID := range batch {
			if err := add_steam_API(appID, tx); err != nil {
				log.Printf("Insert failed for appID %d: %v", appID, err)
			} else {
				// Mark as processed only on success
				saveProcessedApp(processedFile, appID)
				processedCount++
			}

			// Reduced delay between requests
			time.Sleep(1500 * time.Millisecond) // 1.5 seconds instead of 3
		}

		if err := tx.Commit(); err != nil {
			log.Printf("Failed to commit batch: %v", err)
		}

		// Show progress every 100 apps
		if processedCount > 0 && processedCount%saveEvery == 0 {
			log.Printf("Progress: %d/%d apps processed (%.1f%%)",
				processedCount, len(appIDs),
				float64(processedCount)/float64(len(appIDs))*100)
		}

		// Reduced delay between batches
		if i+batchSize < len(appIDs) {
			log.Printf("Batch complete. Waiting 10 seconds before next batch...")
			time.Sleep(10 * time.Second) // Reduced from 30 seconds
		}
	}

	log.Printf("All apps processed successfully! Total: %d", processedCount)
}

func createDB(db *sql.DB) {
	// Create main_game table
	createKey := `
	CREATE TABLE IF NOT EXISTS main_game (
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,
		game_name     TEXT,
		steam_appid INTEGER NOT NULL UNIQUE
	);
	`
	_, err := db.Exec(createKey)
	if err != nil {
		log.Fatal("Failed to create main_game table:", err)
	}

	// Create steam_spy table
	createSteamspy := `
	CREATE TABLE IF NOT EXISTS steam_spy (
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,  
		steam_appid       INTEGER NOT NULL, 
		positive_reviews  INTEGER, 
		negative_reviews  INTEGER, 
		owners            INTEGER, 
		FOREIGN KEY(steam_appid) REFERENCES main_game(steam_appid) ON DELETE CASCADE
	);
	`
	_, err = db.Exec(createSteamspy)
	if err != nil {
		log.Fatal("Failed to create steam_spy table:", err)
	}

	// Create genres table
	createGenres := `
	CREATE TABLE IF NOT EXISTS genres (
		steam_appid INTEGER NOT NULL,
		genre TEXT NOT NULL,
		PRIMARY KEY (steam_appid, genre),
		FOREIGN KEY(steam_appid) REFERENCES main_game(steam_appid) ON DELETE CASCADE
	);
	`
	_, err = db.Exec(createGenres)
	if err != nil {
		log.Fatal("Failed to create genres table:", err)
	}

	// Create steam_api table
	createSteamapi := `
	CREATE TABLE IF NOT EXISTS steam_api (
		detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
		steam_appid INTEGER NOT NULL,
		description TEXT,
		website TEXT,
		header_image TEXT,
		background TEXT,
		screenshot TEXT,
		steam_url TEXT,
		pricing TEXT,
		achievements TEXT,
		FOREIGN KEY(steam_appid) REFERENCES main_game(steam_appid) ON DELETE CASCADE
	);
	`
	_, err = db.Exec(createSteamapi)
	if err != nil {
		log.Fatal("Failed to create steam_api table:", err)
	}
}

func migrateTop50ToSteamAPI(dstDB *sql.DB) {
	srcDB, err := sql.Open("sqlite3", "./steamspy_all_games.db")
	if err != nil {
		log.Fatal("Failed to open source DB:", err)
	}
	defer srcDB.Close()

	rows, err := srcDB.Query(`SELECT appid, name, positive, negative, owners FROM all_games`)
	if err != nil {
		log.Fatal("Failed to query source DB:", err)
	}
	defer rows.Close()

	for rows.Next() {
		var appID int
		var name string
		var positive int
		var negative int
		var owners string

		if err := rows.Scan(&appID, &name, &positive, &negative, &owners); err != nil {
			log.Println("Row scan failed:", err)
			continue
		}

		_, err = dstDB.Exec(`INSERT OR IGNORE INTO main_game (game_name, steam_appid) VALUES (?, ?)`, name, appID)
		if err != nil {
			log.Println("Insert into main_game failed:", err)
			continue
		}

		_, err = dstDB.Exec(`
			INSERT OR REPLACE INTO steam_spy (steam_appid, positive_reviews, negative_reviews, owners)
			VALUES (?, ?, ?, ?)`,
			appID, positive, negative, owners,
		)
		if err != nil {
			log.Println("Insert into steam_spy failed:", err)
		}
	}

	fmt.Println("Migration from our initial db: init_steamspy.db to steam_api.db completed.")
}

func add_steam_API(appID int, tx *sql.Tx) error {
	genre, description, website, headerImage, background, screenshot, steamURL, pricing, achievements := steamApiPull(appID)

	// Skip if we got no data
	if genre == "" && description == "" && website == "" {
		return fmt.Errorf("no data retrieved for app %d", appID)
	}

	_, err := tx.Exec(`
		INSERT INTO steam_api (
			steam_appid,
			description,
			website,
			header_image,
			background,
			screenshot,
			steam_url,
			pricing,
			achievements
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		appID, description, website, headerImage, background, screenshot, steamURL, pricing, achievements,
	)
	if err != nil {
		return err
	}

	//genres into genres table
	if genre != "" {
		genreList := strings.Split(genre, ", ")
		for _, g := range genreList {
			if g != "" { // Skip empty genres
				_, err = tx.Exec(`
					INSERT OR REPLACE INTO genres (steam_appid, genre)
					VALUES (?, ?)`,
					appID, g,
				)
				if err != nil {
					return err
				}
			}
		}
	}

	return nil
}

// Helper functions for tracking progress
func loadProcessedApps(filename string) map[int]bool {
	processed := make(map[int]bool)
	file, err := os.Open(filename)
	if err != nil {
		return processed
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if appID, err := strconv.Atoi(scanner.Text()); err == nil {
			processed[appID] = true
		}
	}
	return processed
}

func saveProcessedApp(filename string, appID int) {
	file, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer file.Close()

	fmt.Fprintf(file, "%d\n", appID)
}
