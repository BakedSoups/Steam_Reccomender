#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.web.app import create_app
from src.config.settings import AppConfig


def main():
    config = AppConfig.from_env()
    app = create_app(config)
    
    print("Starting Flask app with SQLite hierarchical search...")
    app.run(
        debug=config.flask.debug,
        host=config.flask.host,
        port=config.flask.port
    )


if __name__ == '__main__':
    main()