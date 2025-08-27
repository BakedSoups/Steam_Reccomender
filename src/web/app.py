from flask import Flask
from ..config.settings import AppConfig
from ..data.repositories import RecommendationsRepository, SteamApiRepository
from ..services.game_service import GameService
from ..utils.logging import configure_logging, get_logger
from .routes import create_routes

logger = get_logger(__name__)


def create_app(config: AppConfig = None) -> Flask:
    if config is None:
        config = AppConfig.from_env()
    
    configure_logging()
    
    app = Flask(__name__, 
                template_folder='../../templates',
                static_folder='../../static')
    
    app.config['SECRET_KEY'] = config.flask.secret_key
    
    recommendations_repo = RecommendationsRepository(config.database.recommendations_db)
    steam_api_repo = SteamApiRepository(config.database.steam_api_db)
    
    game_service = GameService(
        recommendations_repo=recommendations_repo,
        steam_api_repo=steam_api_repo,
        vectorizer_path=config.database.vectorizer_path
    )
    
    routes_bp = create_routes(game_service)
    app.register_blueprint(routes_bp)
    
    _validate_databases(config)
    
    return app


def _validate_databases(config: AppConfig):
    if not RecommendationsRepository(config.database.recommendations_db).exists():
        logger.error(f"{config.database.recommendations_db} not found!")
        logger.error("Please run the JSON converter first: python json_to_sqlite_converter.py")
    else:
        logger.info(f"Found recommendations database: {config.database.recommendations_db}")
    
    if not SteamApiRepository(config.database.steam_api_db).exists():
        logger.warning(f"{config.database.steam_api_db} not found - images and pricing will use defaults")
    else:
        logger.info(f"Found Steam API database: {config.database.steam_api_db}")