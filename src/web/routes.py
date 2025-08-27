from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from typing import Dict, Any, Optional
from ..services.game_service import GameService
from ..utils.logging import get_logger

logger = get_logger(__name__)


def create_routes(game_service: GameService) -> Blueprint:
    bp = Blueprint('main', __name__)
    
    @bp.route('/')
    def index():
        session.clear()
        return render_template('index.html')
    
    @bp.route('/search', methods=['POST'])
    def search():
        search_query = request.form.get('search_query', '')
        if not search_query:
            return redirect(url_for('main.index'))
        
        try:
            matches = game_service.find_games_by_name(search_query)
            
            if not matches:
                logger.info(f"No matches found for query: {search_query}")
                return redirect(url_for('main.index'))
            
            best_match = matches[0]
            target_appid = best_match['steam_appid']
            
            reference_game = game_service.get_game_details(target_appid)
            if not reference_game:
                logger.error(f"Could not get details for game {target_appid}")
                return redirect(url_for('main.index'))
            
            preferences = game_service.get_available_preferences(target_appid)
            
            session['reference_game'] = reference_game
            session['target_appid'] = target_appid
            session['available_preferences'] = preferences
            
            return render_template('preference_hierarchical.html', 
                                  reference_game=reference_game,
                                  preferences=preferences)
        
        except Exception as e:
            logger.error(f"Error in search: {e}")
            return redirect(url_for('main.index'))
    
    @bp.route('/recommend', methods=['POST'])
    def recommend():
        target_appid = session.get('target_appid')
        reference_game = session.get('reference_game', {})
        
        if not target_appid:
            return redirect(url_for('main.index'))
        
        try:
            user_preferences = _extract_user_preferences(request)
            logger.info(f"User preferences: {user_preferences}")
            
            similar_games = game_service.find_similar_games(
                target_appid, user_preferences, limit=10
            )
            
            return render_template('results_hierarchical.html',
                                  games=similar_games,
                                  reference_game=reference_game,
                                  user_preferences=user_preferences)
        
        except Exception as e:
            logger.error(f"Error in recommend: {e}")
            return redirect(url_for('main.index'))
    
    @bp.route('/api/search', methods=['GET'])
    def api_search():
        search_query = request.args.get('search_query', request.args.get('q', ''))
        
        if len(search_query) < 2:
            if request.headers.get('HX-Request'):
                return render_template('partials/search_results.html', games=[])
            return jsonify([])
        
        try:
            matches = game_service.find_games_by_name(search_query, limit=10)
            
            if request.headers.get('HX-Request') or 'text/html' in request.headers.get('Accept', ''):
                return render_template('partials/search_results.html', games=matches)
            
            results = []
            for match in matches:
                results.append({
                    'id': match['steam_appid'],
                    'name': match['name'],
                    'image': match['header_image'],
                    'genre': f"{match['main_genre']} → {match['sub_genre']}",
                    'data_source': 'hierarchical'
                })
            
            return jsonify(results)
            
        except Exception as e:
            logger.error(f"Error in API search: {e}")
            if request.headers.get('HX-Request'):
                return render_template('partials/search_results.html', games=[])
            return jsonify([])
    
    @bp.route('/debug/game/<int:steam_appid>')
    def debug_game(steam_appid: int):
        try:
            game = game_service.get_game_details(steam_appid)
            preferences = game_service.get_available_preferences(steam_appid)
            
            return jsonify({
                'game': game,
                'preferences': preferences
            })
        except Exception as e:
            logger.error(f"Error in debug_game: {e}")
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/debug/stats')
    def debug_stats():
        try:
            stats = game_service.get_database_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error in debug_stats: {e}")
            return jsonify({'error': str(e)}), 500
    
    return bp


def _extract_user_preferences(request) -> Dict[str, Any]:
    user_preferences = {
        'aesthetics': {},
        'preferred_tags': [],
        'preferred_steam_tags': []
    }
    
    for aesthetic in ['art_style', 'theme', 'music_style']:
        pref_value = request.form.get(f'prefer_{aesthetic}')
        if pref_value:
            user_preferences['aesthetics'][aesthetic] = pref_value
    
    preferred_tags = request.form.getlist('preferred_tags')
    user_preferences['preferred_tags'] = preferred_tags
    
    preferred_steam_tags = request.form.getlist('preferred_steam_tags')
    user_preferences['preferred_steam_tags'] = preferred_steam_tags
    
    return user_preferences