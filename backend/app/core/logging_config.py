"""
Logging persistente del ERP.

Además de la consola, todo lo que pase por logging estándar (uvicorn, errores
no capturados) y por structlog queda en `backend/logs/erp.log` con rotación
(5 MB × 5 archivos). Sin esto, un fallo nocturno en el PC servidor no deja
ningún rastro revisable.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


def configurar_logging(debug: bool = False) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        LOG_DIR / "erp.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s")
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s — %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    # Idempotente: al recargar (tests, uvicorn --reload) no duplicar handlers
    root.handlers = [file_handler, console_handler]

    # structlog enruta por logging estándar → consola Y archivo rotado
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.stdlib.render_to_log_kwargs,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(0),
        cache_logger_on_first_use=True,
    )
