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
	os.Remove("./steam_api.db")

	db, err := sql.Open("sqlite3", "./steam_api.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	db.Exec("PRAGMA foreign_keys = ON;")

	createDB(db)
	migrateTop50ToSteamAPI(db)

	rows, err := db.Query(`SELECT steam_appid FROM main_game`)
	if err != nil {
		log.Fatal("Failed to retrieve appIDs:", err)
	}
	defer rows.Close()
	tx, err := db.Begin()
	if err != nil {
		log.Fatal("Failed to begin transaction:", err)
	}

	for rows.Next() {
		var appID int
		if err := rows.Scan(&appID); err != nil {
			log.Println("Scan failed:", err)
			continue
		}
		if err := add_steam_API(appID, tx); err != nil {
			log.Println("Insert failed for appID", appID, ":", err)
		}
	}

	if err := tx.Commit(); err != nil {
		log.Fatal("Failed to commit transaction:", err)
	}

}

func createDB(db *sql.DB) {
	createKey := `
	CREATE TABLE IF NOT EXISTS main_game (
		game_id INTEGER PRIMARY KEY AUTOINCREMENT,
		game_name     TEXT,
		steam_appid INTEGER NOT NULL UNIQUE
	);
	`

	_, err := db.Exec(createKey)
	if err != nil {
		log.Fatal("Failed to create users table:", err)
	}

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
		log.Fatal("Failed to create users table:", err)
	}

	createSteamapi := `
	CREATE TABLE IF NOT EXISTS steam_api (
		detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
		steam_appid INTEGER NOT NULL,
		genre TEXT,
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
		log.Fatal("Failed to create users table:", err)
	}

}

// func deleteGameByAppID(appID int) {
// 	db, err := sql.Open("sqlite3", "./steam_api.db")
// 	if err != nil {
// 		log.Fatal(err)
// 	}
// 	defer db.Close()

// 	_, err = db.Exec("PRAGMA foreign_keys = ON;")
// 	if err != nil {
// 		log.Fatal("Failed to enable foreign keys:", err)
// 	}

// 	_, err = db.Exec(`DELETE FROM main_game WHERE steam_appid = ?`, appID)
// 	if err != nil {
// 		log.Fatal("Delete failed:", err)
// 	}

// 	fmt.Println("Deleted game with steam_appid:", appID)
// }

func migrateTop50ToSteamAPI(dstDB *sql.DB) {
	srcDB, err := sql.Open("sqlite3", "./steamspy_top50.db")
	if err != nil {
		log.Fatal("Failed to open source DB:", err)
	}
	defer srcDB.Close()

	rows, err := srcDB.Query(`SELECT appid, name, positive, negative, owners FROM top_games`)
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

		// Insert into main_game
		_, err = dstDB.Exec(`INSERT OR IGNORE INTO main_game (game_name, steam_appid) VALUES (?, ?)`, name, appID)
		if err != nil {
			log.Println("Insert into main_game failed:", err)
			continue
		}

		// Insert into steam_spy
		_, err = dstDB.Exec(`
			INSERT OR REPLACE INTO steam_spy (steam_appid, positive_reviews, negative_reviews, owners)
			VALUES (?, ?, ?, ?)`,
			appID, positive, negative, owners,
		)
		if err != nil {
			log.Println("Insert into steam_spy failed:", err)
		}
	}

	fmt.Println("Migration from steamspy_top50.db to steam_api.db completed.")
}

func add_steam_API(appID int, tx *sql.Tx) error {
	genre, description, website, headerImage, background, screenshot, steamURL, pricing, achievements := steamApiPull(appID)
	_, err := tx.Exec(`
		INSERT INTO steam_api (
			steam_appid,
			genre,
			description,
			website,
			header_image,
			background,
			screenshot,
			steam_url,
			pricing,
			achievements
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		appID, genre, description, website, headerImage, background, screenshot, steamURL, pricing, achievements,
	)
	return err
}
