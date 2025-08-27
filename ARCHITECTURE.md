# Steam Recommender - Modular Architecture

## Overview

This Steam game recommendation system has been refactored into a modular, maintainable architecture following clean code principles and separation of concerns.

## Project Structure

```
Steam_Recommender/
├── src/
│   ├── config/          # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py  # App configuration classes
│   ├── data/            # Data access layer
│   │   ├── __init__.py
│   │   └── repositories.py  # Database repository classes
│   ├── services/        # Business logic layer
│   │   ├── __init__.py
│   │   └── game_service.py  # Game search and recommendation logic
│   ├── algorithms/      # Computational algorithms
│   │   ├── __init__.py
│   │   └── similarity.py    # Similarity calculation algorithms
│   ├── web/            # Web interface layer
│   │   ├── __init__.py
│   │   ├── app.py      # Flask application factory
│   │   └── routes.py   # Web route handlers
│   └── utils/          # Utility functions
│       ├── __init__.py
│       └── logging.py  # Logging configuration
├── main.py             # Application entry point
├── app.py              # Original application (deprecated)
├── templates/          # Jinja2 templates
├── static/             # Static web assets
└── database_builder/   # Database construction scripts
```

## Architecture Layers

### 1. Configuration Layer (`src/config/`)
- **Purpose**: Centralized configuration management
- **Components**:
  - `settings.py`: Configuration classes for database paths, Flask settings, etc.
  - Environment variable support
  - Default configuration values

### 2. Data Access Layer (`src/data/`)
- **Purpose**: Database operations and data persistence
- **Components**:
  - `repositories.py`: Repository pattern implementation
    - `RecommendationsRepository`: Game data and hierarchy operations
    - `SteamApiRepository`: Steam API data operations
  - Abstract base repository with connection management
  - Proper error handling and resource cleanup

### 3. Service Layer (`src/services/`)
- **Purpose**: Business logic and orchestration
- **Components**:
  - `game_service.py`: Core business logic
    - Game search functionality
    - Recommendation generation
    - Data enhancement and validation
  - Dependency injection pattern
  - Clean separation from web layer

### 4. Algorithm Layer (`src/algorithms/`)
- **Purpose**: Computational algorithms and calculations
- **Components**:
  - `similarity.py`: Similarity calculation implementations
    - `VectorSimilarityCalculator`: Vector-based similarity
    - `TagBasedSimilarityCalculator`: Tag-based Jaccard similarity
    - `PreferenceCalculator`: User preference scoring
    - `HybridSimilarityCalculator`: Combined approach

### 5. Web Layer (`src/web/`)
- **Purpose**: HTTP interface and request handling
- **Components**:
  - `app.py`: Flask application factory pattern
  - `routes.py`: Route handlers with dependency injection
  - Clean separation of concerns
  - Proper error handling and logging

### 6. Utility Layer (`src/utils/`)
- **Purpose**: Cross-cutting concerns and utilities
- **Components**:
  - `logging.py`: Centralized logging configuration

## Key Improvements

### 1. **Separation of Concerns**
- Database logic separated from business logic
- Business logic separated from web layer
- Algorithms isolated in dedicated modules

### 2. **Dependency Injection**
- Repositories injected into services
- Services injected into web routes
- Easy testing and mocking

### 3. **Configuration Management**
- Centralized configuration
- Environment variable support
- Easy deployment configuration

### 4. **Error Handling**
- Consistent error handling patterns
- Proper logging throughout
- Graceful degradation

### 5. **Testability**
- Clear interfaces between layers
- Repository pattern enables easy mocking
- Service layer can be tested independently

### 6. **Maintainability**
- Single responsibility principle
- Clear module boundaries
- Easy to extend and modify

## Usage

### Running the Application

```bash
# Run with default configuration
python main.py

# Run with environment variables
FLASK_DEBUG=true RECOMMENDATIONS_DB=/path/to/db python main.py
```

### Configuration

Environment variables:
- `STEAM_API_DB`: Path to Steam API database
- `RECOMMENDATIONS_DB`: Path to recommendations database  
- `VECTORIZER_PATH`: Path to TF-IDF vectorizer file
- `FLASK_SECRET_KEY`: Flask secret key
- `FLASK_DEBUG`: Enable debug mode

### Extending the System

1. **Add new similarity algorithms**: Extend `SimilarityCalculator` in `algorithms/similarity.py`
2. **Add new data sources**: Create new repository in `data/repositories.py`
3. **Add new business logic**: Extend `GameService` in `services/game_service.py`
4. **Add new web endpoints**: Add routes to `web/routes.py`

## Migration Notes

The original `app.py` has been completely refactored into the modular structure. The functionality remains the same, but the code is now:

- More maintainable and testable
- Better organized with clear responsibilities
- Easier to extend with new features
- More robust with proper error handling
- Production-ready with proper configuration management

## Dependencies

The modular architecture maintains the same dependencies as the original:
- Flask (web framework)
- SQLite3 (database)
- NumPy (numerical operations)
- scikit-learn (similarity calculations)
- Pickle (serialization)