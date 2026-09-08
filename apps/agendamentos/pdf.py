"""Geração do Cartão de Embarque em PDF (modelo da Prefeitura)."""
from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

NAVY = HexColor("#16386e")
INK = HexColor("#1c2733")
MUTED = HexColor("#5b6b7b")
LINE = HexColor("#c9d3e0")

TELEFONES = "3837-7642  |  3837-5530"


def _logo_path():
    rel = settings.ORGAO.get("LOGO", "img/logo-prefeitura.jpg")
    p = Path(settings.BASE_DIR) / "static" / rel
    return str(p) if p.exists() else None


def gerar_cartao_embarque(agendamento):
    """Retorna os bytes de um PDF A4 com o cartão de embarque."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    margem = 18 * mm
    card_x = margem
    card_w = largura - 2 * margem
    card_top = altura - 24 * mm
    card_h = 150 * mm
    card_bottom = card_top - card_h

    # Moldura do cartão
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.roundRect(card_x, card_bottom, card_w, card_h, 8, stroke=1, fill=0)

    pad = 10 * mm
    x = card_x + pad
    y = card_top - pad

    # Cabeçalho: logo + título
    logo = _logo_path()
    if logo:
        try:
            c.drawImage(logo, x, y - 22 * mm, width=22 * mm, height=22 * mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(x + 26 * mm, y - 9 * mm, "CARTÃO DE EMBARQUE")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(x + 26 * mm, y - 15 * mm, settings.ORGAO["PREFEITURA"])
    c.drawString(x + 26 * mm, y - 20 * mm, f"Nº {agendamento.numero}")

    y -= 30 * mm

    def campo(rotulo, valor, largura_campo=None):
        nonlocal y
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x, y, rotulo.upper())
        c.setFillColor(INK)
        c.setFont("Helvetica", 12)
        c.drawString(x, y - 6 * mm, valor or "—")
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        fim = x + (largura_campo or (card_w - 2 * pad))
        c.line(x, y - 8 * mm, fim, y - 8 * mm)
        y -= 15 * mm

    p = agendamento
    campo("Paciente", p.paciente.nome)
    campo("Acompanhante", p.acompanhante)

    # Data e horário lado a lado
    c.setFillColor(MUTED); c.setFont("Helvetica-Bold", 8)
    c.drawString(x, y, "DATA")
    c.drawString(x + 70 * mm, y, "HORÁRIO DA CONSULTA")
    c.setFillColor(INK); c.setFont("Helvetica", 12)
    c.drawString(x, y - 6 * mm, f"{p.data:%d/%m/%Y}")
    c.drawString(x + 70 * mm, y - 6 * mm, f"{p.horario:%H:%M}")
    c.setStrokeColor(LINE); c.setLineWidth(0.6)
    c.line(x, y - 8 * mm, x + 60 * mm, y - 8 * mm)
    c.line(x + 70 * mm, y - 8 * mm, x + card_w - 2 * pad, y - 8 * mm)
    y -= 15 * mm

    campo("Local da consulta", p.local_consulta or str(p.destino))
    campo("Local de saída (embarque)", p.local_embarque)

    # Texto fixo de orientação
    y -= 2 * mm
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(largura / 2, y, "Prezado(a) paciente,")
    y -= 6 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica", 9.5)
    linhas = [
        "Solicitamos que entre em contato com a Secretaria de Saúde para confirmar o",
        "horário de saída do transporte no dia anterior à sua consulta, das 10h às 13h.",
    ]
    for ln in linhas:
        c.drawCentredString(largura / 2, y, ln)
        y -= 5 * mm
    y -= 1 * mm
    c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(largura / 2, y, f"Telefones: {TELEFONES}")
    y -= 6 * mm
    c.setFillColor(MUTED); c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(
        largura / 2, y,
        "Importante: caso não precise do transporte, avise com antecedência.",
    )

    # Rodapé
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(
        largura / 2, card_bottom - 6 * mm,
        f"{settings.ORGAO['SISTEMA_NOME']} · {settings.ORGAO['SECRETARIA']} · "
        f"Emitido em {p.criado_em:%d/%m/%Y}" if p.criado_em else settings.ORGAO["SISTEMA_NOME"],
    )

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
