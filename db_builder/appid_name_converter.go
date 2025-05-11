package main

import (
	"encoding/json"
	"io"
	"os"
	"regexp"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

// working with simpler json file
type Gametag struct {
	Name          string         `json:"name"`
	Score         float64        `json:"numeric_score"`
	Ratio         map[string]int `json:"tag_ratios"` //this is going to have to be in a seperate table
	MainGenre     string         `json:"main_genre"`
	UniqueTag     []string       `json:"unique_tags"`
	SubjectiveTag []string       `json:"subjective_tags"`
}

// this extracts the output json and gives me what I need for matching
func gameVerdicts() ([]Gametag, error) {
	file, err := os.Open("./tag_builder/game_verdicts_with_ratio_tags.json")

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

// takes in the data base name and current name, then returns the db name and boolean
func Match(dbName, searchName string) (string, bool) {
	dbNameLower := strings.ToLower(strings.TrimSpace(dbName))
	searchNameLower := strings.ToLower(strings.TrimSpace(searchName))

	// 1. Exact match - perfect match case-insensitive
	if dbNameLower == searchNameLower {
		return dbName, true
	}

	// 2. Special handling for Early Access and similar suffixes
	cleanSuffixes := func(name string) string {
		suffixes := []string{" early access", " demo", " beta", " alpha"}
		result := name
		for _, suffix := range suffixes {
			result = strings.TrimSuffix(result, suffix)
		}
		return result
	}

	dbNameClean := cleanSuffixes(dbNameLower)
	searchNameClean := cleanSuffixes(searchNameLower)

	if dbNameClean == searchNameClean {
		return dbName, true
	}

	// 3. CRITICAL: Handle numbered sequels - STRICT MATCHING
	reNum := regexp.MustCompile(`\b\d+\b`)
	dbHasNum := reNum.MatchString(dbNameLower)
	searchHasNum := reNum.MatchString(searchNameLower)

	// If search has a number but DB doesn't (or vice versa), NO MATCH
	if dbHasNum != searchHasNum {
		return "", false
	}

	if dbHasNum && searchHasNum {
		dbNums := reNum.FindAllString(dbNameLower, -1)
		searchNums := reNum.FindAllString(searchNameLower, -1)

		// If numbers don't match, NO MATCH ( this solves the matching of series)
		if !sameNumbers(dbNums, searchNums) {
			return "", false
		}

		dbNameWithoutNum := reNum.ReplaceAllString(dbNameLower, "NUMBER")
		searchNameWithoutNum := reNum.ReplaceAllString(searchNameLower, "NUMBER")

		// Check if the structure is the same after removing numbers
		if dbNameWithoutNum == searchNameWithoutNum {
			return dbName, true
		}
	}

	// 4. Handle subtitles with colon
	if strings.Contains(dbNameLower, ":") && strings.Contains(searchNameLower, ":") {
		dbParts := strings.SplitN(dbNameLower, ":", 2)
		searchParts := strings.SplitN(searchNameLower, ":", 2)

		if strings.TrimSpace(dbParts[0]) == strings.TrimSpace(searchParts[0]) {
			dbSubtitle := strings.TrimSpace(dbParts[1])
			searchSubtitle := strings.TrimSpace(searchParts[1])

			if dbSubtitle == searchSubtitle {
				return dbName, true
			}

			if reNum.MatchString(dbSubtitle) || reNum.MatchString(searchSubtitle) {
				// If either subtitle has a number, they must match exactly
				return "", false
			}

			// For non-numbered subtitles, allow some similarity
			similarity := calculateSimilarity(dbSubtitle, searchSubtitle)
			if similarity > 0.8 {
				return dbName, true
			}
		}
		return "", false
	}

	// 5. If one has a subtitle and the other doesn't, generally no match
	if strings.Contains(dbNameLower, ":") != strings.Contains(searchNameLower, ":") {
		return "", false
	}

	if !dbHasNum && !searchHasNum && !strings.Contains(dbNameLower, ":") && !strings.Contains(searchNameLower, ":") {
		similarity := calculateSimilarity(dbNameLower, searchNameLower)
		if similarity > 0.9 { // Very high threshold
			return dbName, true
		}
	}

	return "", false
}

// Helper func to check if two slices of number strings have the same content
// this is to help remove matching sequels
func sameNumbers(nums1, nums2 []string) bool {
	if len(nums1) != len(nums2) {
		return false
	}

	// Create maps to count occurrences
	count1 := make(map[string]int)
	count2 := make(map[string]int)

	for _, num := range nums1 {
		count1[num]++
	}

	for _, num := range nums2 {
		count2[num]++
	}

	// Compare counts
	for num, count := range count1 {
		if count2[num] != count {
			return false
		}
	}

	return true
}

// diy fuzzy match
func calculateSimilarity(s1, s2 string) float64 {
	longer := s1
	shorter := s2
	if len(s1) < len(s2) {
		longer = s2
		shorter = s1
	}

	if len(longer) == 0 {
		return 1.0
	}

	// Count character matches
	matches := 0
	for i := 0; i < len(shorter); i++ {
		if longer[i] == shorter[i] {
			matches++
		}
	}

	return float64(matches) / float64(len(longer))
}
