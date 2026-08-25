"""Armazenamento de estáticos do WhiteNoise, tolerante a manifesto incompleto.

Com ``manifest_strict = False``, um arquivo estático referenciado que não esteja
no manifesto (ex.: esqueceram de rodar collectstatic após uma atualização) não
derruba a página com erro 500 — cai para o nome sem hash em vez de levantar
exceção.
"""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class StaticStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False
