"""Coleta de inventário de hardware e software do sistema local.

Cada getter pode ser substituído em testes (monkeypatch) para que a
suite não dependa de WMI, registro do Windows ou subprocessos lentos.
"""

from __future__ import annotations

import ctypes
import os
import platform
import subprocess

from .models import Hardware, Inventory, Software


def get_hostname() -> str:
    """Nome do equipamento na rede."""
    return platform.node()


def get_os_info() -> tuple[str, str, str]:
    """Nome, versão e arquitetura do sistema operacional."""
    return platform.system(), platform.release(), platform.version()


def get_cpu_info() -> tuple[str, int]:
    """Modelo da CPU e número de núcleos lógicos."""
    return platform.processor(), os.cpu_count() or 1


def get_ram_gb() -> float:
    """Memória física total em gigabytes."""
    if platform.system() == "Windows":
        return _ram_gb_windows()
    return _ram_gb_unix()


def _ram_gb_windows() -> float:
    class MEMORYSTATUSEX(ctypes.Structure):  # noqa: D106 - estrutura da Win32 API
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return status.ullTotalPhys / (1024**3)
    return 0.0


def _ram_gb_unix() -> float:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                if linha.startswith("MemTotal:"):
                    kib = int(linha.split()[1])
                    return kib / (1024**2)
    except (OSError, ValueError):
        pass
    return 0.0


def get_disk_gb() -> float:
    """Espaço total do disco do sistema em gigabytes."""
    if platform.system() == "Windows":
        return _disk_gb_windows()
    return _disk_gb_unix()


def _disk_gb_windows() -> float:
    livre_para_chamador = ctypes.c_ulonglong()
    total = ctypes.c_ulonglong()
    livre_total = ctypes.c_ulonglong()
    if ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        "C:\\",
        ctypes.byref(livre_para_chamador),
        ctypes.byref(total),
        ctypes.byref(livre_total),
    ):
        return total.value / (1024**3)
    return 0.0


def _disk_gb_unix() -> float:
    try:
        estat = os.statvfs("/")
        return estat.f_blocks * estat.f_frsize / (1024**3)
    except OSError:
        return 0.0


def get_serial_number() -> str:
    """Número de série do BIOS (Windows); vazio fora do Windows ou sem dados."""

    if platform.system() != "Windows":
        return ""
    try:
        resultado = subprocess.run(
            ["wmic", "bios", "get", "serialnumber"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    linhas = [
        linha.strip()
        for linha in resultado.stdout.splitlines()
        if linha.strip()
    ]
    return linhas[-1] if linhas else ""


def collect_hardware() -> Hardware:
    """Coleta o registro de hardware do computador atual."""

    os_name, os_version, os_architecture = get_os_info()
    cpu, cpu_cores = get_cpu_info()
    return Hardware(
        hostname=get_hostname(),
        os_name=os_name,
        os_version=os_version,
        os_architecture=os_architecture,
        cpu=cpu,
        cpu_cores=cpu_cores,
        ram_gb=get_ram_gb(),
        disk_gb=get_disk_gb(),
        serial_number=get_serial_number(),
    )


def _query_registro(chave) -> dict[str, str | None]:
    """Lê os valores de exibição de uma chave de desinstalação."""

    import winreg  # só existe no Windows

    valores: dict[str, str | None] = {}
    for nome in ("DisplayName", "DisplayVersion", "Publisher", "InstallDate"):
        try:
            valor, _tipo = winreg.QueryValueEx(chave, nome)
            valores[nome] = str(valor) if valor is not None else None
        except OSError:
            valores[nome] = None
    return valores


def _read_registry_software() -> list[dict[str, str | None]]:
    """Lê as chaves de desinstalação do registro do Windows."""

    import winreg  # só existe no Windows

    if platform.system() != "Windows":
        return []

    caminhos = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
    ]
    encontrados: list[dict[str, str | None]] = []
    for hive, caminho in caminhos:
        try:
            with winreg.OpenKey(hive, caminho) as chave:
                quantidade, _, _ = winreg.QueryInfoKey(chave)
                for indice in range(quantidade):
                    try:
                        nome_subchave = winreg.EnumKey(chave, indice)
                        with winreg.OpenKey(chave, nome_subchave) as subchave:
                            encontrados.append(_query_registro(subchave))
                    except OSError:
                        continue
        except OSError:
            continue
    return encontrados


def _parse_registry_entries(
    entradas: list[dict[str, str | None]],
) -> list[dict[str, str | None]]:
    """Normaliza entradas do registro; ignora as que não têm nome de exibição."""

    resultado: list[dict[str, str | None]] = []
    for entrada in entradas:
        nome = entrada.get("DisplayName")
        if not nome:
            continue
        resultado.append(
            {
                "name": str(nome),
                "version": entrada.get("DisplayVersion") or None,
                "publisher": entrada.get("Publisher") or None,
                "install_date": entrada.get("InstallDate") or None,
            }
        )
    return resultado


def collect_software() -> list[Software]:
    """Lista softwares instalados (registro do Windows; vazio em outros SO)."""

    if platform.system() != "Windows":
        return []
    entradas = _read_registry_software()
    return [
        Software(
            name=dados["name"],
            version=dados["version"],
            publisher=dados["publisher"],
            install_date=dados["install_date"],
        )
        for dados in _parse_registry_entries(entradas)
    ]


def collect_inventory() -> Inventory:
    """Executa coleta completa: hardware + software do computador local."""

    return Inventory(hardware=collect_hardware(), software=collect_software())
