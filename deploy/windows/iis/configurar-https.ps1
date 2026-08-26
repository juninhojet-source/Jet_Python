<#
    Configura HTTPS no IIS (proxy reverso) para o Sistema MCMV.

    Fluxo: navegador --HTTPS--> IIS (porta 443, certificado) --HTTP--> Waitress
           (127.0.0.1:8000). Requisicoes HTTP (porta 80) sao redirecionadas
           para HTTPS.

    Este script:
      - garante os recursos do IIS e os modulos URL Rewrite + ARR (proxy);
      - garante o site MCMV com o web.config de HTTPS;
      - gera um certificado AUTOASSINADO para o hostname (e o IP) e o vincula
        na porta 443 (ou usa um .pfx existente com -Pfx / -SenhaPfx);
      - exporta o certificado publico (.cer) para instalar nos clientes;
      - libera a porta 443 no firewall;
      - ajusta o .env do Django para HTTPS (SSL_REDIRECT=1, BEHIND_PROXY=1).

    Pre-requisitos:
      - PowerShell COMO ADMINISTRADOR.
      - Waitress rodando em 127.0.0.1:8000 (servico MCMV). Apos rodar este
        script, reinicie o servico para aplicar o .env (net stop/start MCMV).

    Uso (exemplo, autoassinado):
      cd C:\mcmv\Jet_Python\deploy\windows\iis
      powershell -ExecutionPolicy Bypass -File .\configurar-https.ps1 `
        -ProjetoDir C:\mcmv\Jet_Python -BaixarModulos

    Uso (certificado oficial .pfx):
      powershell -ExecutionPolicy Bypass -File .\configurar-https.ps1 `
        -ProjetoDir C:\mcmv\Jet_Python -Pfx C:\certs\mcmv.pfx -SenhaPfx "senha"
#>
param(
    [string]$Hostname   = "mcmv.baraodecocais.mg.gov.br",
    [string]$Ip         = "172.16.64.9",
    [string]$SiteName   = "MCMV",
    [string]$SitePath   = "C:\mcmv\iis-site",
    [string]$ProjetoDir = "",
    [string]$Pfx        = "",
    [string]$SenhaPfx   = "",
    [string]$CerSaida   = "C:\mcmv\mcmv-cert.cer",
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

Write-Host "== 1/8 Recursos do IIS ==" -ForegroundColor Cyan
Import-Module ServerManager -ErrorAction SilentlyContinue
Install-WindowsFeature -Name Web-Server, Web-Common-Http, Web-Static-Content, `
    Web-Default-Doc, Web-Http-Errors, Web-Http-Logging, Web-Filtering, `
    Web-Mgmt-Console -IncludeManagementTools | Out-Null
Import-Module WebAdministration

Write-Host "== 2/8 Modulos URL Rewrite e ARR ==" -ForegroundColor Cyan
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
    if (-not $temArr)     { Write-Host "  - ARR 3.0: https://www.iis.net/downloads/microsoft/application-request-routing" }
    Write-Host "Instale-os (ou rode com -BaixarModulos, com internet) e tente de novo." -ForegroundColor Yellow
    throw "Modulos ausentes."
}

Write-Host "== 3/8 Habilitando o proxy do ARR ==" -ForegroundColor Cyan
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "enabled" -value "True"
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "preserveHostHeader" -value "True"

Write-Host "== 4/8 Publicando o site e o web.config de HTTPS ==" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $SitePath | Out-Null
Copy-Item (Join-Path $PSScriptRoot "web-https.config") (Join-Path $SitePath "web.config") -Force
if (-not (Get-Website -Name $SiteName -ErrorAction SilentlyContinue)) {
    New-Website -Name $SiteName -PhysicalPath $SitePath -Port 80 -HostHeader $Hostname -Force | Out-Null
}
# Garante binding HTTP por IP (para o redirect funcionar tambem por IP).
if ($Ip) {
    try { New-WebBinding -Name $SiteName -Protocol http -Port 80 -IPAddress $Ip -HostHeader "" -ErrorAction Stop } catch {}
}
# Para o Default Web Site (evita conflito na porta 80/443).
$dws = Get-Website -Name "Default Web Site" -ErrorAction SilentlyContinue
if ($dws) {
    Stop-Website -Name "Default Web Site" -ErrorAction SilentlyContinue
    Set-ItemProperty "IIS:\Sites\Default Web Site" -Name serverAutoStart -Value $false -ErrorAction SilentlyContinue
}

Write-Host "== 5/8 Certificado TLS ==" -ForegroundColor Cyan
if ($Pfx) {
    if (-not (Test-Path $Pfx)) { throw "Arquivo PFX nao encontrado: $Pfx" }
    Write-Host "  Importando PFX: $Pfx"
    $sec = ConvertTo-SecureString -String $SenhaPfx -AsPlainText -Force
    $cert = Import-PfxCertificate -FilePath $Pfx -CertStoreLocation Cert:\LocalMachine\My -Password $sec
} else {
    Write-Host "  Gerando certificado AUTOASSINADO para: $Hostname, $Ip"
    $nomes = @($Hostname)
    if ($Ip) { $nomes += $Ip }
    # OBS: no Windows 2012 R2 o New-SelfSignedCertificate e a versao antiga
    # (nao aceita -FriendlyName/-NotAfter). Usamos apenas -DnsName.
    $cert = New-SelfSignedCertificate -DnsName $nomes -CertStoreLocation Cert:\LocalMachine\My -ErrorAction Stop
    try { $cert.FriendlyName = "MCMV - $Hostname" } catch {}
    # Exporta o certificado publico (.cer) para instalar nos clientes.
    New-Item -ItemType Directory -Force -Path (Split-Path $CerSaida) | Out-Null
    Export-Certificate -Cert $cert -FilePath $CerSaida -Force | Out-Null
    Write-Host "  Certificado publico exportado em: $CerSaida" -ForegroundColor Green
    Write-Host "  (instale-o nas maquinas clientes em 'Autoridades de Certificacao Raiz Confiaveis')" -ForegroundColor Yellow
}
$thumb = $cert.Thumbprint
Write-Host "  Thumbprint: $thumb"

Write-Host "== 6/8 Binding HTTPS (porta 443) ==" -ForegroundColor Cyan
# Binding sem host header (0.0.0.0:443) -> funciona por hostname E por IP, sem SNI.
$b = Get-WebBinding -Name $SiteName -Protocol https -Port 443 -ErrorAction SilentlyContinue
if (-not $b) {
    New-WebBinding -Name $SiteName -Protocol https -Port 443 -IPAddress "*" -HostHeader "" | Out-Null
    $b = Get-WebBinding -Name $SiteName -Protocol https -Port 443
}
$b.AddSslCertificate($thumb, "My")
Start-Website -Name $SiteName -ErrorAction SilentlyContinue

Write-Host "== 7/8 Firewall (portas 80 e 443) ==" -ForegroundColor Cyan
netsh advfirewall firewall add rule name="MCMV IIS 80" dir=in action=allow protocol=TCP localport=80 | Out-Null
netsh advfirewall firewall add rule name="MCMV IIS 443" dir=in action=allow protocol=TCP localport=443 | Out-Null

Write-Host "== 8/8 Ajustando o .env do Django (HTTPS) ==" -ForegroundColor Cyan
if ($ProjetoDir -and (Test-Path (Join-Path $ProjetoDir ".env"))) {
    $envPath = Join-Path $ProjetoDir ".env"
    # HSTS: ligado so com certificado oficial. Autoassinado -> 0 (desligado),
    # para nao "prender" o navegador em HTTPS caso o cert autoassinado expire.
    $hsts = if ($Pfx) { "31536000" } else { "0" }
    $desejado = [ordered]@{
        "DJANGO_BEHIND_PROXY"         = "1"
        "DJANGO_SSL_REDIRECT"         = "1"
        "DJANGO_HSTS_SECONDS"         = $hsts
        "DJANGO_ALLOWED_HOSTS"        = "$Hostname,$Ip,127.0.0.1,localhost"
        "DJANGO_CSRF_TRUSTED_ORIGINS" = "https://$Hostname,https://$Ip"
        "MCMV_HOST"                   = "127.0.0.1"
        "MCMV_PORT"                   = "8000"
    }
    $linhas = Get-Content $envPath
    foreach ($k in $desejado.Keys) {
        $v = "$k=$($desejado[$k])"
        if ($linhas -match "^\s*$k=") { $linhas = $linhas -replace "^\s*$k=.*", $v }
        else { $linhas += $v }
    }
    Set-Content -Path $envPath -Value $linhas -Encoding UTF8
    Write-Host "  .env atualizado em $envPath" -ForegroundColor Green
} else {
    Write-Host "  Informe -ProjetoDir para atualizar o .env, ou ajuste manualmente:" -ForegroundColor Yellow
    Write-Host "    DJANGO_BEHIND_PROXY=1"
    Write-Host "    DJANGO_SSL_REDIRECT=1"
    Write-Host "    DJANGO_ALLOWED_HOSTS=$Hostname,$Ip,127.0.0.1,localhost"
    Write-Host "    DJANGO_CSRF_TRUSTED_ORIGINS=https://$Hostname,https://$Ip"
    Write-Host "    MCMV_HOST=127.0.0.1"
    Write-Host "    MCMV_PORT=8000"
}

Write-Host ""
Write-Host "Concluido. AGORA reinicie o Waitress para aplicar o .env:" -ForegroundColor Green
Write-Host "  net stop MCMV  &&  net start MCMV" -ForegroundColor Green
Write-Host "Acesse: https://$Hostname  (ou https://$Ip)" -ForegroundColor Green
Write-Host "Com certificado autoassinado, o navegador avisa 'Nao seguro' ate" -ForegroundColor Yellow
Write-Host "instalar $CerSaida nos clientes (Certificados > Autoridades Raiz Confiaveis)." -ForegroundColor Yellow
