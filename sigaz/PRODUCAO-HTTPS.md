# Guia de HTTPS / Acesso Externo

O SIGAZ por padrão roda em **HTTP na porta 3000**, o que é suficiente para uso interno na rede da prefeitura. Para expor o sistema na internet (ex: para cidadãos acessarem a consulta pública e o portal), siga este guia.

## 🎯 Opções recomendadas

### Opção 1 — Proxy reverso com Nginx (recomendada)

Coloca o Nginx na frente do SIGAZ e ele cuida do HTTPS.

**Vantagens:**
- Padrão de mercado
- Funciona bem com Let's Encrypt (HTTPS gratuito automático)
- Permite expor mais de um serviço no mesmo servidor

**Pré-requisito:** servidor Linux acessível pela internet com domínio (ex: `sigaz.bcocais.mg.gov.br`).

**Resumo da configuração** (arquivo `/etc/nginx/sites-available/sigaz`):

```nginx
server {
    listen 80;
    server_name sigaz.bcocais.mg.gov.br;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name sigaz.bcocais.mg.gov.br;

    # Certificados gerados pelo certbot
    ssl_certificate /etc/letsencrypt/live/sigaz.bcocais.mg.gov.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sigaz.bcocais.mg.gov.br/privkey.pem;

    # Hardening básico
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    client_max_body_size 200M;  # Para uploads de banco no restore

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Instalar certificado HTTPS gratuito (Let's Encrypt):**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d sigaz.bcocais.mg.gov.br
```

O certbot renova o certificado sozinho a cada 60 dias.

---

### Opção 2 — IIS como proxy reverso (Windows)

Se o servidor é Windows Server e já tem IIS:

1. Instale o módulo **URL Rewrite** e **Application Request Routing (ARR)** no IIS
2. Crie um site no IIS apontando para `sigaz.bcocais.mg.gov.br`
3. Configure a regra de rewrite para `http://localhost:3000`
4. Habilite o certificado SSL no Bindings do IIS

Procure por "IIS reverse proxy node.js" no Google para o passo a passo detalhado.

---

### Opção 3 — Cloudflare Tunnel (mais simples)

Se você não quer mexer em firewall, DNS público, etc:

1. Crie uma conta gratuita no Cloudflare
2. Instale o `cloudflared` na máquina onde o SIGAZ está rodando
3. Configure um Tunnel apontando para `http://localhost:3000`
4. O Cloudflare cuida do HTTPS automaticamente

Mais info: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

---

## 🛡️ Recomendações de segurança em produção

1. **Trocar o JWT_SECRET** no arquivo `.env` por uma string aleatória longa:
   ```
   JWT_SECRET=cole-aqui-uma-string-de-pelo-menos-64-caracteres-totalmente-aleatoria-xyz123
   ```

2. **Firewall**: a porta 3000 não deve ser exposta diretamente. Só o Nginx (80/443) fica público.

3. **Backup automático para fora do servidor**: use a tarefa do Windows ou cron pra copiar a pasta `backend/backups/` para um drive de rede / nuvem (Google Drive, OneDrive, etc).

4. **Usuários reais**: assim que o sistema entrar em produção, **delete os usuários `admin` e `veterinario` demo** ou troque suas senhas pelos botões "Resetar Senha".

5. **Pasta de backups**: garanta que ela esteja em um disco com bastante espaço. Cada backup do SIGAZ tem ~150 KB no início, mas cresce com o tempo.

6. **Atualizações do Node.js**: mantenha o Node em uma versão LTS atualizada (22 ou superior).

---

## 📞 Suporte

Departamento de Informática e Tecnologia
Prefeitura Municipal de Barão de Cocais — MG
📞 (31) 3837-7661
