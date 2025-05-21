package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// pulls from steam store page based on the unique game id
func steamApiPull(appID int) (
	genre, description, website, headerImage, background, screenshot, steamURL, pricing, achievements string,
) {
	str := strconv.Itoa(appID)
	url := fmt.Sprintf("https://store.steampowered.com/api/appdetails?appids=%s", str)

	maxRetries := 3
	for attempt := 0; attempt < maxRetries; attempt++ {
		resp, err := http.Get(url)
		if err != nil {
			log.Printf("Failed to fetch data for app %d: %v", appID, err)
			return
		}
		defer resp.Body.Close()

		// If rate limited, wait and retry
		if resp.StatusCode == 429 {
			retryAfter := resp.Header.Get("Retry-After")
			wait := 30 * time.Second // Reduced default wait time

			if retryAfter != "" {
				if seconds, err := strconv.Atoi(retryAfter); err == nil {
					wait = time.Duration(seconds) * time.Second
				}
			}

			log.Printf("Rate limited for app %d. Waiting %v before retry %d/%d",
				appID, wait, attempt+1, maxRetries)
			time.Sleep(wait)
			continue
		}

		// Check other bad statuses
		if resp.StatusCode != http.StatusOK {
			log.Printf("Bad status for app %d: %s", appID, resp.Status)
			return
		}

		// Read the response body
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			log.Printf("Failed to read response for app %d: %v", appID, err)
			return
		}

		// Check if response starts with HTML (error page)
		if strings.HasPrefix(string(body), "<") {
			log.Printf("Got HTML response for app %d, likely rate limited or invalid ID", appID)
			time.Sleep(5 * time.Second) // Brief pause before retry
			continue
		}

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

		if err := json.Unmarshal(body, &result); err != nil {
			log.Printf("Failed to parse JSON for app %d: %v", appID, err)
			return
		}

		// Check if the API call was successful
		appData, exists := result[str]
		if !exists || !appData.Success {
			log.Printf("API returned success=false for app %d", appID)
			return
		}

		info := appData.Data

		// Join genres
		var genreList []string
		for _, g := range info.Genres {
			genreList = append(genreList, g.Description)
		}
		genre = strings.Join(genreList, ", ")

		// First screenshot if exists
		if len(info.Screenshots) > 0 {
			screenshot = info.Screenshots[0].PathFull
		}

		// Steam store URL
		steamURL = fmt.Sprintf("https://store.steampowered.com/app/%s", str)

		// Achievements to string
		if info.Achievements.Total > 0 {
			achievements = fmt.Sprintf("%d achievements", info.Achievements.Total)
		} else {
			achievements = "0 achievements"
		}

		return genre, info.ShortDesc, info.Website, info.HeaderImage, info.Background,
			screenshot, steamURL, info.PriceOverview.FinalFormatted, achievements
	}

	return // Return empty if all retries failed
}
