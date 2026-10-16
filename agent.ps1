# =============================================================================
# Agente Windows do Inventário de Ativos de TI
# Coleta hardware e software do computador local e envia para o servidor.
# Uso: .\agent.ps1 [-ServerUrl URL] [-IntervaloSegundos N] [-UmaVez]
# =============================================================================

param(
    [string]$ServerUrl = "http://127.0.0.1:8765",
    [int]$IntervaloSegundos = 300,
    [switch]$UmaVez
)

function Obter-Hardware {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $ramGB = [math]::Round(
        ((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB), 2)
    $discoGB = [math]::Round(
        ((Get-CimInstance Win32_LogicalDisk | Where-Object {$_.DriveType -eq 3} | Measure-Object Size -Sum).Size / 1GB), 2)
    $bios = Get-CimInstance Win32_BIOS | Select-Object -First 1

    [pscustomobject]@{
        Hostname         = $env:COMPUTERNAME
        OsName           = $os.Caption
        OsVersion        = $os.Version
        OsArchitecture   = $os.OSArchitecture
        Cpu              = $cpu.Name
        CpuCores         = [int]$cpu.NumberOfCores
        RamGb            = $ramGB
        DiskGb           = $discoGB
        SerialNumber     = [string]$bios.SerialNumber
        CollectedAt      = (Get-Date -Format "o")
    }
}

function Obter-Software {
    $caminhos = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    )
    $itens = @()
    foreach ($caminho in $caminhos) {
        if (-not (Test-Path $caminho)) { continue }
        Get-ChildItem $caminho | ForEach-Object {
            try {
                $prop = Get-ItemProperty $_.PSPath
                if (-not $prop.DisplayName) { return }
                $itens += [pscustomobject]@{
                    Name        = $prop.DisplayName
                    Version     = [string]$prop.DisplayVersion
                    Publisher   = [string]$prop.Publisher
                    InstallDate = [string]$prop.InstallDate
                }
            } catch {
                # ignora chaves do registro inacessíveis
            }
        }
    }
    $itens
}

function Enviar-Inventario {
    param(
        [pscustomobject]$Hardware,
        [array]$Software
    )
    $corpo = @{ hardware = $Hardware; software = $Software } | ConvertTo-Json -Depth 3
    try {
        $resposta = Invoke-RestMethod -Uri "$ServerUrl/api/inventory" -Method Post `
            -Body $corpo -ContentType "application/json" -TimeoutSec 15
        Write-Host ("Inventário enviado ({0}) - id={1}" -f $Hardware.Hostname, $resposta.id)
    } catch {
        Write-Warning ("Falha ao enviar inventário: {0}" -f $_.Exception.Message)
    }
}

$hardware = Obter-Hardware
$software = Obter-Software
Enviar-Inventario -Hardware $hardware -Software $software

if (-not $UmaVez) {
    while ($true) {
        Start-Sleep -Seconds $IntervaloSegundos
        $hardware = Obter-Hardware
        $software = Obter-Software
        Enviar-Inventario -Hardware $hardware -Software $software
    }
}
