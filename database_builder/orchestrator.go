package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"database/sql"

	"log"

	_ "github.com/mattn/go-sqlite3"
)

func main() {
	// FIRST RUN tag_builder scrape.py then extract_verdicts.py this program needs game_verdicts_with_ratio_tags.json to run
	if warning() {
		fmt.Println("Proceeding...")
	} else {
		fmt.Println("Operation canceled.")
	}

	// creates steamspy (this gives us the appids we need)
	createSteamSpy()

	// creates tables for steam powered end points
	// poppulates tables
	initDB()
	migrate()
}

func migrate() {
	db, err := sql.Open("sqlite3", "./steam_api.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	db.Exec("PRAGMA foreign_keys = ON;")
	// creates ign table
	createACGTable(db)
	// migrate data from json into table
	migrateACG(db)

}

func warning() bool {
	reader := bufio.NewReader(os.Stdin)

	fmt.Print("WARNING: the creation of the database takes 1 day due to endpoint restrictions\n I undestand(y/n):")
	input, err := reader.ReadString('\n')
	if err != nil {
		fmt.Println("Error reading input:", err)
		return false
	}

	input = strings.TrimSpace(strings.ToLower(input))
	if input == "y" {
		return true
	} else if input == "n" {
		return false
	} else {
		fmt.Println("Invalid input. Please enter 'y' or 'n'.")
		return false
	}
}
