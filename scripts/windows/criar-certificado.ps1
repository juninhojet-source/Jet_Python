<#
    SIGTRANS Saude - Geracao automatica do certificado interno (HTTPS)

    Cria uma CA (autoridade certificadora) da Prefeitura e, com ela, o
    certificado do site, no formato pronto para o IIS (.pfx) e para o nginx
    (fullchain). Usa o OpenSSL que acompanha o Git para Windows.

    Uso (Git nao precisa estar no PATH):
        powershell -ExecutionPolicy Bypass -File criar-certificado.ps1
    ou, mais simples, execute o criar-certificado.bat

    Parametros (todos opcionais):
        -Dominio   Nome DNS do site       (padrao: sigtrans.baraodecocais.mg.gov.br)
        -IP        IP do servidor         (padrao: 172.16.64.8)
        -Saida     Pasta de saida         (padrao: C:\certs)
        -Dias      Validade em dias       (padrao: 3650 = 10 anos)
        -SenhaPfx  Senha do arquivo .pfx  (se omitida, sera solicitada)

    Reexecucao: se a CA (prefeitura-ca.crt/.key) ja existir na pasta de saida,
    ela e REUTILIZADA (as maquinas que ja confiam nela continuam confiando).
    Apenas o certificado do site e regerado.
#>
[CmdletBinding()]
param(
    [string]$Dominio  = "sigtrans.baraodecocais.mg.gov.br",
    [string]$IP       = "172.16.64.8",
    [string]$Saida    = "C:\certs",
    [int]   $Dias     = 3650,
    [string]$SenhaPfx = ""
)

$ErrorActionPreference = "Stop"

function Escrever($cor, $txt) { Write-Host $txt -ForegroundColor $cor }

# ----------------------------------------------------------- localizar OpenSSL
function Achar-OpenSSL {
    $cands = @(
        "$env:ProgramFiles\Git\usr\bin\openssl.exe",
        "$env:ProgramFiles\Git\mingw64\bin\openssl.exe",
        "${env:ProgramFiles(x86)}\Git\usr\bin\openssl.exe",
        "$env:LOCALAPPDATA\Programs\Git\usr\bin\openssl.exe"
    )
    foreach ($c in $cands) { if (Test-Path $c) { return $c } }
    $cmd = Get-Command openssl.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$openssl = Achar-OpenSSL
if (-not $openssl) {
    Escrever Red "[ERRO] OpenSSL nao encontrado. Instale o Git para Windows"
    Escrever Red "       (https://git-scm.com/download/win) e rode de novo."
    exit 1
}
Escrever Cyan "OpenSSL: $openssl"

function OpenSSL() {
    & $openssl @args
    if ($LASTEXITCODE -ne 0) { throw "Falha no OpenSSL (codigo $LASTEXITCODE): openssl $args" }
}

# ------------------------------------------------------------------- preparar
if (-not (Test-Path $Saida)) { New-Item -ItemType Directory -Path $Saida | Out-Null }
Escrever Cyan "Pasta de saida: $Saida"

$caKey = Join-Path $Saida "prefeitura-ca.key"
$caCrt = Join-Path $Saida "prefeitura-ca.crt"
$srvKey = Join-Path $Saida "sigtrans.key"
$srvCsr = Join-Path $Saida "sigtrans.csr"
$srvExt = Join-Path $Saida "sigtrans.ext"
$srvCrt = Join-Path $Saida "sigtrans.crt"
$pfx    = Join-Path $Saida "sigtrans.pfx"
$full   = Join-Path $Saida "sigtrans-fullchain.crt"

$subjBase = "/C=BR/ST=MG/L=Barao de Cocais/O=Prefeitura Municipal de Barao de Cocais"

# senha do PFX
if (-not $SenhaPfx) {
    $sec = Read-Host "Defina uma senha para o arquivo .pfx (guarde-a)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    $SenhaPfx = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
}
if (-not $SenhaPfx) { Escrever Red "[ERRO] Senha do PFX nao informada."; exit 1 }

# --------------------------------------------------------------- 1) CA interna
if ((Test-Path $caKey) -and (Test-Path $caCrt)) {
    Escrever Yellow "CA existente encontrada - REUTILIZANDO (nao redistribuir)."
} else {
    Escrever Green "[1/4] Criando a CA interna da Prefeitura..."
    OpenSSL genrsa -out $caKey 4096
    OpenSSL req -x509 -new -nodes -key $caKey -sha256 -days $Dias `
        -subj "$subjBase/CN=Prefeitura BC - CA Interna" -out $caCrt
}

# ------------------------------------------------------ 2) chave + CSR do site
Escrever Green "[2/4] Gerando chave e pedido do site ($Dominio)..."
OpenSSL genrsa -out $srvKey 2048
OpenSSL req -new -key $srvKey -subj "$subjBase/CN=$Dominio" -out $srvCsr

# extensoes (SAN + serverAuth) - obrigatorio para navegadores modernos
$extConteudo = "subjectAltName=DNS:$Dominio,IP:$IP`r`nextendedKeyUsage=serverAuth`r`n"
[IO.File]::WriteAllText($srvExt, $extConteudo, [Text.Encoding]::ASCII)

# --------------------------------------------------- 3) assinar com a CA
Escrever Green "[3/4] Assinando o certificado do site (validade $Dias dias)..."
OpenSSL x509 -req -in $srvCsr -CA $caCrt -CAkey $caKey -CAcreateserial `
    -days $Dias -sha256 -extfile $srvExt -out $srvCrt

# --------------------------------------------------- 4) exportar PFX + fullchain
Escrever Green "[4/4] Exportando .pfx (IIS) e fullchain (nginx)..."
$env:SIGTRANS_PFXPASS = $SenhaPfx
# PBE 3DES/SHA1 = maxima compatibilidade com importacao no Windows.
OpenSSL pkcs12 -export -out $pfx -inkey $srvKey -in $srvCrt -certfile $caCrt `
    -passout env:SIGTRANS_PFXPASS -certpbe PBE-SHA1-3DES -keypbe PBE-SHA1-3DES -macalg sha1
Remove-Item Env:\SIGTRANS_PFXPASS

$conteudoFull = (Get-Content $srvCrt -Raw) + (Get-Content $caCrt -Raw)
[IO.File]::WriteAllText($full, $conteudoFull, [Text.Encoding]::ASCII)

# ----------------------------------------------------------------- resumo
Escrever Cyan  ""
Escrever Cyan  "============================================================"
Escrever Green " Certificado gerado com sucesso!"
Escrever Cyan  "============================================================"
Write-Host    " Pasta: $Saida"
Write-Host    ""
Write-Host    " Para o IIS ....... sigtrans.pfx            (importar e vincular na 443)"
Write-Host    " Para o nginx ..... sigtrans-fullchain.crt + sigtrans.key"
Write-Host    " Distribuir ....... prefeitura-ca.crt       (nas maquinas, via GPO)"
Write-Host    ""
Write-Host    " Proximos passos: docs\MANUAL_PUBLICACAO_DOMINIO_HTTPS.md (secoes 5 e 6)."
Escrever Yellow " Guarde prefeitura-ca.key em local seguro (e a chave da CA)."
Escrever Cyan  "============================================================"
