import logging
import yaml
from typing import NoReturn
import os

def setup_logger() -> logging.Logger:
    """
    Configure and return a logger instance based on config settings
    """
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Create logger
    logger = logging.getLogger('blacklist_monitor')
    logger.setLevel(config['logging']['level'])

    # Create formatters and handlers
    formatter = logging.Formatter(config['logging']['format'])
    
    # File handler
    file_handler = logging.FileHandler(config['logging']['file'])
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
