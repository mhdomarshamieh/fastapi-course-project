import logging
from logging.config import dictConfig

from social_media_app.config import DevConfig, config


def obsufcated(email: str, obfuscated_length: int) -> str:
    characters = email[:obfuscated_length]
    first, last = email.split("@")
    return characters + ("*" * (len(first) - obfuscated_length)) + "@" + last


class EmailObfuscationFilter(logging.Filter):
    def __init__(self, name: str = "", obfuscated_length: int = 2):
        super().__init__(name)
        self.obfuscated_length = obfuscated_length

    def filter(self, record: logging.LogRecord) -> bool:
        if "email" in record.__dict__:
            record.email = obsufcated(record.email, self.obfuscated_length)
        return True


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                # Filter: Adds a unique ID to every log message
                "correlation_id": {
                    "()": "asgi_correlation_id.CorrelationIdFilter",
                    "uuid_length": 8 if isinstance(config, DevConfig) else 32,
                    "default_value": "-",
                },
                # Filter: Hides sensitive email addresses
                "email_obfuscation": {
                    "()": EmailObfuscationFilter,
                    "obfuscated_length": 2 if isinstance(config, DevConfig) else 0,
                },
            },
            "formatters": {
                # Formatter: Simple text format for the console
                "console": {
                    "class": "logging.Formatter",
                    "format": " %(correlation_id)s %(name)s:%(lineno)d - %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                },
                # Formatter: JSON format for the log file (machine readable)
                "file": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                    "format": "%(asctime)s %(msecs)03d  %(correlation_id)s %(levelname)-8s  %(name)s %(lineno)d  %(message)s",
                },
            },
            "handlers": {
                # Handler: Prints logs to the terminal (Console)
                "default": {
                    "class": "rich.logging.RichHandler",
                    "formatter": "console",
                    "level": "DEBUG",
                    "filters": ["correlation_id", "email_obfuscation"],
                },
                # Handler: Writes logs to a file (social_media_app.log)
                "rotating_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "file",
                    "filename": "social_media_app.log",
                    "maxBytes": 1024 * 1024,  # 1 MB
                    "backupCount": 5,
                    "encoding": "utf8",
                    "level": "DEBUG",
                    "filters": ["correlation_id"],
                },
            },
            "loggers": {
                # Logger: Captures logs from the Uvicorn server
                "uvicorn": {"handlers": ["default", "rotating_file"], "level": "INFO"},
                "databases": {"handlers": ["default"], "level": "WARNING"},
                # Logger: Captures logs from our application code
                "social_media_app": {
                    "handlers": ["default", "rotating_file"],
                    "level": "DEBUG" if isinstance(config, DevConfig) else "INFO",
                    "propagate": False,
                },
                "aiosqlite": {"handlers": ["default"], "level": "WARNING"},
            },
        }
    )
