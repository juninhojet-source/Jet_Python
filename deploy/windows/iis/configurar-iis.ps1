<#
    Configura o IIS como proxy reverso do Sistema MCMV.

    Fluxo: navegador -> IIS (porta 80, hostname) -> Waitress (127.0.0.1:8000).

    Pre-requisitos:
      - Executar o PowerShell COMO ADMINISTRADOR.
      - O Waitress deve rodar em 127.0.0.1:8000 (ver iniciar.bat / servico NSSM;
        no .env: MCMV_HOST=127.0.0.1  MCMV_PORT=8000).
      - Apos o apontamento de DNS de mcmv.baraodecocais.mg.gov.br -> 172.16.64.9.

    Uso (exemplo):
      cd C:\mcmv\Jet_Python\deploy\windows\iis
      powershell -ExecutionPolicy Bypass -File .\configurar-iis.ps1 `
        -ProjetoDir C:\mcmv\Jet_Python

    Para baixar/instalar automaticamente os modulos URL Rewrite e ARR (requer
    internet no servidor), acrescente -BaixarModulos.
#>
param(
    [string]$Hostname   = "mcmv.baraodecocais.mg.gov.br",
    [string]$Ip         = "172.16.64.9",
    [string]$Backend    = "http://127.0.0.1:8000",
    [string]$SiteName   = "MCMV",
    [string]$SitePath   = "C:\mcmv\iis-site",
    [int]$Porta         = 80,
    [string]$ProjetoDir = "",
    [switch]$BaixarModulos
)

$ErrorActionPreference = "Stop"

function Requer-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Execute este script como Administrador."
    }
}

function Baixar-Arquivo($url, $destino) {
    [Net.ServicePointManager]::SecurityProtocol = `
        [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls11
    Invoke-WebRequest -Uri $url -OutFile $destino -UseBasicParsing
}

Requer-Admin
Write-Host "== 1/6 Instalando recursos do IIS ==" -ForegroundColor Cyan
Import-Module ServerManager -ErrorAction SilentlyContinue
Install-WindowsFeature -Name Web-Server, Web-Common-Http, Web-Static-Content, `
    Web-Default-Doc, Web-Http-Errors, Web-Http-Logging, Web-Filtering, `
    Web-Mgmt-Console -IncludeManagementTools | Out-Null

Import-Module WebAdministration

Write-Host "== 2/6 Verificando URL Rewrite e ARR ==" -ForegroundColor Cyan
$temRewrite = [bool](Get-WebGlobalModule | Where-Object { $_.Name -eq "RewriteModule" })
$arrDll = Join-Path $env:ProgramFiles "IIS\Application Request Routing\requestRouter.dll"
$temArr = Test-Path $arrDll

if ((-not $temRewrite -or -not $temArr) -and $BaixarModulos) {
    $tmp = Join-Path $env:TEMP "mcmv-iis"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    if (-not $temRewrite) {
        $u = "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi"
        $f = Join-Path $tmp "rewrite.msi"
        Write-Host "  Baixando URL Rewrite..."; Baixar-Arquivo $u $f
        Start-Process msiexec.exe -ArgumentList "/i `"$f`" /qn /norestart" -Wait
    }
    if (-not $temArr) {
        $u = "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/requestRouter_amd64.msi"
        $f = Join-Path $tmp "arr.msi"
        Write-Host "  Baixando ARR..."; Baixar-Arquivo $u $f
        Start-Process msiexec.exe -ArgumentList "/i `"$f`" /qn /norestart" -Wait
    }
    net stop was /y 2>$null | Out-Null
    net start w3svc 2>$null | Out-Null
    $temRewrite = [bool](Get-WebGlobalModule | Where-Object { $_.Name -eq "RewriteModule" })
    $temArr = Test-Path $arrDll
}

if (-not $temRewrite -or -not $temArr) {
    Write-Host "FALTAM modulos do IIS:" -ForegroundColor Yellow
    if (-not $temRewrite) { Write-Host "  - URL Rewrite 2.1: https://www.iis.net/downloads/microsoft/url-rewrite" }
    if (-not $temArr)     { Write-Host "  - Application Request Routing 3.0: https://www.iis.net/downloads/microsoft/application-request-routing" }
    Write-Host "Instale-os (ou rode com -BaixarModulos, com internet) e execute novamente." -ForegroundColor Yellow
    throw "Modulos ausentes."
}

Write-Host "== 3/6 Habilitando o proxy do ARR ==" -ForegroundColor Cyan
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "enabled" -value "True"
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "preserveHostHeader" -value "True"

Write-Host "== 4/6 Publicando o site no IIS ==" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $SitePath | Out-Null
Copy-Item (Join-Path $PSScriptRoot "web.config") (Join-Path $SitePath "web.config") -Force
if (Get-Website -Name $SiteName -ErrorAction SilentlyContinue) { Remove-Website -Name $SiteName }
New-Website -Name $SiteName -PhysicalPath $SitePath -Port $Porta -HostHeader $Hostname -Force | Out-Null
# Binding adicional por IP (permite acessar por http://IP antes do DNS apontar).
if ($Ip) {
    try {
        New-WebBinding -Name $SiteName -Protocol http -Port $Porta -IPAddress $Ip -HostHeader "" -ErrorAction Stop
    } catch {
        Write-Host "  (binding por IP ja existia ou nao pode ser criado: $($_.Exception.Message))" -ForegroundColor DarkYellow
    }
}
# Para o "Default Web Site" para ele não responder na porta 80 no lugar do MCMV.
$dws = Get-Website -Name "Default Web Site" -ErrorAction SilentlyContinue
if ($dws) {
    Stop-Website -Name "Default Web Site" -ErrorAction SilentlyContinue
    Set-ItemProperty "IIS:\Sites\Default Web Site" -Name serverAutoStart -Value $false -ErrorAction SilentlyContinue
    Write-Host "  'Default Web Site' parado (evita conflito na porta $Porta)."
}
Start-Website -Name $SiteName

Write-Host "== 5/6 Liberando a porta $Porta no firewall ==" -ForegroundColor Cyan
netsh advfirewall firewall add rule name="MCMV IIS $Porta" dir=in action=allow protocol=TCP localport=$Porta | Out-Null

Write-Host "== 6/6 Ajustando o .env do Django ==" -ForegroundColor Cyan
if ($ProjetoDir -and (Test-Path (Join-Path $ProjetoDir ".env"))) {
    $envPath = Join-Path $ProjetoDir ".env"
    $desejado = [ordered]@{
        "DJANGO_BEHIND_PROXY"         = "1"
        "DJANGO_SSL_REDIRECT"         = "0"
        "DJANGO_ALLOWED_HOSTS"        = "$Hostname,172.16.64.9,127.0.0.1,localhost"
        "DJANGO_CSRF_TRUSTED_ORIGINS" = "http://$Hostname"
        "MCMV_HOST"                   = "127.0.0.1"
        "MCMV_PORT"                   = "8000"
    }
    $linhas = Get-Content $envPath
    foreach ($k in $desejado.Keys) {
        $v = "$k=$($desejado[$k])"
        if ($linhas -match "^\s*$k=") {
            $linhas = $linhas -replace "^\s*$k=.*", $v
        } else {
            $linhas += $v
        }
    }
    Set-Content -Path $envPath -Value $linhas -Encoding UTF8
    Write-Host "  .env atualizado em $envPath" -ForegroundColor Green
    Write-Host "  Reinicie o Waitress (servico MCMV ou iniciar.bat) para aplicar." -ForegroundColor Yellow
} else {
    Write-Host "  Informe -ProjetoDir para atualizar o .env automaticamente, ou ajuste manualmente:" -ForegroundColor Yellow
    Write-Host "    DJANGO_BEHIND_PROXY=1"
    Write-Host "    DJANGO_SSL_REDIRECT=0"
    Write-Host "    DJANGO_ALLOWED_HOSTS=$Hostname,172.16.64.9,127.0.0.1,localhost"
    Write-Host "    DJANGO_CSRF_TRUSTED_ORIGINS=http://$Hostname"
    Write-Host "    MCMV_HOST=127.0.0.1"
    Write-Host "    MCMV_PORT=8000"
}

Write-Host ""
Write-Host "Concluido. Apos o DNS apontar $Hostname -> 172.16.64.9, acesse:" -ForegroundColor Green
Write-Host "  http://$Hostname" -ForegroundColor Green
Write-Host "Garanta que o Waitress esteja rodando em $Backend (servico MCMV/NSSM)." -ForegroundColor Green
