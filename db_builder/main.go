package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

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

	fmt.Println("Migration from steamspy_top50.db to steam_api.db completed.")
}

func add_steam_API(appID int, tx *sql.Tx) error {
	genre, description, website, headerImage, background, screenshot, steamURL, pricing, achievements := steamApiPull(appID)

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
	genreList := strings.Split(genre, ", ")
	for _, g := range genreList {
		_, err = tx.Exec(`
			INSERT OR REPLACE INTO genres (steam_appid, genre)
			VALUES (?, ?)`,
			appID, g,
		)
		if err != nil {
			return err
		}
	}

	return nil
}
