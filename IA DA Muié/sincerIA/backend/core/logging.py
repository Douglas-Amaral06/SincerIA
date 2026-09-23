"""Configuração de logs sem dados de requisição ou segredos."""

import logging
import os


def configure_logging() -> None:
    """Inicializa o logger da aplicação uma única vez."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


configure_logging()
