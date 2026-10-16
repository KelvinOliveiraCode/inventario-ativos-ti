"""Interface de linha de comando do inventário de ativos de TI."""

from __future__ import annotations

import argparse
import json
import sys

from dataclasses import asdict

from .collector import collect_inventory
from .server import run


def cmd_coletar(args: argparse.Namespace) -> int:
    inventario = collect_inventory()
    payload = {
        "hardware": asdict(inventario.hardware),
        "software": [asdict(item) for item in inventario.software],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_servidor(args: argparse.Namespace) -> int:
    run(host=args.host, port=args.port, db_path=args.db)
    return 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inventario-ti",
        description="Inventário de ativos de TI: coleta HW/SW e servidor com dashboard.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    coletar = sub.add_parser("coletar", help="Coleta inventário do computador local e imprime JSON.")
    coletar.set_defaults(func=cmd_coletar)

    servidor = sub.add_parser("servidor", help="Inicia o servidor HTTP com dashboard (bloqueante).")
    servidor.add_argument("--host", default="127.0.0.1", help="Host do servidor (padrão: 127.0.0.1).")
    servidor.add_argument("--port", type=int, default=8765, help="Porta do servidor (padrão: 8765).")
    servidor.add_argument("--db", default="inventario.db", help="Caminho do banco SQLite (padrão: inventario.db).")
    servidor.set_defaults(func=cmd_servidor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = montar_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
