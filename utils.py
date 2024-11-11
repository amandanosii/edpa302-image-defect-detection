import logging
from logging.handlers import RotatingFileHandler


# Configure logging
def setup_logging():
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = 'quality_control.log'

    # Create handlers
    file_handler = RotatingFileHandler(log_file,
                                       maxBytes=5 * 1024 * 1024,
                                       backupCount=5)
    file_handler.setFormatter(log_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    # Create logger
    logger = logging.getLogger('QualityControl')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


LOGGER = setup_logging()
TITLE = "Automatic Quality Control System"
