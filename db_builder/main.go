package main

import (
	"fmt"
	"log"

	"os"

	_ "github.com/mattn/go-sqlite3"
	openai "github.com/sashabaranov/go-openai"
)

func main() {

	gametags, err := gameVerdicts()
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

	// ok now I want to find the steam appid assoiated with  before data insertion
	client := openai.NewClient(os.Getenv("OPENAI_API_KEY"))

	findMatches(*client)
}
