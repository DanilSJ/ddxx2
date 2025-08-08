import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from .config import BASE_DIR


LOGS_DIR: Path = BASE_DIR.parent / "logs"


def _ensure_logs_dir_exists() -> None:
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        # If logs directory can't be created, fallback to no-op; avoid crashing app startup
        pass


_LOGGING_ENABLED_CACHE: bool | None = None


def set_logging_enabled(enabled: bool) -> None:
    global _LOGGING_ENABLED_CACHE
    _LOGGING_ENABLED_CACHE = bool(enabled)


def apply_logging_configuration(enabled: bool) -> None:
    """Apply logging on/off to all existing component loggers at runtime."""
    set_logging_enabled(enabled)

    # Iterate over all known loggers and reconfigure ours
    for logger_name, logger_obj in logging.root.manager.loggerDict.items():
        # loggerDict may contain PlaceHolder objects; get real logger via getLogger
        if not isinstance(logger_name, str) or not logger_name.startswith("rovmarket_bot."):
            continue

        logger = logging.getLogger(logger_name)

        # Remove existing handlers and close them to release file locks
        for handler in list(logger.handlers):
            try:
                handler.close()
            except Exception:
                pass
            logger.removeHandler(handler)

        logger.setLevel(logging.INFO)
        logger.propagate = False

        if enabled:
            _ensure_logs_dir_exists()
            component = logger_name.split(".", 1)[1] if "." in logger_name else logger_name
            log_file = LOGS_DIR / f"{component}.log"
            file_handler = TimedRotatingFileHandler(
                filename=str(log_file), when="midnight", backupCount=7, encoding="utf-8"
            )
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        else:
            logger.addHandler(logging.NullHandler())


def _get_logging_enabled() -> bool:
    global _LOGGING_ENABLED_CACHE
    if _LOGGING_ENABLED_CACHE is not None:
        return _LOGGING_ENABLED_CACHE

    # If not initialized yet from DB, default to True (model default)
    return True


def get_component_logger(component_name: str) -> logging.Logger:
    """Return a configured logger for a given component.

    - Writes into logs/<component_name>.log if logging is enabled
    - Uses daily rotation, keeps 7 backups
    - Non-propagating to avoid duplicate logs
    """
    logger_name = f"rovmarket_bot.{component_name}"
    logger = logging.getLogger(logger_name)

    if getattr(logger, "_is_configured", False):
        return logger

    logger.setLevel(logging.INFO)

    if _get_logging_enabled():
        _ensure_logs_dir_exists()
        log_file = LOGS_DIR / f"{component_name}.log"
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file), when="midnight", backupCount=7, encoding="utf-8"
        )
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        logger.addHandler(logging.NullHandler())

    logger.propagate = False
    setattr(logger, "_is_configured", True)
    return logger


