"""Rate limiting compartido (login y futuros endpoints sensibles)."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# config_filename evita que slowapi autodetecte y lea ".env": en Windows lo abre
# con el codec por defecto (cp1252), no UTF-8, y crashea con nuestro .env real.
limiter = Limiter(key_func=get_remote_address, config_filename="slowapi_unused.env")
