package main

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// pulls from steam store page based on the unique game id
func steamApiPull(appID string) (name string, description string, price string) {
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
		} `json:"data"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		panic(err)
	}

	info := result[appID]

	return info.Data.Name, info.Data.ShortDesc, info.Data.Price.FinalFormatted
}
