package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"

	_ "github.com/mattn/go-sqlite3"
)

// {
//     "name": "Commandos: Origins",
//     "score": "8",
//     "url": "https://www.ign.com/articles/commandos-origins-review",
//     "verdict": "Commandos: Origins strikes a great balance between the classic stealth tactics games and modern streamlined ideas, creating tons of potential for finding creative solutions to problems like “too many living fascists.” Pruning out elements like inventory management may not be to every older fan’s tastes, but that’s focused a spotlight on strict stealth – and it’s here Origins shines. Sneaking through its massive maps, each of which are swarming with hundreds of enemies, takes hours and hours of patient planning and careful clicking. I regularly gleaned a ton of pleasure from executing a perfect coordinated strike and fading away into the background, with the remaining Nazis none the wiser. No plan survives contact with this many bugs, but quick-loading will get you past nearly any issue and this otherwise might be the sneakiest fun you can have going commando with your underwear on.",
//     "tags": [
//       "Stealth",
//       "Tactics",
//       "Modern",
//       "World War II",
//       "Large Maps",
//       "Planning",
//       "Real-time Strategy"
//     ]
//   },
//   {

type Gametag struct {
	Name    string   `json:"name"`
	Score   string   `json:"score"`
	Url     string   `json:"url"`
	Verdict string   `json:"verdict"`
	Tags    []string `json:"tags"`
}

func main() {
	file, err := os.Open("python/game_verdicts_with_tags.json")

	if err != nil {
		log.Fatal("ERROR: %v", err)
	}
	defer file.Close()

	bytes, err := io.ReadAll(file)
	if err != nil {
		log.Fatal("ERROR: %v\n", err)
	}

	var gametags []Gametag

	err = json.Unmarshal(bytes, &gametags)
	if err != nil {
		log.Fatal("ERROR: %v\n", err)
	}

	for i, game := range gametags {
		fmt.Printf("\nGame %d:\n", i+1)
		fmt.Printf("Name: %s\n", game.Name)
		fmt.Printf("Score: %s\n", game.Score)
		fmt.Printf("URL: %s\n", game.Url)
		fmt.Printf("Tags: %v\n", game.Tags)
	}

}
