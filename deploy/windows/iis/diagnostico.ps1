<#
    Diagnostico do acesso ao Sistema MCMV no Windows (IIS + Waitress).

    Verifica, em ordem, cada elo da cadeia:
        navegador -> IIS (porta 80) -> Waitress (127.0.0.1:8000) -> Django

    NAO altera nada; apenas informa o que esta certo/errado e o que fazer.

    Uso (PowerShell COMO ADMINISTRADOR):
      cd C:\mcmv\Jet_Python\deploy\windows\iis
      powershell -ExecutionPolicy Bypass -File .\diagnostico.ps1
#>
param(
    [string]$Ip      = "172.16.64.9",
    [int]$Porta      = 80,
    [string]$Backend = "http://127.0.0.1:8000",
    [string]$SiteName = "MCMV"
)

$ErrorActionPreference = "Continue"
function OK($m)    { Write-Host "[ OK ] $m"    -ForegroundColor Green }
function FALHA($m) { Write-Host "[FALHA] $m"   -ForegroundColor Red }
function INFO($m)  { Write-Host "[info] $m"    -ForegroundColor Cyan }
function ACAO($m)  { Write-Host "   -> $m"     -ForegroundColor Yellow }

Write-Host ""
Write-Host "=== Diagnostico MCMV (IIS + Waitress) ===" -ForegroundColor White
Write-Host ""

# 1) Waitress respondendo localmente?
INFO "1) Waitress (Django) em $Backend"
try {
    $r = Invoke-WebRequest -Uri $Backend -UseBasicParsing -TimeoutSec 8 -MaximumRedirection 0 -ErrorAction Stop
    OK "Waitress respondeu (HTTP $($r.StatusCode)). Django esta no ar."
} catch {
    $resp = $_.Exception.Response
    if ($resp -and $resp.StatusCode) {
        OK "Waitress respondeu (HTTP $([int]$resp.StatusCode)). Django esta no ar."
    } else {
        FALHA "Waitress NAO respondeu em $Backend. ($($_.Exception.Message))"
        ACAO "Inicie o Waitress: 'net start MCMV' ou scripts\windows\iniciar.bat"
        ACAO "Confirme no .env: MCMV_HOST=127.0.0.1  MCMV_PORT=8000 (para uso com IIS)."
    }
}

# 2) Modulos URL Rewrite e ARR instalados?
INFO "2) Modulos do IIS (URL Rewrite + ARR)"
Import-Module WebAdministration -ErrorAction SilentlyContinue
$temRewrite = [bool](Get-WebGlobalModule -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "RewriteModule" })
$arrDll = Join-Path $env:ProgramFiles "IIS\Application Request Routing\requestRouter.dll"
$temArr = Test-Path $arrDll
if ($temRewrite) { OK "URL Rewrite instalado." } else {
    FALHA "URL Rewrite NAO instalado."
    ACAO "Rode configurar-iis.ps1 -BaixarModulos (com internet), ou instale de https://www.iis.net/downloads/microsoft/url-rewrite"
}
if ($temArr) { OK "ARR instalado." } else {
    FALHA "Application Request Routing (ARR) NAO instalado."
    ACAO "Rode configurar-iis.ps1 -BaixarModulos (com internet), ou instale de https://www.iis.net/downloads/microsoft/application-request-routing"
}

# 3) Proxy do ARR habilitado?
INFO "3) Proxy do ARR habilitado"
try {
    $proxy = Get-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "enabled" -ErrorAction Stop
    if ($proxy.Value) { OK "Proxy do ARR habilitado." }
    else { FALHA "Proxy do ARR DESABILITADO."; ACAO "Rode configurar-iis.ps1 (habilita o proxy) ou ligue em IIS > Application Request Routing Cache > Server Proxy Settings > Enable proxy." }
} catch {
    FALHA "Nao foi possivel ler a config do proxy (ARR pode nao estar instalado)."
}

# 4) Site MCMV existe e esta iniciado?
INFO "4) Site '$SiteName' no IIS"
$site = Get-Website -Name $SiteName -ErrorAction SilentlyContinue
if ($site) {
    if ($site.State -eq "Started") { OK "Site '$SiteName' existe e esta Started." }
    else { FALHA "Site '$SiteName' existe mas esta $($site.State)."; ACAO "Start-Website -Name $SiteName" }
    Write-Host "       Bindings:" -ForegroundColor DarkGray
    Get-WebBinding -Name $SiteName | ForEach-Object { Write-Host "         $($_.protocol) $($_.bindingInformation)" -ForegroundColor DarkGray }
} else {
    FALHA "Site '$SiteName' NAO existe."
    ACAO "Rode: powershell -ExecutionPolicy Bypass -File .\configurar-iis.ps1 -ProjetoDir C:\mcmv\Jet_Python -BaixarModulos"
}

# 5) Default Web Site nao esta ocupando a porta 80?
INFO "5) 'Default Web Site' (conflito na porta $Porta)"
$dws = Get-Website -Name "Default Web Site" -ErrorAction SilentlyContinue
if ($dws -and $dws.State -eq "Started") {
    FALHA "'Default Web Site' esta Started e pode responder na porta $Porta no lugar do MCMV."
    ACAO "Stop-Website -Name 'Default Web Site'"
} else { OK "'Default Web Site' nao esta ocupando a porta (parado ou inexistente)." }

# 6) Alguem escutando na porta 80?
INFO "6) Quem escuta na porta $Porta"
$conns = Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    OK "Ha processo escutando na porta $Porta."
    $conns | Select-Object -First 3 | ForEach-Object {
        $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        Write-Host "         $($_.LocalAddress):$($_.LocalPort)  <- $($p.ProcessName) (PID $($_.OwningProcess))" -ForegroundColor DarkGray
    }
} else {
    FALHA "NINGUEM escutando na porta $Porta. Por isso 'nao abre'."
    ACAO "Suba o site MCMV (passo 4) ou reinicie o IIS: iisreset"
}

# 7) Firewall libera a porta 80?
INFO "7) Firewall na porta $Porta"
$fw = Get-NetFirewallPortFilter -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq "$Porta" }
if ($fw) { OK "Ha regra de firewall referenciando a porta $Porta." }
else {
    FALHA "Sem regra de firewall explicita para a porta $Porta (pode estar bloqueada de fora)."
    ACAO "netsh advfirewall firewall add rule name=`"MCMV IIS $Porta`" dir=in action=allow protocol=TCP localport=$Porta"
}

# 8) Teste real: IIS -> Waitress pela porta 80 (localhost)
INFO "8) Teste porta $Porta -> backend (via IIS, localhost)"
try {
    $r2 = Invoke-WebRequest -Uri "http://127.0.0.1:$Porta/" -UseBasicParsing -TimeoutSec 8 -MaximumRedirection 0 -ErrorAction Stop
    OK "IIS respondeu na porta $Porta (HTTP $($r2.StatusCode)). Proxy funcionando localmente."
} catch {
    $resp2 = $_.Exception.Response
    if ($resp2 -and $resp2.StatusCode) {
        $code = [int]$resp2.StatusCode
        if ($code -ge 500) { FALHA "IIS respondeu HTTP $code na porta $Porta (erro do proxy/backend). Veja passos 1-3." }
        else { OK "IIS respondeu HTTP $code na porta $Porta (chegou ao Django)." }
    } else {
        FALHA "Nada respondeu em http://127.0.0.1:$Porta ($($_.Exception.Message)). Veja passos 4-6."
    }
}

Write-Host ""
Write-Host "=== Resumo ===" -ForegroundColor White
Write-Host "Se 1) OK e 8) OK  -> acesse de outro PC: http://$Ip  (sem :8000)" -ForegroundColor Green
Write-Host "Se faltam modulos -> configurar-iis.ps1 -BaixarModulos (com internet)" -ForegroundColor Yellow
Write-Host "Alternativa sem IIS -> .env MCMV_HOST=0.0.0.0 e acesse http://$Ip`:8000" -ForegroundColor Yellow
Write-Host ""
