import logging

from parkpass.settings import BASE_LOGGER_NAME


def get_logger(name=BASE_LOGGER_NAME):
    return logging.getLogger(name)
