# Publicação por domínio + HTTPS — SIGTRANS Saúde

Guia para acessar o sistema por **https://sigtrans.baraodecocais.mg.gov.br**
(sem digitar `:8000`) e com **certificado gratuito**, no servidor
**172.16.64.8** (Windows Server).

> Cenário desta instalação: acesso **somente pela rede interna** da Prefeitura
> (o IP 172.16.64.8 é interno) e **sem controle do DNS público** do domínio.
> Por isso o certificado será um **certificado interno gratuito** (CA da própria
> Prefeitura), confiável em todas as máquinas após um passo único de distribuição.
> Veja o porquê no fim (seção “Sobre o Let's Encrypt”).

---

## 1. Como fica a arquitetura

```
   Navegador do usuário
        │  https://sigtrans.baraodecocais.mg.gov.br   (porta 443, com cadeado)
        ▼
   Proxy reverso  (IIS ou nginx)   ← termina o HTTPS (certificado)
        │  http://127.0.0.1:8000                       (interno ao servidor)
        ▼
   Waitress → Django (SIGTRANS)
```

- O **Django/Waitress** roda apenas em `127.0.0.1:8000` (não acessível de fora).
- O **proxy reverso** publica nas portas **80/443**, cuida do certificado e
  encaminha para o Waitress.
- O usuário nunca mais digita a porta `:8000`.

Você vai fazer, na ordem:
1. Rodar o SIGTRANS em modo produção (Waitress).
2. Gerar o certificado interno gratuito.
3. Configurar o proxy reverso (recomendado: **IIS**).
4. Distribuir o certificado nas máquinas (tira o aviso do navegador).
5. Liberar o firewall e testar.

---

## 2. Confirmar o apontamento de DNS

No servidor (ou em um PC da rede), abra o Prompt de Comando e rode:

```
nslookup sigtrans.baraodecocais.mg.gov.br
```

Deve responder **172.16.64.8**. Se não responder, o apontamento de DNS ainda
não propagou — aguarde ou verifique com quem administra o DNS.

---

## 3. Passo 1 — Rodar o SIGTRANS em produção (Waitress)

1. Na pasta do sistema, copie `.env.example` para `.env` e edite:

   ```
   SECRET_KEY=<uma-chave-longa-e-aleatoria>
   DEBUG=False
   ALLOWED_HOSTS=sigtrans.baraodecocais.mg.gov.br,172.16.64.8,localhost,127.0.0.1
   CSRF_TRUSTED_ORIGINS=https://sigtrans.baraodecocais.mg.gov.br
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

   Para gerar a `SECRET_KEY`:
   ```
   .venv\Scripts\python.exe -c "import secrets;print(secrets.token_urlsafe(64))"
   ```

2. Inicie em produção:
   ```
   scripts\windows\iniciar-producao.bat
   ```
   Isso roda o `collectstatic` e sobe o Waitress em `127.0.0.1:8000`.
   Teste no próprio servidor: `http://127.0.0.1:8000` deve abrir a tela de login.

> **Para iniciar sozinho quando o servidor ligar**, registre como serviço do
> Windows com o **NSSM** (ver seção 8).

---

## 4. Passo 2 — Gerar o certificado interno gratuito (OpenSSL)

Vamos criar **uma CA (autoridade certificadora) da Prefeitura** e, com ela,
o certificado do site. O OpenSSL já vem com o **Git para Windows** (instalado
antes).

### Forma automática (recomendada)

Execute o script pronto — ele localiza o OpenSSL do Git e gera tudo em `C:\certs`:

```
scripts\windows\criar-certificado.bat
```

Ele pede uma senha para o arquivo `.pfx` e cria: `prefeitura-ca.crt` (distribuir
nas máquinas), `sigtrans.pfx` (IIS) e `sigtrans-fullchain.crt` + `sigtrans.key`
(nginx). Ao reexecutar, **reutiliza a mesma CA** (as máquinas continuam confiando).

Parâmetros opcionais (se precisar mudar):
```
powershell -ExecutionPolicy Bypass -File scripts\windows\criar-certificado.ps1 ^
  -Dominio sigtrans.baraodecocais.mg.gov.br -IP 172.16.64.8 -Saida C:\certs -Dias 3650
```

Feito isso, pule para o **Passo 3** (seção 5). Se preferir fazer manualmente,
siga abaixo.

### Forma manual (passo a passo no Git Bash)

Crie uma pasta `C:\certs` e, dentro dela, no Git Bash:

```bash
cd /c/certs

# 1) Autoridade Certificadora da Prefeitura (validade 10 anos) — cria uma vez.
openssl genrsa -out prefeitura-ca.key 4096
openssl req -x509 -new -nodes -key prefeitura-ca.key -sha256 -days 3650 \
  -subj "/C=BR/ST=MG/L=Barao de Cocais/O=Prefeitura Municipal de Barao de Cocais/CN=Prefeitura BC - CA Interna" \
  -out prefeitura-ca.crt

# 2) Chave e pedido (CSR) do site.
openssl genrsa -out sigtrans.key 2048
openssl req -new -key sigtrans.key \
  -subj "/C=BR/ST=MG/L=Barao de Cocais/O=Prefeitura Municipal de Barao de Cocais/CN=sigtrans.baraodecocais.mg.gov.br" \
  -out sigtrans.csr

# 3) Extensões (SAN) — obrigatório para os navegadores modernos.
printf "subjectAltName=DNS:sigtrans.baraodecocais.mg.gov.br,IP:172.16.64.8\nextendedKeyUsage=serverAuth\n" > sigtrans.ext

# 4) Assina o certificado do site com a CA (validade 10 anos).
openssl x509 -req -in sigtrans.csr -CA prefeitura-ca.crt -CAkey prefeitura-ca.key \
  -CAcreateserial -days 3650 -sha256 -extfile sigtrans.ext -out sigtrans.crt

# 5) Para o IIS: exporta tudo em um arquivo .pfx (defina uma senha quando pedir).
openssl pkcs12 -export -out sigtrans.pfx \
  -inkey sigtrans.key -in sigtrans.crt -certfile prefeitura-ca.crt

# 6) Para o nginx: gera o "fullchain" (site + CA).
cat sigtrans.crt prefeitura-ca.crt > sigtrans-fullchain.crt
```

Você terá em `C:\certs`:
- `prefeitura-ca.crt` → **distribuir nas máquinas** (passo 5).
- `sigtrans.pfx` → usar no **IIS**.
- `sigtrans-fullchain.crt` + `sigtrans.key` → usar no **nginx**.

Guarde `prefeitura-ca.key` em local seguro (é a chave da CA).

---

## 5. Passo 3 — Proxy reverso

### Opção A (recomendada): IIS + URL Rewrite + ARR

O IIS já vem no Windows Server e faz o binding do certificado pela interface.

#### Forma automática (recomendada)

Depois de instalar os dois módulos da Microsoft (passo 2 abaixo), rode:

```
scripts\windows\configurar-iis.bat
```

Ele pede permissão de administrador e faz sozinho: importa o `sigtrans.pfx`,
cria os bindings 80/443, habilita o proxy do ARR, libera o cabeçalho
`X-Forwarded-Proto`, grava o `web.config` e libera o firewall. Ao final, é só
testar `https://sigtrans.baraodecocais.mg.gov.br`.

> O script **não instala** o URL Rewrite nem o ARR (são instaladores próprios da
> Microsoft). Ele detecta se faltam e mostra o link. Instale-os antes (passo 2).

Se preferir fazer manualmente, siga os passos abaixo.

#### Forma manual

1. **Instale o IIS**: Gerenciador do Servidor → Adicionar Funções → *Servidor Web (IIS)*.
2. **Baixe e instale** (uma vez), do site da Microsoft:
   - **URL Rewrite 2.1**
   - **Application Request Routing (ARR) 3.0**
3. Abra o **Gerenciador do IIS** → clique no nó do servidor → **Application
   Request Routing Cache** → *Server Proxy Settings* → marque **Enable proxy** → *Apply*.
4. Importe o certificado: nó do servidor → **Server Certificates** → *Import…* →
   selecione `C:\certs\sigtrans.pfx` e a senha.
5. No site (pode ser o *Default Web Site*) → **Bindings…**:
   - `http`, porta **80**, host `sigtrans.baraodecocais.mg.gov.br`.
   - `https`, porta **443**, host `sigtrans.baraodecocais.mg.gov.br`,
     *SSL certificate* = o certificado importado.
6. **Permitir a variável de proxy**: nó do servidor → **URL Rewrite** →
   *View Server Variables* → **Add** `HTTP_X_FORWARDED_PROTO`.
7. No ARR, mantenha **preserveHostHeader** ligado (Server Proxy Settings →
   *Preserve client IP…* e *Reverse rewrite host in response headers*).
8. Na pasta do site (ex.: `C:\inetpub\wwwroot`), crie/edite o **web.config**:

```xml
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
          <action type="Rewrite" url="http://127.0.0.1:8000/{R:1}" />
        </rule>
      </rules>
    </rewrite>
    <!-- Aumenta o limite de upload, se necessario -->
    <security>
      <requestFiltering>
        <requestLimits maxAllowedContentLength="20971520" />
      </requestFiltering>
    </security>
  </system.webServer>
</configuration>
```

9. Reinicie o site. Pronto: `https://sigtrans.baraodecocais.mg.gov.br` já
   responde, e `http://…` redireciona para `https://…`.

### Opção B (alternativa): nginx para Windows

1. Baixe o nginx para Windows e descompacte em `C:\nginx`.
2. Edite `C:\nginx\conf\nginx.conf`, dentro do bloco `http { … }`:

```nginx
server {
    listen 80;
    server_name sigtrans.baraodecocais.mg.gov.br;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name sigtrans.baraodecocais.mg.gov.br;

    ssl_certificate     C:/certs/sigtrans-fullchain.crt;
    ssl_certificate_key C:/certs/sigtrans.key;

    client_max_body_size 20m;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Real-IP         $remote_addr;
    }
}
```

3. Teste a configuração e inicie:
   ```
   C:\nginx\nginx.exe -t
   C:\nginx\nginx.exe
   ```
   Para rodar como serviço no boot, use o **NSSM** (seção 8).

---

## 6. Passo 4 — Confiar no certificado nas máquinas (tira o aviso)

Como o certificado é da **CA interna da Prefeitura**, cada computador precisa
confiar nessa CA **uma vez**. Depois disso, o cadeado fica verde, sem aviso.

**Em rede com Active Directory (recomendado — faz em todas de uma vez):**
1. Copie `prefeitura-ca.crt` para um local acessível.
2. *Group Policy Management* → edite uma GPO aplicada aos computadores →
   *Configuração do Computador → Políticas → Configurações do Windows →
   Configurações de Segurança → Políticas de Chave Pública → Autoridades de
   Certificação Raiz Confiáveis* → **Importar** → selecione `prefeitura-ca.crt`.
3. Nos PCs, `gpupdate /force` (ou aguardar a atualização da política).

**Sem AD (manual, por máquina):** dê duplo clique em `prefeitura-ca.crt` →
*Instalar Certificado* → *Computador Local* → *Colocar todos… → Autoridades de
Certificação Raiz Confiáveis* → OK.

> **Firefox** usa um repositório próprio: ative
> `security.enterprise_roots.enabled = true` em `about:config`, ou importe a CA
> nas configurações do Firefox.

---

## 7. Passo 5 — Firewall

Libere as portas do site e mantenha a 8000 fechada para fora (o Waitress já
escuta só em 127.0.0.1). No PowerShell (Admin):

```powershell
New-NetFirewallRule -DisplayName "HTTP 80"  -Direction Inbound -Protocol TCP -LocalPort 80  -Action Allow
New-NetFirewallRule -DisplayName "HTTPS 443" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

---

## 8. Rodar como serviço do Windows (NSSM)

Para o SIGTRANS (e o nginx, se usar) subirem sozinhos ao ligar o servidor:

1. Baixe o **NSSM** (nssm.exe).
2. Instale o serviço do app:
   ```
   nssm install SIGTRANS "C:\caminho\SIGTRANS\.venv\Scripts\python.exe" "-m" "waitress" "--listen=127.0.0.1:8000" "config.wsgi:application"
   nssm set SIGTRANS AppDirectory "C:\caminho\SIGTRANS"
   nssm start SIGTRANS
   ```
3. (Se usar nginx) `nssm install nginx "C:\nginx\nginx.exe"` e `nssm start nginx`.

Com o IIS, o proxy já é um serviço nativo do Windows (não precisa de NSSM).

---

## 9. Checklist final de testes

- [ ] `http://127.0.0.1:8000` abre no servidor (Waitress ativo).
- [ ] `nslookup sigtrans.baraodecocais.mg.gov.br` → 172.16.64.8.
- [ ] `http://sigtrans.baraodecocais.mg.gov.br` redireciona para `https://…`.
- [ ] `https://sigtrans.baraodecocais.mg.gov.br` abre a tela de login.
- [ ] Após distribuir a CA, o **cadeado** aparece sem aviso.
- [ ] Login, agenda, senhas, relatórios e o botão **Sair** funcionam.
- [ ] Consegue baixar um backup em *Configurações → Backup*.

---

## 10. Renovação e validade

- O certificado do site e a CA foram criados com **10 anos** de validade — não
  há renovação frequente. Anote a data para renovar antes de expirar.
- Se um dia trocar o certificado, basta gerar um novo `sigtrans.pfx`/`.crt`
  com a **mesma CA** e reimportar no proxy (as máquinas continuam confiando na CA).

---

## 11. Sobre o Let's Encrypt (certificado público automático)

O Let's Encrypt é gratuito e confiável, mas **valida a posse do domínio** de
duas formas, e **nenhuma se aplica neste cenário**:

- **HTTP-01**: exige que o servidor esteja acessível pela **internet** — aqui o
  acesso é só interno (172.16.64.8).
- **DNS-01**: exige criar um registro **TXT** na zona **pública** do domínio —
  aqui o DNS é terceirizado e você não controla os registros.

Por isso o caminho correto e gratuito agora é o **certificado interno** (seções
4 e 6). Ele é tão seguro quanto (mesma criptografia TLS); a única diferença é o
passo único de distribuir a CA nas máquinas.

**Quando o Let's Encrypt passaria a ser possível:**
- Se o setor/empresa que administra o DNS **criar os registros TXT** quando
  solicitado (validação DNS-01, via **win-acme**), ou
- Se, futuramente, houver acesso público controlado.

**Alternativa:** solicitar a quem administra `baraodecocais.mg.gov.br` um
**certificado oficial** já emitido para o subdomínio (muitos órgãos têm cert
wildcard `*.baraodecocais.mg.gov.br`). Se conseguirem o `.pfx`/`.crt`, basta usá-lo
no proxy no lugar do certificado interno — o restante do guia é o mesmo.

---

## 12. Observação de segurança (LGPD)

- Manter o acesso **interno** é a opção mais adequada para dados de saúde.
- O Windows Server 2012 está **fora do suporte** da Microsoft (sem correções de
  segurança). Recomenda-se planejar a migração para uma versão suportada
  (2019/2022) — registre esse ponto no plano de TI.
```
