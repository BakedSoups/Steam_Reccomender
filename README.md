# Steam Recommender 
Have you ever finished a game and wanted to play one like it? 
If so, use this tool and you can find your next favorite game.

Basically, we gather as much info on a game that we can, create tags, apply weights to the tags, and using that the user can find new games.

![image](https://github.com/user-attachments/assets/2aff4217-270c-4ca3-befa-715a3fc5b0a1)

![image](https://github.com/user-attachments/assets/55db5ddd-8998-4992-a786-674c5ffa1c5f)

![image](https://github.com/user-attachments/assets/1cd779b3-6b5a-47af-9b17-ea311d79c065)

### Our glorious tech stack
![image](https://github.com/user-attachments/assets/2266a005-ea0d-4081-9836-69bc965eac51)

## Setup and Installation

1. Clone the repository:
```
git clone <repository_url>
cd Steam_Reccomender
```

2. Create and activate a virtual environment (recommended):
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```
pip install -r requirements.txt
```

4. Run the application:
```
python app.py
```

5. Access the web application at http://localhost:5000

## Usage

- Enter a game name in the search box to get recommendations
- Try searching for "Battlefield" or "Elden Ring" for demo results
- Click on a game to view its details
- Sort options are available to organize the results

## API Endpoints

- `/search` - POST endpoint for searching games
- `/game/<game_id>` - GET endpoint for viewing game details
- `/recommend/<game_name>` - GET endpoint for recommendations based on a specific game
- `/api/recommend?game=<game_name>` - GET endpoint for recommendations in JSON format

## Features

- Steam-like UI with game recommendations
- Game details view with information about each game
- Interactive UI elements (Add to Cart, Wishlist)
- Responsive design for different screen sizes

## Demo Data

The application includes demo data for:
- Battlefield series games
- Elden Ring

