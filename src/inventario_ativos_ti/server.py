"""Servidor HTTP com API REST e dashboard do inventário de ativos."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .db import Database
from .models import Hardware, Inventory, Software

CAMPOS_OBRIGATORIOS = (
    "hostname",
    "os_name",
    "os_version",
    "os_architecture",
    "cpu",
    "cpu_cores",
    "ram_gb",
    "disk_gb",
    "serial_number",
)

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inventário de Ativos de TI</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         margin: 0; padding: 1rem; background: #f3f4f6; color: #111827; }
  header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; }
  h1 { font-size: 1.25rem; margin: 0; letter-spacing: -0.01em; }
  .btn { background: #111827; color: #fff; border: none; padding: 0.45rem 0.9rem;
         border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
  .btn:hover { background: #374151; }
  table { width: 100%; border-collapse: collapse; background: #fff;
          border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
  th, td { text-align: left; padding: 0.6rem 0.8rem; border-bottom: 1px solid #e5e7eb; }
  th { background: #f9fafb; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #374151; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f9fafb; }
  .mono { font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
          font-size: 0.85rem; }
  .badge { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px;
           background: #e5e7eb; color: #374151; font-size: 0.75rem; }
  .muted { color: #6b7280; font-size: 0.85rem; }
  .empty { padding: 2rem; text-align: center; color: #6b7280; }
</style>
</head>
<body>
<header>
  <h1>Inventário de Ativos de TI</h1>
  <button class="btn" onclick="carregar()">Atualizar</button>
</header>
<p class="muted">
  API REST: <code>GET /api/assets</code> · <code>GET /api/assets/{id}</code> ·
  <code>GET /api/assets/{id}/software</code> ·
  <code>POST /api/inventory</code> · <code>GET /health</code>
</p>
<table>
  <thead>
    <tr>
      <th>Hostname</th>
      <th>Sistema</th>
      <th>CPU / Cores</th>
      <th>RAM (GB)</th>
      <th>Disco (GB)</th>
      <th>Serial</th>
      <th>Softwares</th>
      <th>Coletado em</th>
    </tr>
  </thead>
  <tbody id="corpo"></tbody>
</table>
<script>
  async function carregar() {
    const corpo = document.getElementById('corpo');
    corpo.innerHTML = '';
    try {
      const resposta = await fetch('/api/assets');
      const ativos = await resposta.json();
      if (ativos.length === 0) {
        corpo.innerHTML = '<tr><td colspan="8" class="empty">Nenhum ativo coletado ainda.</td></tr>';
        return;
      }
      for (const a of ativos) {
        const tr = document.createElement('tr');
        tr.innerHTML =
          '<td class="mono">' + escapar(a.hostname) + '</td>' +
          '<td>' + escapar(a.os_name) + ' ' + escapar(a.os_version) +
          ' <span class="badge">' + escapar(a.os_architecture) + '</span></td>' +
          '<td><span class="mono">' + escapar(a.cpu) + '</span><br>' +
          '<span class="muted">' + a.cpu_cores + ' núcleos</span></td>' +
          '<td>' + a.ram_gb + '</td>' +
          '<td>' + a.disk_gb + '</td>' +
          '<td class="mono">' + escapar(a.serial_number) + '</td>' +
          '<td><a href="/api/assets/' + a.id + '/software" class="mono">' +
          'ver softwares</a></td>' +
          '<td class="muted">' + escapar(a.collected_at) + '</td>';
        corpo.appendChild(tr);
      }
    } catch (erro) {
      corpo.innerHTML = '<tr><td colspan="8" class="empty">Erro ao carregar ativos.</td></tr>';
    }
  }
  function escapar(texto) {
    return String(texto == null ? '' : texto)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  carregar();
</script>
</body>
</html>
"""


def make_app(db: Database) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "InventarioTI/0.1"

        def log_message(self, formato: str, *args: Any) -> None:
            return  # logs de acesso silenciados no console

        def do_GET(self) -> None:
            caminho = self.path.split("?", 1)[0]
            partes = [parte for parte in caminho.split("/") if parte]

            if partes == ["health"]:
                self._resposta_json(200, {"status": "ok"})
            elif partes == []:
                corpo = HTML_DASHBOARD.encode("utf-8")
                self._resposta(200, corpo, "text/html; charset=utf-8")
            elif partes == ["api", "assets"]:
                self._resposta_json(200, self.db.list_assets())
            elif len(partes) == 3 and partes[:2] == ["api", "assets"]:
                try:
                    asset_id = int(partes[2])
                except ValueError:
                    self._resposta_json(404, {"error": "not found"})
                    return
                asset = self.db.get_asset(asset_id)
                if asset is None:
                    self._resposta_json(404, {"error": "not found"})
                else:
                    self._resposta_json(200, asset)
            elif (
                len(partes) == 4
                and partes[:2] == ["api", "assets"]
                and partes[3] == "software"
            ):
                try:
                    asset_id = int(partes[2])
                except ValueError:
                    self._resposta_json(404, {"error": "not found"})
                    return
                self._resposta_json(200, self.db.list_software(asset_id))
            else:
                self._resposta_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            caminho = self.path.split("?", 1)[0]
            partes = [parte for parte in caminho.split("/") if parte]
            if partes != ["api", "inventory"]:
                self._resposta_json(404, {"error": "not found"})
                return
            self._receber_inventario()

        def _receber_inventario(self) -> None:
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
                dados = json.loads(self.rfile.read(tamanho) or b"{}")
            except (json.JSONDecodeError, ValueError):
                self._resposta_json(400, {"error": "json invalido"})
                return

            hardware = dados.get("hardware")
            if not isinstance(hardware, dict):
                self._resposta_json(400, {"error": "campo hardware obrigatorio"})
                return

            faltando = [campo for campo in CAMPOS_OBRIGATORIOS if campo not in hardware]
            if faltando:
                self._resposta_json(
                    400,
                    {"error": "campos obrigatorios faltando", "faltando": faltando},
                )
                return

            ativo = Hardware(
                hostname=str(hardware["hostname"]),
                os_name=str(hardware["os_name"]),
                os_version=str(hardware["os_version"]),
                os_architecture=str(hardware["os_architecture"]),
                cpu=str(hardware["cpu"]),
                cpu_cores=int(hardware["cpu_cores"]),
                ram_gb=float(hardware["ram_gb"]),
                disk_gb=float(hardware["disk_gb"]),
                serial_number=str(hardware["serial_number"]),
                collected_at=str(
                    hardware.get("collected_at")
                    or datetime.now(timezone.utc).isoformat()
                ),
            )

            registros: list[Software] = []
            softwares = dados.get("software", [])
            if isinstance(softwares, list):
                for item in softwares:
                    if isinstance(item, dict) and item.get("name"):
                        registros.append(
                            Software(
                                name=str(item["name"]),
                                version=str(item.get("version") or ""),
                                publisher=str(item.get("publisher") or ""),
                                install_date=str(item["install_date"])
                                if item.get("install_date")
                                else None,
                            )
                        )

            asset_id = self.db.add_inventory(Inventory(hardware=ativo, software=registros))
            self._resposta_json(201, {"id": asset_id, "hostname": ativo.hostname})

        def _resposta(self, status: int, corpo: bytes, tipo_conteudo: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", tipo_conteudo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _resposta_json(self, status: int, payload: Any) -> None:
            corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._resposta(status, corpo, "application/json; charset=utf-8")

    Handler.db = db
    return Handler


def run(
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: str | Path = "inventario.db",
) -> None:
    """Inicia o servidor HTTP do dashboard (bloqueante)."""

    db = Database(db_path)
    handler = make_app(db)
    servidor = ThreadingHTTPServer((host, port), handler)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        db.close()
