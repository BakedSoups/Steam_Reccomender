import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    steam_api_db: str = "./steam_api.db"
    recommendations_db: str = "./steam_recommendations.db"
    vectorizer_path: str = "./hierarchical_vectorizer.pkl"
    
    def __post_init__(self):
        self.steam_api_db = os.path.abspath(self.steam_api_db)
        self.recommendations_db = os.path.abspath(self.recommendations_db)
        self.vectorizer_path = os.path.abspath(self.vectorizer_path)

@dataclass
class FlaskConfig:
    secret_key: str = "steam_game_recommender_secret_key"
    debug: bool = True
    host: str = "localhost"
    port: int = 5000

@dataclass
class AppConfig:
    database: DatabaseConfig
    flask: FlaskConfig
    
    @classmethod
    def create_default(cls) -> 'AppConfig':
        return cls(
            database=DatabaseConfig(),
            flask=FlaskConfig()
        )
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        config = cls.create_default()
        
        if steam_api_db := os.getenv('STEAM_API_DB'):
            config.database.steam_api_db = steam_api_db
        
        if recommendations_db := os.getenv('RECOMMENDATIONS_DB'):
            config.database.recommendations_db = recommendations_db
        
        if vectorizer_path := os.getenv('VECTORIZER_PATH'):
            config.database.vectorizer_path = vectorizer_path
        
        if secret_key := os.getenv('FLASK_SECRET_KEY'):
            config.flask.secret_key = secret_key
        
        if debug := os.getenv('FLASK_DEBUG'):
            config.flask.debug = debug.lower() in ('true', '1', 'yes')
        
        return config