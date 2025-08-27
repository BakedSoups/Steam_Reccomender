import logging
import sys
from typing import Optional


def configure_logging(level: str = 'INFO', 
                     format_string: Optional[str] = None) -> None:
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)