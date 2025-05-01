package main

import (
	"database/sql"
	"fmt"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

func steamspy_appids() []int {
	var appids []int
	db, err := sql.Open("sqlite3", "./steamspy_top50.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	rows, err := db.Query(`SELECT appid FROM top_games LIMIT 50`)
	if err != nil {
		log.Fatal(err)
	}
	defer rows.Close()

	for rows.Next() {
		var appid int
		if err := rows.Scan(&appid); err != nil {
			log.Fatal(err)
		}
		fmt.Println("AppID:", appid)
		appids = append(appids, appid)

	}
	return appids

}
