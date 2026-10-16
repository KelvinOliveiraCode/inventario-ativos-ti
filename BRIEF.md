# BRIEF — inventario-ativos-ti

**Projeto:** inventario-ativos-ti
**Área:** Suporte TI
**Objetivo:** inventário de ativos de TI — agente Windows coleta HW/SW, servidor
SQLite armazena, dashboard simples exibe os ativos.
**Dono da validação (workflow manager):** quem solicitou este build.
**Output:** todos os arquivos em
`C:\Users\Kelvin\AppData\Local\Temp\opencode\github-staging\projects\inventario-ativos-ti\`

## Entregas

| Arquivo | Conteúdo |
|---|---|
| `README.md` | Documentação completa bilíngue PT-BR + EN (sobre, estrutura, como usar, testes, licença MIT, autor Kelvin Oliveira) |
| `BRIEF.md` | Este resumo: entregas e como verificar |
| `pyproject.toml` | Metadados do projeto e ponto de entrada `inventario-ti` |
| `src/inventario_ativos_ti/__init__.py` | Pacote e versão |
| `src/inventario_ativos_ti/__main__.py` | CLI: `coletar` (imprime JSON) e `servidor` (HTTP + dashboard) |
| `src/inventario_ativos_ti/collector.py` | Coleta de hardware (WMI/ctypes) e software (registro do Windows) |
| `src/inventario_ativos_ti/db.py` | Camada SQLite: upsert de ativos por hostname e substituição de softwares |
| `src/inventario_ativos_ti/models.py` | Dataclasses `Hardware`, `Software`, `Inventory` (imutáveis, tipadas) |
| `src/inventario_ativos_ti/server.py` | Servidor HTTP: API REST (`/health`, `/api/assets`, `POST /api/inventory`, etc.) + dashboard HTML/JS |
| `agent.ps1` | Agente Windows: coleta via CIM/WMI + registro e POST para `/api/inventory` (execução única ou loop a cada 300 s) |
| `tests/test_models.py` | Testes dos modelos de dados |
| `tests/test_db.py` | Testes do banco SQLite (schema, upsert, cascata, integridade) |
| `tests/test_collector.py` | Testes do coletor (determinísticos, sem WMI/registro) |
| `tests/test_server.py` | Testes do servidor e dashboard (HTTP real em porta efêmera) |

## Como verificar

1. Entre na pasta do projeto.
2. Rode a suíte de testes:

```powershell
python -m pytest -q
```

**Resultado esperado:** `25 passed` (todos os testes passam).

3. Confirme o inventário populado:

```powershell
$env:PYTHONPATH="src"
python -m inventario_ativos_ti coletar
```

Deve imprimir JSON com hardware (hostname, OS, CPU, RAM, disco, serial) e
software do computador.

4. Confirme o servidor/dashboard:

```powershell
python -m inventario_ativos_ti servidor
```

Acesse `http://127.0.0.1:8765` no navegador; `GET /api/assets` deve listar os
ativos cadastrados via `POST /api/inventory`.

## Critérios de aceitação (espec)

- [x] Inventário populado corretamente: agente coleta HW/SW e servidor grava no SQLite (upsert por hostname, softwares substituídos a cada coleta).
- [x] Testes que passam: suíte pytest com 25 testes passando.
- [x] README completo em PT-BR e EN, com licença MIT e autor Kelvin Oliveira.

## Stack

Python 3.10+ (biblioteca padrão apenas), PowerShell 5.1+, SQLite.
