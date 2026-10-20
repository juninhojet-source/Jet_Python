"""Corrige o .env: remove BOM e garante uma DJANGO_SECRET_KEY forte.

Uso (com o virtualenv ativo, na raiz do projeto):

    python scripts\\windows\\definir_secret.py

- Le o .env tolerando BOM (utf-8-sig) e o regrava em UTF-8 SEM BOM (evita que o
  BOM "cole" no nome da 1a variavel e ela deixe de ser lida).
- Se DJANGO_SECRET_KEY estiver ausente ou fraca (curta/placeholder), gera uma
  chave nova e forte. Para forcar a troca mesmo com chave valida, use --forcar.
- Preserva todas as demais linhas e comentarios do .env.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV = BASE_DIR / ".env"
CHAVE = "DJANGO_SECRET_KEY"


def _fraca(valor: str) -> bool:
    v = valor.strip().strip('"').strip("'")
    return (
        len(v) < 50
        or len(set(v)) < 5
        or v.startswith("django-insecure-")
        or "dev-inseguro" in v
    )


def main() -> int:
    forcar = "--forcar" in sys.argv
    if not ENV.exists():
        print(f"[ERRO] .env nao encontrado em {ENV}")
        return 1

    # utf-8-sig remove um eventual BOM no inicio do arquivo.
    linhas = ENV.read_text(encoding="utf-8-sig").splitlines()

    idx = next(
        (i for i, ln in enumerate(linhas) if ln.lstrip().startswith(f"{CHAVE}=")),
        None,
    )
    atual = linhas[idx].split("=", 1)[1] if idx is not None else ""

    if idx is None or _fraca(atual) or forcar:
        nova = get_random_secret_key()
        linha = f"{CHAVE}={nova}"
        if idx is None:
            linhas.append(linha)
            print(f"{CHAVE} ausente -> gerada uma chave nova e forte.")
        else:
            linhas[idx] = linha
            print(f"{CHAVE} fraca/forcada -> substituida por uma chave nova e forte.")
    else:
        print(f"{CHAVE} ja e forte; mantida. (use --forcar para trocar mesmo assim)")

    # Regrava SEM BOM, com quebras de linha \n.
    ENV.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f".env regravado sem BOM em {ENV}")
    return 0


if __name__ == "__main__":
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    # get_random_secret_key nao exige settings configurado, mas garantimos o import.
    raise SystemExit(main())
