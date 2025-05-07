package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
)

// pulls from steam store page based on the unique game id
func steamApiPull(appID int) (
	genre, description, website, headerImage, background, screenshot, steamURL, pricing, achievements string,
) {
	str := strconv.Itoa(appID)
	url := fmt.Sprintf("https://store.steampowered.com/api/appdetails?appids=%s", str)

	resp, err := http.Get(url)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()

	var result map[string]struct {
		Success bool `json:"success"`
		Data    struct {
			ShortDesc   string `json:"short_description"`
			Website     string `json:"website"`
			HeaderImage string `json:"header_image"`
			Background  string `json:"background"`
			Genres      []struct {
				Description string `json:"description"`
			} `json:"genres"`
			Screenshots []struct {
				PathFull string `json:"path_full"`
			} `json:"screenshots"`
			PriceOverview struct {
				FinalFormatted string `json:"final_formatted"`
			} `json:"price_overview"`
			Achievements struct {
				Total int `json:"total"`
			} `json:"achievements"`
		} `json:"data"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		panic(err)
	}

	info := result[str].Data

	// Join genres
	var genreList []string
	for _, g := range info.Genres {
		genreList = append(genreList, g.Description)
	}
	genre = strings.Join(genreList, ", ")

	// first screenshot if exists
	if len(info.Screenshots) > 0 {
		screenshot = info.Screenshots[0].PathFull
	}

	// steam store URL
	steamURL = fmt.Sprintf("https://store.steampowered.com/app/%s", str)

	// achievements to string
	achievements = fmt.Sprintf("%d achievements", info.Achievements.Total)

	return genre, info.ShortDesc, info.Website, info.HeaderImage, info.Background, screenshot, steamURL, info.PriceOverview.FinalFormatted, achievements
}
