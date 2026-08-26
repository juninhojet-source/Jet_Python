"""Gera um certificado TLS autoassinado DECENTE para o Sistema MCMV.

Ao contrario do New-SelfSignedCertificate do Windows 2012 R2 (que gera SHA-1 e
nao poe o IP como IP SAN), este script gera:
  - SHA-256, RSA 2048;
  - SubjectAltName com os nomes DNS **e** os IPs corretos (o Chrome exige SAN,
    e para acessar por IP exige o IP como iPAddress, nao como DNS);
  - ExtendedKeyUsage = serverAuth; validade de ~2 anos.

Saidas:
  - um .pfx (certificado + chave, com senha) para o IIS importar/vincular;
  - um .cer (certificado publico) para instalar nos clientes (Autoridades de
    Certificacao Raiz Confiaveis) e sumir com o aviso "Nao seguro".

Uso (com o virtualenv ativo; requer o pacote 'cryptography'):
    python scripts\\windows\\gerar_certificado.py ^
        --hostname mcmv.baraodecocais.mg.gov.br --ip 172.16.64.9 ^
        --senha mcmv123 --saida C:\\mcmv

Depois, vincule no IIS e reinicie o servico:
    powershell -ExecutionPolicy Bypass -File deploy\\windows\\iis\\configurar-https.ps1 ^
        -ProjetoDir C:\\mcmv\\Jet_Python -Pfx C:\\mcmv\\mcmv.pfx -SenhaPfx mcmv123
    net stop MCMV ^& net start MCMV
"""

from __future__ import annotations

import argparse
import datetime
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


def _san(hostnames: list[str], ips: list[str]) -> x509.SubjectAlternativeName:
    entradas: list[x509.GeneralName] = [x509.DNSName(h) for h in hostnames]
    for ip in ips:
        entradas.append(x509.IPAddress(ipaddress.ip_address(ip)))
    return x509.SubjectAlternativeName(entradas)


def main() -> int:
    p = argparse.ArgumentParser(description="Gera certificado TLS autoassinado (SHA-256, com SAN).")
    p.add_argument("--hostname", default="mcmv.baraodecocais.mg.gov.br")
    p.add_argument("--ip", action="append", default=[], help="IP no SAN (pode repetir)")
    p.add_argument("--dias", type=int, default=730)
    p.add_argument("--senha", default="mcmv", help="senha do .pfx")
    p.add_argument("--saida", default=".", help="pasta de saida")
    p.add_argument("--nome", default="mcmv", help="prefixo dos arquivos (.pfx/.cer)")
    args = p.parse_args()

    hostnames = [args.hostname, "localhost"]
    ips = list(dict.fromkeys(args.ip + ["127.0.0.1"]))  # remove duplicatas, garante loopback
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, args.hostname)])
    agora = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - datetime.timedelta(days=1))
        .not_valid_after(agora + datetime.timedelta(days=args.dias))
        .add_extension(_san(hostnames, ips), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_encipherment=True, content_commitment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .sign(chave, hashes.SHA256())
    )

    pfx = saida / f"{args.nome}.pfx"
    cer = saida / f"{args.nome}-cert.cer"
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=args.hostname.encode(),
        key=chave,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(args.senha.encode()),
    )
    pfx.write_bytes(pfx_bytes)
    cer.write_bytes(cert.public_bytes(serialization.Encoding.DER))

    print(f"Certificado gerado (SHA-256, valido {args.dias} dias).")
    print(f"  DNS no SAN: {', '.join(hostnames)}")
    print(f"  IP  no SAN: {', '.join(ips)}")
    print(f"  PFX (para o IIS):     {pfx}")
    print(f"  CER (para clientes):  {cer}")
    print(f"  Senha do PFX:         {args.senha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
