package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"

	_ "github.com/mattn/go-sqlite3"
)

type Gametag struct {
	Name    string   `json:"name"`
	Score   string   `json:"score"`
	Url     string   `json:"url"`
	Verdict string   `json:"verdict"`
	Tags    []string `json:"tags"`
}

func main() {
	file, err := os.Open("game_verdicts_with_tags.json")

	if err != nil {
		log.Fatal("ERROR: ", err)
	}
	defer file.Close()

	bytes, err := io.ReadAll(file)
	if err != nil {
		log.Fatal("ERROR: ", err)
	}

	var gametags []Gametag

	err = json.Unmarshal(bytes, &gametags)
	if err != nil {
		log.Fatal("ERROR: ", err)
	}

	for i, game := range gametags {
		fmt.Printf("\nGame %d:\n", i+1)
		fmt.Printf("Name: %s\n", game.Name)
		fmt.Printf("Score: %s\n", game.Score)
		fmt.Printf("URL: %s\n", game.Url)
		fmt.Printf("Tags: %v\n", game.Tags)
	}

	// ok now I want to comapare any potential duplicates before data insertion

}
