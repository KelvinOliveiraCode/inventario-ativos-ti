"""Testes do servidor HTTP, API REST e dashboard (SQLite temporário, porta efêmera)."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from inventario_ativos_ti.db import Database
from inventario_ativos_ti.server import make_app


@pytest.fixture
def base_url(tmp_path):
    database = Database(tmp_path / "server.db")
    handler = make_app(database)
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{servidor.server_address[1]}"
    finally:
        servidor.shutdown()
        servidor.server_close()
        database.close()


def _get(caminho, base_url):
    with urllib.request.urlopen(base_url + caminho, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode() or "{}")


def _post_json(caminho, payload, base_url):
    corpo = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url + caminho,
        data=corpo,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode() or "{}")


def _hardware_payload():
    return {
        "hostname": "PC-SRV",
        "os_name": "Windows",
        "os_version": "10.0.19045",
        "os_architecture": "AMD64",
        "cpu": "Intel CPU",
        "cpu_cores": 4,
        "ram_gb": 16.0,
        "disk_gb": 512.0,
        "serial_number": "SRV123",
    }


def test_health_retorna_ok(base_url):
    status, corpo = _get("/health", base_url)
    assert status == 200
    assert corpo == {"status": "ok"}


def test_dashboard_retorna_html(base_url):
    with urllib.request.urlopen(base_url + "/", timeout=5) as resp:
        assert resp.status == 200
        assert "text/html" in resp.headers.get("Content-Type", "")


def test_post_inventory_entao_listar_assets(base_url):
    payload = {"hardware": _hardware_payload(), "software": []}
    status, corpo = _post_json("/api/inventory", payload, base_url)
    assert status == 201
    assert corpo["id"] > 0
    assert corpo["hostname"] == "PC-SRV"

    status, assets = _get("/api/assets", base_url)
    assert status == 200
    assert len(assets) == 1
    assert assets[0]["hostname"] == "PC-SRV"
    assert assets[0]["ram_gb"] == 16.0


def test_post_json_invalido_retorna_400(base_url):
    req = urllib.request.Request(
        base_url + "/api/inventory",
        data=b"invalid json",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as err:
        assert err.code == 400
    else:
        raise AssertionError("esperava HTTP 400")


def test_post_campos_obrigatorios_faltando_retorna_400(base_url):
    req = urllib.request.Request(
        base_url + "/api/inventory",
        data=json.dumps({"hardware": {"hostname": "PC"}}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as err:
        assert err.code == 400
    else:
        raise AssertionError("esperava HTTP 400")


def test_get_asset_inexistente_retorna_404(base_url):
    try:
        _get("/api/assets/999999", base_url)
    except urllib.error.HTTPError as err:
        assert err.code == 404
    else:
        raise AssertionError("esperava HTTP 404")


def test_post_software_e_listar_por_asset(base_url):
    status, corpo = _post_json(
        "/api/inventory",
        {
            "hardware": _hardware_payload(),
            "software": [
                {"name": "App A", "version": "1.0", "publisher": "X"},
                {"name": "App B", "version": "2.0"},
            ],
        },
        base_url,
    )
    assert status == 201
    asset_id = corpo["id"]

    status, softwares = _get(f"/api/assets/{asset_id}/software", base_url)
    assert status == 200
    assert len(softwares) == 2
    assert {s["name"] for s in softwares} == {"App A", "App B"}


def test_coletar_mesma_maquina_atualiza_registro(base_url):
    payload = {"hardware": _hardware_payload(), "software": []}
    _post_json("/api/inventory", payload, base_url)

    atualizado = dict(_hardware_payload())
    atualizado["ram_gb"] = 64.0
    _post_json("/api/inventory", {"hardware": atualizado, "software": []}, base_url)

    status, assets = _get("/api/assets", base_url)
    assert len(assets) == 1
    assert assets[0]["ram_gb"] == 64.0
