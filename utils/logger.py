import logging

import colorlog


def get_logger(log_file_path, logger_name='myLogger'):
    """Log plain text to file and to terminal with colors"""

    logger = logging.getLogger('playground')

    # Log to file (but not to terminal)
    logfile_handler = logging.FileHandler(log_file_path)
    plain_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s')
    logfile_handler.setFormatter(plain_formatter)
    logfile_handler.setLevel(logging.DEBUG)

    # Logging info level to stdout with colors

    terminal_handler = colorlog.StreamHandler()
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(asctime)s %(blue)s%(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )
    terminal_handler.setLevel(logging.DEBUG)
    terminal_handler.setFormatter(color_formatter)

    # Add handlers to logger
    logger.addHandler(logfile_handler)
    logger.addHandler(terminal_handler)
    logger.setLevel(logging.DEBUG)

    return logger
