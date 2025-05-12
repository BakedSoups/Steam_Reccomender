package main

import (
	"database/sql"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

func main() {

	// game:= "Persona 3 Reload"
	// appid := "2161700"

	db, err := sql.Open("sqlite3", "./db_builder/steam_api.db")

	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	// Replace `id` with your actual column name if different
	_, err = db.Exec(`DELETE FROM ign_unique_tags WHERE game_id > 409`)
	if err != nil {
		log.Fatal("Failed to delete rows:", err)
	}

	log.Println("Rows below line 533 deleted.")

	// rows, err := db.Query(`SELECT * FROM main_game WHERE appid = ?`, appid)
	// if err != nil {
	// 	log.Fatal(err)
	// }
	// defer rows.Close()

	// // the amount of columns that are in my given row function
	// columns, err := rows.Columns()
	// if err != nil {
	// 	log.Fatal(err)
	// }

	// for rows.Next() {
	// 	values := make([]interface{}, len(columns))
	// 	valuePtrs := make([]interface{}, len(columns))
	// 	for i := range values {
	// 		valuePtrs[i] = &values[i]
	// 	}

	// 	if err := rows.Scan(valuePtrs...); err != nil {
	// 		log.Fatal(err)
	// 	}

	// 	row := make(map[string]interface{})
	// 	for i, col := range columns {
	// 		val := values[i]
	// 		if b, ok := val.([]byte); ok {
	// 			row[col] = string(b)
	// 		} else {
	// 			row[col] = val
	// 		}
	// 	}

	// 	fmt.Println(row)
	// }
}
