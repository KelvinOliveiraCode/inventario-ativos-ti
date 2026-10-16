"""Testes do coletor de inventário (determinísticos, sem dependência de WMI)."""

from inventario_ativos_ti import collector


def test_collect_hardware_compoe_campos_dos_getters(monkeypatch):
    monkeypatch.setattr(collector, "get_hostname", lambda: "PC-TEST")
    monkeypatch.setattr(
        collector, "get_os_info", lambda: ("Windows", "10.0.19045", "AMD64")
    )
    monkeypatch.setattr(collector, "get_cpu_info", lambda: ("Intel CPU", 8))
    monkeypatch.setattr(collector, "get_ram_gb", lambda: 32.0)
    monkeypatch.setattr(collector, "get_disk_gb", lambda: 1024.0)
    monkeypatch.setattr(collector, "get_serial_number", lambda: "SN-TEST")

    h = collector.collect_hardware()

    assert h.hostname == "PC-TEST"
    assert h.os_name == "Windows"
    assert h.os_version == "10.0.19045"
    assert h.os_architecture == "AMD64"
    assert h.cpu == "Intel CPU"
    assert h.cpu_cores == 8
    assert h.ram_gb == 32.0
    assert h.disk_gb == 1024.0
    assert h.serial_number == "SN-TEST"


def test_collect_software_retorna_vazio_fora_do_windows(monkeypatch):
    monkeypatch.setattr(collector.platform, "system", lambda: "Linux")
    assert collector.collect_software() == []


def test_parse_registro_ignora_entradas_sem_display_name():
    entradas = [
        {
            "DisplayName": "App A",
            "DisplayVersion": "1.0",
            "Publisher": "X",
            "InstallDate": "20240101",
        },
        {"DisplayVersion": "2.0"},  # sem DisplayName -> ignorado
        {"DisplayName": "App B", "Publisher": "Y"},
        {},  # ignorado
    ]
    resultado = collector._parse_registry_entries(entradas)
    assert [item["name"] for item in resultado] == ["App A", "App B"]
    assert resultado[0] == {
        "name": "App A",
        "version": "1.0",
        "publisher": "X",
        "install_date": "20240101",
    }
    assert resultado[1] == {
        "name": "App B",
        "version": None,
        "publisher": "Y",
        "install_date": None,
    }


def test_collect_software_converte_entrada_em_dataclass(monkeypatch):
    monkeypatch.setattr(collector.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        collector,
        "_read_registry_software",
        lambda: [{"DisplayName": "App A", "DisplayVersion": "1.0"}],
    )
    softwares = collector.collect_software()
    assert len(softwares) == 1
    assert softwares[0].name == "App A"
    assert softwares[0].version == "1.0"
