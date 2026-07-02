from datetime import datetime
from app.core.time import utcnow
from sqlalchemy import String, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

ROLES_VALIDOS = ("Admin", "Administradora", "Auxiliar")


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "rol IN (" + ", ".join(repr(r) for r in ROLES_VALIDOS) + ")",
            name="ck_usuarios_rol",
        ),
        {'extend_existing': True},
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(50), nullable=False, default="Auxiliar")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RefreshToken(Base):
    """Refresh tokens activos, uno por sesión. Se rota (borra + recrea) en cada uso."""
    __tablename__ = "refresh_tokens"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
