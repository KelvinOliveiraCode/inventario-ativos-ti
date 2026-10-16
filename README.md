# Inventário de Ativos de TI / IT Asset Inventory

## Sobre o projeto

Um agente Windows coleta hardware e software do computador local, envia os
dados para um servidor SQLite e um dashboard simples exibe a lista de ativos
coletados. Foi feito para suporte de TI que precisa de um inventário leve, sem
depender de agentes pesados ou de banco de dados externo.

Stack: Python 3.10+ (somente biblioteca padrão), PowerShell 5.1+ e SQLite.

## Estrutura do projeto

```
inventario-ativos-ti/
├── agent.ps1                 # Agente Windows: coleta HW/SW e envia ao servidor
├── BRIEF.md                  # Este resumo de entregas e como verificar
├── README.md                 # Este arquivo (PT-BR + EN)
├── pyproject.toml            # Metadados e ponto de entrada da CLI
├── src/inventario_ativos_ti/
│   ├── __init__.py           # Pacote e versao
│   ├── __main__.py           # CLI: coletar | servidor
│   ├── collector.py          # Coleta de hardware e software (WMI/registro Windows)
│   ├── db.py                 # Camada SQLite: upsert de ativos e softwares
│   ├── models.py             # Dataclasses Hardware, Software e Inventory
│   └── server.py             # Servidor HTTP: API REST + dashboard HTML/JS
└── tests/
    ├── test_collector.py
    ├── test_db.py
    ├── test_models.py
    └── test_server.py
```

## Como usar

### 1. Inicie o servidor

```powershell
$env:PYTHONPATH="src"
python -m inventario_ativos_ti servidor
```

Ou instale o projeto e use o ponto de entrada:

```powershell
pip install -e .
inventario-ti servidor --port 8765
```

O servidor escuta em `http://127.0.0.1:8765`. Abra esse endereço no navegador
para ver o dashboard. Endpoints da API:

- `GET /health` — status do servidor
- `GET /api/assets` — lista de ativos
- `GET /api/assets/{id}` — detalhe de um ativo
- `GET /api/assets/{id}/software` — softwares de um ativo
- `POST /api/inventory` — recebe o JSON de hardware e software do agente

### 2. Rode o agente Windows

No computador a ser inventariado:

```powershell
.\agent.ps1 -UmaVez
```

Envia uma única coleta e encerra. Sem o parâmetro, o agente repete a coleta a
cada 300 segundos enquanto estiver rodando. Aponte para outro servidor com:

```powershell
.\agent.ps1 -ServerUrl http://servidor:8765 -UmaVez
```

### 3. Coleta local (sem servidor)

```powershell
$env:PYTHONPATH="src"
python -m inventario_ativos_ti coletar
```

Imprime o JSON do inventário do computador atual (útil para depuração).

## Testes

```powershell
python -m pytest -q
```

Resultado esperado: todos os testes passam (25 testes, sem dependência de WMI
ou do registro — os getters são substituídos por monkeypatch). O banco de
dados dos testes usa um arquivo temporário em `tmp_path`.

## Licença

MIT License.

## Autor

Kelvin Oliveira

---

# IT Asset Inventory

## About the project

A Windows agent collects hardware and software from the local computer, sends
the data to a SQLite server, and a simple dashboard displays the collected
assets. Built for IT support teams that need a lightweight inventory without
heavy agents or an external database.

Stack: Python 3.10+ (standard library only), PowerShell 5.1+, SQLite.

## Project structure

Same as above (see the tree in the Portuguese section).

## How to use

### 1. Start the server

```powershell
$env:PYTHONPATH="src"
python -m inventario_ativos_ti servidor
```

Or install the project and use the entry point:

```powershell
pip install -e .
inventario-ti servidor --port 8765
```

The server listens on `http://127.0.0.1:8765`. Open that address in a browser
to see the dashboard. API endpoints:

- `GET /health` — server status
- `GET /api/assets` — asset list
- `GET /api/assets/{id}` — asset detail
- `GET /api/assets/{id}/software` — software of an asset
- `POST /api/inventory` — receives the agent's hardware/software JSON

### 2. Run the Windows agent

On the computer to inventory:

```powershell
.\agent.ps1 -UmaVez
```

Sends a single collection and exits. Without the flag, the agent repeats the
collection every 300 seconds while running. Point to another server with:

```powershell
.\agent.ps1 -ServerUrl http://servidor:8765 -UmaVez
```

### 3. Local collection (no server)

```powershell
$env:PYTHONPATH="src"
python -m inventario_ativos_ti coletar
```

Prints the current computer's inventory as JSON (useful for debugging).

## Tests

```powershell
python -m pytest -q
```

Expected result: all tests pass (25 tests, no dependency on WMI or the
registry — getters are replaced via monkeypatch). Tests use a temporary
database file under `tmp_path`.

## License

MIT License.

## Author

Kelvin Oliveira
