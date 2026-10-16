"""Testes do modelo de dados: Hardware, Software e Inventory."""

from dataclasses import FrozenInstanceError

import pytest

from inventario_ativos_ti.models import Hardware, Software, Inventory


def _hardware() -> Hardware:
    return Hardware(
        hostname="PC-001",
        os_name="Windows",
        os_version="10.0.19045",
        os_architecture="AMD64",
        cpu="Intel(R) Core(TM) i5-8365U",
        cpu_cores=4,
        ram_gb=16.0,
        disk_gb=512.0,
        serial_number="ABC123456",
    )


def test_hardware_atributos_e_tipos() -> None:
    h = _hardware()
    assert h.hostname == "PC-001"
    assert h.os_name == "Windows"
    assert h.os_version == "10.0.19045"
    assert h.os_architecture == "AMD64"
    assert h.cpu == "Intel(R) Core(TM) i5-8365U"
    assert h.cpu_cores == 4
    assert isinstance(h.ram_gb, float)
    assert h.ram_gb == 16.0
    assert isinstance(h.disk_gb, float)
    assert h.disk_gb == 512.0
    assert h.serial_number == "ABC123456"
    assert isinstance(h.collected_at, str)


def test_hardware_nao_aceita_mutacao() -> None:
    h = _hardware()
    with pytest.raises(FrozenInstanceError):
        h.hostname = "outro"


def test_software_valores_padrao() -> None:
    s = Software(name="7-Zip", version="24.09")
    assert s.name == "7-Zip"
    assert s.version == "24.09"
    assert s.publisher == ""
    assert s.install_date is None


def test_software_com_todos_campos() -> None:
    s = Software(
        name="Google Chrome",
        version="120.0.0.0",
        publisher="Google LLC",
        install_date="2024-01-15",
    )
    assert s.publisher == "Google LLC"
    assert s.install_date == "2024-01-15"


def test_inventory_agrupa_hardware_e_software() -> None:
    h = _hardware()
    s = Software(name="App", version="1.0")
    inv = Inventory(hardware=h, software=[s])
    assert inv.hardware is h
    assert inv.software == [s]
    assert inv.software[0].name == "App"
