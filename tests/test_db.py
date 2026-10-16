"""Testes da camada de banco de dados SQLite."""

import sqlite3

import pytest

from inventario_ativos_ti.db import Database
from inventario_ativos_ti.models import Hardware, Software


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "inventario.db")
    yield database
    database.close()


def test_schema_cria_tabelas_assets_e_software(db):
    nomes = {
        linha[0]
        for linha in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "assets" in nomes
    assert "software" in nomes


def test_upsert_asset_insere_e_lista(db):
    h = Hardware(
        hostname="PC-001",
        os_name="Windows",
        os_version="10.0.19045",
        os_architecture="AMD64",
        cpu="Intel CPU",
        cpu_cores=4,
        ram_gb=16.0,
        disk_gb=512.0,
        serial_number="ABC123456",
    )
    asset_id = db.upsert_asset(h)
    assert isinstance(asset_id, int) and asset_id > 0

    assets = db.list_assets()
    assert len(assets) == 1
    assert assets[0]["id"] == asset_id
    assert assets[0]["hostname"] == "PC-001"
    assert assets[0]["ram_gb"] == 16.0


def test_upsert_mesmo_hostname_atualiza_em_vez_de_duplicar(db):
    h1 = Hardware(
        hostname="PC-001",
        os_name="Windows",
        os_version="10",
        os_architecture="AMD64",
        cpu="Intel CPU",
        cpu_cores=4,
        ram_gb=8.0,
        disk_gb=256.0,
        serial_number="SN1",
    )
    h2 = Hardware(
        hostname="PC-001",
        os_name="Windows",
        os_version="11",
        os_architecture="AMD64",
        cpu="Intel CPU",
        cpu_cores=8,
        ram_gb=32.0,
        disk_gb=1024.0,
        serial_number="SN1",
    )
    id1 = db.upsert_asset(h1)
    id2 = db.upsert_asset(h2)
    assert id1 == id2

    assets = db.list_assets()
    assert len(assets) == 1
    assert assets[0]["os_version"] == "11"
    assert assets[0]["ram_gb"] == 32.0


def test_get_asset_retorna_none_quando_inexistente(db):
    assert db.get_asset(999999) is None


def test_get_asset_retorna_campos(db):
    h = Hardware(
        hostname="PC-002",
        os_name="Windows",
        os_version="10",
        os_architecture="AMD64",
        cpu="AMD CPU",
        cpu_cores=6,
        ram_gb=8.0,
        disk_gb=512.0,
        serial_number="SN2",
    )
    asset_id = db.upsert_asset(h)
    asset = db.get_asset(asset_id)
    assert asset is not None
    assert asset["hostname"] == "PC-002"
    assert asset["cpu_cores"] == 6


def test_software_inserir_e_listar(db):
    asset_id = db.upsert_asset(
        Hardware(
            hostname="PC-003",
            os_name="Windows",
            os_version="10",
            os_architecture="AMD64",
            cpu="CPU",
            cpu_cores=2,
            ram_gb=4.0,
            disk_gb=128.0,
            serial_number="SN3",
        )
    )
    db.upsert_software(
        asset_id,
        [
            Software(name="App A", version="1.0", publisher="Editora A"),
            Software(name="App B", version="2.3.1"),
        ],
    )
    softwares = db.list_software(asset_id)
    assert len(softwares) == 2
    nomes = {s["name"] for s in softwares}
    assert nomes == {"App A", "App B"}


def test_upsert_software_substitui_coleta_anterior(db):
    asset_id = db.upsert_asset(
        Hardware(
            hostname="PC-004",
            os_name="Windows",
            os_version="10",
            os_architecture="AMD64",
            cpu="CPU",
            cpu_cores=2,
            ram_gb=4.0,
            disk_gb=128.0,
            serial_number="SN4",
        )
    )
    db.upsert_software(asset_id, [Software(name="App A", version="1.0")])
    db.upsert_software(asset_id, [Software(name="App B", version="2.0")])
    softwares = db.list_software(asset_id)
    assert len(softwares) == 1
    assert softwares[0]["name"] == "App B"


def test_software_de_asset_inexistente_levanta_integrity_error(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.upsert_software(999999, [Software(name="App", version="1.0")])
