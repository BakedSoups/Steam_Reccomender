package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"

	_ "github.com/mattn/go-sqlite3"
	openai "github.com/sashabaranov/go-openai"
)

type Gametag struct {
	Name    string   `json:"name"`
	Score   string   `json:"score"`
	Url     string   `json:"url"`
	Verdict string   `json:"verdict"`
	Tags    []string `json:"tags"`
}

func findMatches(client openai.Client) {
	resp, err := client.CreateChatCompletion(
		context.Background(),
		openai.ChatCompletionRequest{
			Model: openai.GPT3Dot5Turbo,
			Messages: []openai.ChatCompletionMessage{
				{
					Role:    openai.ChatMessageRoleUser,
					Content: "Hello!",
				},
			},
		},
	)

	if err != nil {
		fmt.Printf("ChatCompletion error: %v\n", err)
		return
	}

	fmt.Println(resp.Choices[0].Message.Content)
}

func gameVerdicts() ([]Gametag, error) {
	file, err := os.Open("game_verdicts_with_tags.json")

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
