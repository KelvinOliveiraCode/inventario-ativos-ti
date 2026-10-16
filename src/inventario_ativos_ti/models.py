"""Modelos de dados do inventário de ativos de TI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Hardware:
    """Dados de hardware de um ativo coletados do sistema local."""

    hostname: str
    os_name: str
    os_version: str
    os_architecture: str
    cpu: str
    cpu_cores: int
    ram_gb: float
    disk_gb: float
    serial_number: str
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class Software:
    """Registro de um software instalado no ativo."""

    name: str
    version: str = ""
    publisher: str = ""
    install_date: str | None = None


@dataclass(frozen=True)
class Inventory:
    """Resultado de uma coleta completa de inventário de um ativo."""

    hardware: Hardware
    software: list[Software]
