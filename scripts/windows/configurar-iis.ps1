<#
    SIGTRANS Saude - Configuracao automatica do IIS como proxy reverso (HTTPS)

    O que faz:
      1. Garante o IIS instalado.
      2. Verifica os modulos URL Rewrite e ARR (se faltarem, avisa e para).
      3. Importa o certificado (.pfx) no repositorio do computador.
      4. Cria os bindings HTTP (80) e HTTPS (443) e vincula o certificado.
      5. Habilita o proxy do ARR (preservando o Host).
      6. Libera a variavel HTTP_X_FORWARDED_PROTO.
      7. Grava o web.config que encaminha para o Waitress (127.0.0.1:8000).
      8. Libera o firewall (80/443) e reinicia o IIS.

    Requer execucao como Administrador. Use o configurar-iis.bat (ele eleva
    automaticamente) ou rode em um PowerShell "Como administrador":
        powershell -ExecutionPolicy Bypass -File configurar-iis.ps1

    Parametros (opcionais):
        -Site      Nome do site no IIS    (padrao: "Default Web Site")
        -Dominio   Nome DNS do site       (padrao: sigtrans.baraodecocais.mg.gov.br)
        -Pfx       Caminho do .pfx        (padrao: C:\certs\sigtrans.pfx)
        -SenhaPfx  Senha do .pfx          (se omitida, sera solicitada)
        -Backend   Endereco do Waitress   (padrao: http://127.0.0.1:8000)
#>
[CmdletBinding()]
param(
    [string]$Site     = "Default Web Site",
    [string]$Dominio  = "sigtrans.baraodecocais.mg.gov.br",
    [string]$Pfx      = "C:\certs\sigtrans.pfx",
    [string]$SenhaPfx = "",
    [string]$Backend  = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
function Info($m)  { Write-Host $m -ForegroundColor Cyan }
function Ok($m)    { Write-Host $m -ForegroundColor Green }
function Aviso($m) { Write-Host $m -ForegroundColor Yellow }
function Erro($m)  { Write-Host $m -ForegroundColor Red }

# 0) Administrador
$idn = [Security.Principal.WindowsIdentity]::GetCurrent()
$prc = New-Object Security.Principal.WindowsPrincipal($idn)
if (-not $prc.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Erro "Este script precisa ser executado como Administrador."
    Erro "Use o configurar-iis.bat (ele pede elevacao) ou abra o PowerShell como admin."
    exit 1
}

if (-not (Test-Path $Pfx)) {
    Erro "Certificado nao encontrado: $Pfx"
    Erro "Rode antes o criar-certificado.bat."
    exit 1
}

# 1) IIS instalado
Info "[1/8] Verificando o IIS..."
Import-Module ServerManager -ErrorAction SilentlyContinue
if (Get-Command Get-WindowsFeature -ErrorAction SilentlyContinue) {
    if (-not (Get-WindowsFeature Web-Server).Installed) {
        Ok "   Instalando o IIS (pode demorar)..."
        Install-WindowsFeature Web-Server -IncludeManagementTools | Out-Null
    }
}
Import-Module WebAdministration

# 2) URL Rewrite + ARR
Info "[2/8] Verificando URL Rewrite e ARR..."
$rewriteOk = Test-Path "$env:windir\System32\inetsrv\rewrite.dll"
$arrOk     = Test-Path "$env:ProgramFiles\IIS\Application Request Routing"
if (-not $rewriteOk -or -not $arrOk) {
    Erro "Faltam modulos do IIS. Instale e rode este script de novo:"
    if (-not $rewriteOk) { Erro "  - URL Rewrite 2.1: https://www.iis.net/downloads/microsoft/url-rewrite" }
    if (-not $arrOk)     { Erro "  - App Request Routing 3.0: https://www.iis.net/downloads/microsoft/application-request-routing" }
    Aviso "Dica: instale pelo 'Web Platform Installer' (busque por 'URL Rewrite' e 'Application Request Routing')."
    exit 1
}

# 3) Importar o certificado (.pfx) no repositorio do computador
Info "[3/8] Importando o certificado..."
if ($SenhaPfx) {
    $senhaPlain = $SenhaPfx
} else {
    $sec = Read-Host "Senha do arquivo .pfx" -AsSecureString
    $senhaPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
}
$flags = [Security.Cryptography.X509Certificates.X509KeyStorageFlags]"MachineKeySet,PersistKeySet,Exportable"
$cert  = New-Object Security.Cryptography.X509Certificates.X509Certificate2
$cert.Import($Pfx, $senhaPlain, $flags)
$store = New-Object Security.Cryptography.X509Certificates.X509Store("My", "LocalMachine")
$store.Open("ReadWrite"); $store.Add($cert); $store.Close()
$thumb = $cert.Thumbprint
Ok "   Certificado importado (thumbprint $thumb)."

# 4) Bindings HTTP/HTTPS + vinculo do certificado
Info "[4/8] Configurando os bindings do site '$Site'..."
if (-not (Get-WebBinding -Name $Site -Protocol http -Port 80 -ErrorAction SilentlyContinue)) {
    New-WebBinding -Name $Site -Protocol http -Port 80 | Out-Null
}
if (-not (Get-WebBinding -Name $Site -Protocol https -Port 443 -ErrorAction SilentlyContinue)) {
    New-WebBinding -Name $Site -Protocol https -Port 443 | Out-Null
}
(Get-WebBinding -Name $Site -Protocol https -Port 443).AddSslCertificate($thumb, "My")
Ok "   Bindings 80 e 443 prontos."

# 5) Habilitar proxy do ARR (preservando o Host)
Info "[5/8] Habilitando o proxy (ARR)..."
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "enabled" -value "True"
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "preserveHostHeader" -value "True"

# 6) Liberar a variavel de servidor usada pela regra
Info "[6/8] Liberando HTTP_X_FORWARDED_PROTO..."
$psPath = 'MACHINE/WEBROOT/APPHOST'
$filtro = "system.webServer/rewrite/allowedServerVariables"
$existe = Get-WebConfiguration -pspath $psPath -filter "$filtro/add[@name='HTTP_X_FORWARDED_PROTO']" -ErrorAction SilentlyContinue
if (-not $existe) {
    Add-WebConfigurationProperty -pspath $psPath -filter $filtro -name "." -value @{ name = 'HTTP_X_FORWARDED_PROTO' }
}

# 7) Gravar o web.config (redireciona p/ HTTPS e faz o proxy)
Info "[7/8] Gravando o web.config..."
$siteObj = Get-Website -Name $Site
$fisico  = [Environment]::ExpandEnvironmentVariables($siteObj.physicalPath)
if (-not (Test-Path $fisico)) { New-Item -ItemType Directory -Path $fisico | Out-Null }
$webconfig = Join-Path $fisico "web.config"
if (Test-Path $webconfig) { Copy-Item $webconfig "$webconfig.bak" -Force; Aviso "   web.config anterior salvo como web.config.bak" }

$conteudo = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="Forcar HTTPS" stopProcessing="true">
          <match url="(.*)" />
          <conditions>
            <add input="{HTTPS}" pattern="off" />
          </conditions>
          <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
        </rule>
        <rule name="Proxy SIGTRANS" stopProcessing="true">
          <match url="(.*)" />
          <serverVariables>
            <set name="HTTP_X_FORWARDED_PROTO" value="https" />
          </serverVariables>
          <action type="Rewrite" url="$Backend/{R:1}" />
        </rule>
      </rules>
    </rewrite>
    <security>
      <requestFiltering>
        <requestLimits maxAllowedContentLength="20971520" />
      </requestFiltering>
    </security>
  </system.webServer>
</configuration>
"@
[IO.File]::WriteAllText($webconfig, $conteudo, (New-Object Text.UTF8Encoding($false)))
Ok "   web.config gravado em $webconfig"

# 8) Firewall + reiniciar IIS
Info "[8/8] Liberando firewall (80/443) e reiniciando o IIS..."
& netsh advfirewall firewall add rule name="SIGTRANS HTTP 80"  dir=in action=allow protocol=TCP localport=80  | Out-Null
& netsh advfirewall firewall add rule name="SIGTRANS HTTPS 443" dir=in action=allow protocol=TCP localport=443 | Out-Null
& iisreset /restart | Out-Null

Info ""
Info "============================================================"
Ok   " IIS configurado com sucesso!"
Info "============================================================"
Write-Host " Teste agora: https://$Dominio"
Write-Host ""
Write-Host " Antes de testar, confirme que:"
Write-Host "  - O SIGTRANS esta rodando (iniciar-producao.bat) em 127.0.0.1:8000."
Write-Host "  - A CA (C:\certs\prefeitura-ca.crt) foi distribuida nas maquinas"
Write-Host "    (senao o navegador mostra aviso de certificado)."
Info "============================================================"
