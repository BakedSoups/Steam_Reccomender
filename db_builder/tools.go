package main

// this is not being used
import (
	"os"

	openai "github.com/sashabaranov/go-openai"
)

// struct that holds clients and can scale later
type ToolManager struct {
	client *openai.Client
}

// creates a newinstance with open ai client
func NewToolManager() *ToolManager {
	return &ToolManager{
		client: openai.NewClient(os.Getenv("OPEN_API_KEY")),
	}
}

// this tells out current instance of chat gpt what tools are available and what parmaters they need so it understands:
// to input
// {
// 	"name": "reverse_text",
// 	"arguments": "{\"text\": \"hello\"}"
//   }

func (t *ToolManager) GetTools() []openai.Tool {
	return []openai.Tool{
		{
			Type: openai.ToolTypeFunction,
			Function: &openai.FunctionDefinition{
				Name:        "reverse_text",
				Description: "Reverses any text string",
				Parameters: map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"text": map[string]interface{}{
							"type":        "string",
							"description": "The text to reverse",
						},
					},
					"required": []string{"text"},
				},
			},
		},
	}
}

// response for name tool
type NameMatcherResponse struct {
	name       string
	status     string
	methodUsed string
}
