package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

// pulls from steam store page based on the unique game id
func steamApiPull(appID string) (name string, description string, price string, descriptiontag string, genretag string) {
	url := fmt.Sprintf("https://store.steampowered.com/api/appdetails?appids=%s", appID)

	resp, err := http.Get(url)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()

	var result map[string]struct {
		Success bool `json:"success"`
		Data    struct {
			Name       string   `json:"name"`
			Type       string   `json:"type"`
			ShortDesc  string   `json:"short_description"`
			Publishers []string `json:"publishers"`
			IsFree     bool     `json:"is_free"`
			Price      struct {
				FinalFormatted string `json:"final_formatted"`
			} `json:"price_overview"`
			Categories []struct {
				ID          int    `json:"id"`
				Description string `json:"description"`
			} `json:"categories"`
			Genres []struct {
				ID          string `json:"id"`
				Description string `json:"description"`
			} `json:"genres"`
		} `json:"data"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		panic(err)
	}

	info := result[appID]

	var tagHolder []string

	for _, category := range info.Data.Categories {
		tagHolder = append(tagHolder, category.Description)
	}

	descriptionTags := strings.Join(tagHolder, ", ")

	for _, genre := range info.Data.Genres {
		tagHolder = append(tagHolder, genre.Description)
	}

	genreTags := strings.Join(tagHolder, ", ")

	return info.Data.Name, info.Data.ShortDesc, info.Data.Price.FinalFormatted, descriptionTags, genreTags
}
