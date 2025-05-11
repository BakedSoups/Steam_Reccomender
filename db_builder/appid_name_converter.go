package main

import (
	"encoding/json"
	"io"
	"os"

	"github.com/lithammer/fuzzysearch/fuzzy"
	_ "github.com/mattn/go-sqlite3"
)

// working with simpler json file
type Gametag struct {
	Name string `json:"name"`
}

func Match(appidName, inputName string) (string, bool) {
	if fuzzy.MatchFold(inputName, appidName) {
		return appidName, true
	}
	return "", false
}

func gameVerdicts() ([]Gametag, error) {
	file, err := os.Open("./tag_builder/game_verdicts_complete.json")

	if err != nil {
		return nil, err
	}
	defer file.Close()

	bytes, err := io.ReadAll(file)
	if err != nil {
		return nil, err
	}
	var gametags []Gametag

	err = json.Unmarshal(bytes, &gametags)
	if err != nil {
		return nil, err
	}

	return gametags, nil

}
