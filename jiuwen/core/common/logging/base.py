__all__ = ("logger")

import logging
import sys

def create_logger():
    log_format = '%(asctime)s|%(name)s|%(levelname)s|%(threadName)s|%(message)s'
    formatter = logging.Formatter(log_format)
    level = 'DEBUG'
    common_logger = logging.getLogger('common')
    common_logger.setLevel(level)
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(logging.Formatter(log_format))
    common_logger.addHandler(stream_handler)
    return common_logger

logger = create_logger()