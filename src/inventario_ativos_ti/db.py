"""Camada de banco de dados SQLite do inventário de ativos."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import Hardware, Inventory, Software

_COLUNAS_ASSET = (
    "id, hostname, os_name, os_version, os_architecture, cpu, cpu_cores, "
    "ram_gb, disk_gb, serial_number, collected_at, updated_at"
)

_COLUNAS_SOFTWARE = (
    "id, asset_id, name, version, publisher, install_date, collected_at"
)


class Database:
    """Banco SQLite que armazena ativos e seus softwares instalados."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.init_schema()

    def init_schema(self) -> None:
        with self._lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname TEXT NOT NULL UNIQUE,
                    os_name TEXT NOT NULL,
                    os_version TEXT NOT NULL,
                    os_architecture TEXT NOT NULL,
                    cpu TEXT NOT NULL,
                    cpu_cores INTEGER NOT NULL,
                    ram_gb REAL NOT NULL,
                    disk_gb REAL NOT NULL,
                    serial_number TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS software (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    version TEXT,
                    publisher TEXT,
                    install_date TEXT,
                    collected_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_software_asset
                    ON software(asset_id);
                """
            )
            self.conn.commit()

    def upsert_asset(self, hardware: Hardware) -> int:
        """Insere ou atualiza o ativo identificado pelo hostname. Retorna o id."""

        agora = hardware.collected_at
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO assets (
                    hostname, os_name, os_version, os_architecture, cpu,
                    cpu_cores, ram_gb, disk_gb, serial_number,
                    collected_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hostname) DO UPDATE SET
                    os_name = excluded.os_name,
                    os_version = excluded.os_version,
                    os_architecture = excluded.os_architecture,
                    cpu = excluded.cpu,
                    cpu_cores = excluded.cpu_cores,
                    ram_gb = excluded.ram_gb,
                    disk_gb = excluded.disk_gb,
                    serial_number = excluded.serial_number,
                    collected_at = excluded.collected_at,
                    updated_at = excluded.updated_at
                """,
                (
                    hardware.hostname,
                    hardware.os_name,
                    hardware.os_version,
                    hardware.os_architecture,
                    hardware.cpu,
                    hardware.cpu_cores,
                    hardware.ram_gb,
                    hardware.disk_gb,
                    hardware.serial_number,
                    agora,
                    agora,
                ),
            )
            self.conn.commit()
            linha = self.conn.execute(
                "SELECT id FROM assets WHERE hostname = ?", (hardware.hostname,)
            ).fetchone()
            return int(linha[0])

    def upsert_software(
        self, asset_id: int, softwares: Iterable[Software]
    ) -> None:
        """Substitui a lista de softwares do ativo por uma coleta completa."""

        agora = datetime.now(timezone.utc).isoformat()
        linhas = [
            (
                asset_id,
                s.name,
                s.version or None,
                s.publisher or None,
                s.install_date,
                agora,
            )
            for s in softwares
        ]
        with self._lock:
            self.conn.execute(
                "DELETE FROM software WHERE asset_id = ?", (asset_id,)
            )
            self.conn.executemany(
                """
                INSERT INTO software (
                    asset_id, name, version, publisher, install_date, collected_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                linhas,
            )
            self.conn.commit()

    def add_inventory(self, inventory: Inventory) -> int:
        """Registra hardware e software de uma coleta completa. Retorna id do ativo."""

        asset_id = self.upsert_asset(inventory.hardware)
        self.upsert_software(asset_id, inventory.software)
        return asset_id

    def list_assets(self) -> list[dict]:
        with self._lock:
            cursor = self.conn.execute(
                f"SELECT {_COLUNAS_ASSET} FROM assets ORDER BY hostname"
            )
            colunas = [descricao[0] for descricao in cursor.description]
            return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

    def get_asset(self, asset_id: int) -> dict | None:
        with self._lock:
            cursor = self.conn.execute(
                f"SELECT {_COLUNAS_ASSET} FROM assets WHERE id = ?", (asset_id,)
            )
            linha = cursor.fetchone()
            if linha is None:
                return None
            colunas = [descricao[0] for descricao in cursor.description]
            return dict(zip(colunas, linha))

    def list_software(self, asset_id: int) -> list[dict]:
        with self._lock:
            cursor = self.conn.execute(
                f"SELECT {_COLUNAS_SOFTWARE} FROM software WHERE asset_id = ? ORDER BY name",
                (asset_id,),
            )
            colunas = [descricao[0] for descricao in cursor.description]
            return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

    def close(self) -> None:
        with self._lock:
            self.conn.close()
