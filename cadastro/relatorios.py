"""Geração de relatórios (Fase 5): planilhas Excel e PDFs.

- ``planilha_response`` — exporta cabeçalhos + linhas para .xlsx (openpyxl).
- ``ficha_pdf`` — ficha individual de um Núcleo Familiar (reportlab).
- ``classificacao_pdf`` — lista de classificação (reportlab).
"""

from __future__ import annotations

from io import BytesIO

from django.contrib.staticfiles import finders
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_AZUL = colors.HexColor("#1f4e79")

# Caracteres que o Excel/LibreOffice interpretam como início de fórmula.
_GATILHOS_FORMULA = ("=", "+", "-", "@", "\t", "\r", "\n")


def _neutralizar(valor):
    """Evita injeção de fórmula (CSV injection) em células de texto.

    Dados de terceiros (ex.: nome do requerente) podem começar com '=' e virar
    fórmula ativa na planilha. Prefixa um apóstrofo para forçar texto.
    """
    if isinstance(valor, str) and valor.startswith(_GATILHOS_FORMULA):
        return "'" + valor
    return valor


def planilha_response(filename: str, cabecalhos: list[str], linhas) -> HttpResponse:
    wb = Workbook()
    ws = wb.active
    ws.title = "Dados"
    ws.append(cabecalhos)
    for celula in ws[1]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor="1F4E79")
    for linha in linhas:
        ws.append([_neutralizar(v) for v in linha])
    for i, _ in enumerate(cabecalhos, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = 22
    ws.freeze_panes = "A2"

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf.getvalue(), content_type=XLSX_MIME)
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def _pdf_response(nome: str, elementos) -> HttpResponse:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=16 * mm, rightMargin=16 * mm, title=nome,
    )
    doc.build(elementos)
    buf.seek(0)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{nome}"'
    return resp


def _estilo_tabela(cabecalho=True):
    cmds = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d6dce3")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
    ]
    if cabecalho:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    return TableStyle(cmds)


def ficha_pdf(inscricao) -> HttpResponse:
    estilos = getSampleStyleSheet()
    h = estilos["Heading2"]
    h.textColor = _AZUL
    normal = estilos["BodyText"]
    e = []

    e.append(Paragraph("Ficha do Núcleo Familiar — MCMV / Barão de Cocais", estilos["Title"]))
    e.append(Paragraph(
        f"Inscrição <b>{inscricao.numero_inscricao}</b> — situação: "
        f"{inscricao.get_status_display()}", normal))
    e.append(Spacer(1, 6))

    req = inscricao.requerente
    dados = [
        ["Requerente", req.nome],
        ["CPF", req.cpf],
        ["Nascimento", str(req.data_nascimento)],
        ["Contato", f"{inscricao.telefone}  {inscricao.email}"],
        ["Endereço", f"{inscricao.endereco} {inscricao.numero} {inscricao.bairro} {inscricao.cep}"],
    ]
    t = Table(dados, colWidths=[35 * mm, 140 * mm])
    t.setStyle(_estilo_tabela(cabecalho=False))
    e.append(t)

    e.append(Paragraph("Composição do núcleo", h))
    linhas = [["Nome", "Parentesco", "Nascimento", "Arrimo", "PcD"]]
    for m in inscricao.membros.select_related("pessoa"):
        linhas.append([
            m.pessoa.nome, m.get_parentesco_display(), str(m.pessoa.data_nascimento),
            "Sim" if m.arrimo else "—", "Sim" if m.pessoa.pcd else "—",
        ])
    t = Table(linhas, colWidths=[60 * mm, 45 * mm, 30 * mm, 20 * mm, 20 * mm])
    t.setStyle(_estilo_tabela())
    e.append(t)

    e.append(Paragraph("Critérios Legais", h))
    linhas = [["Inciso", "Atendido", "Pontos"]]
    for c in inscricao.criterios_legais.all():
        linhas.append([c.get_inciso_display(), "Sim" if c.atendido else "Não", str(c.pontos)])
    t = Table(linhas, colWidths=[120 * mm, 30 * mm, 25 * mm])
    t.setStyle(_estilo_tabela())
    e.append(t)

    cc = getattr(inscricao, "criterio_complementar", None)
    if cc:
        e.append(Paragraph("Critérios Complementares", h))
        linhas = [
            ["Item", "Apurado", "Pontos"],
            ["Renda per capita", f"R$ {cc.renda_per_capita}", str(cc.pontos_renda)],
            ["Comprometimento aluguel", f"{cc.percentual or '—'}%", str(cc.pontos_aluguel)],
        ]
        t = Table(linhas, colWidths=[100 * mm, 45 * mm, 30 * mm])
        t.setStyle(_estilo_tabela())
        e.append(t)

    e.append(Spacer(1, 8))
    e.append(Paragraph(
        f"<b>CL = {inscricao.pontos_legais or 0} &nbsp; "
        f"CC = {inscricao.pontos_complementares or 0} &nbsp; "
        f"→ &nbsp; P = {inscricao.pontuacao_total or 0} pontos</b> (máx. 190)",
        estilos["Heading3"],
    ))

    # Pendências de cadastro (campos esperados em branco).
    from .wizard import pendencias as _pendencias

    pend = _pendencias(inscricao)
    e.append(Paragraph("Pendências de cadastro", h))
    if pend:
        for item in pend:
            e.append(Paragraph(f"• {item}", normal))
    else:
        e.append(Paragraph("Nenhuma pendência — cadastro completo.", normal))

    return _pdf_response(f"ficha_{inscricao.numero_inscricao}.pdf", e)


def classificacao_pdf(itens) -> HttpResponse:
    estilos = getSampleStyleSheet()
    e = [Paragraph("Classificação Geral — MCMV / Barão de Cocais", estilos["Title"]),
         Spacer(1, 6)]
    linhas = [["Pos.", "Inscrição", "Requerente", "Pontos", "Filhos ≤12", "Idosos", "Empate"]]
    for c in itens:
        linhas.append([
            str(c.posicao or "—"), c.inscricao.numero_inscricao, c.inscricao.requerente.nome,
            str(c.pontuacao), str(c.dependentes_ate_12), str(c.idosos),
            "Sorteio" if c.empate_pendente_sorteio else "—",
        ])
    t = Table(linhas, colWidths=[14 * mm, 26 * mm, 60 * mm, 18 * mm, 22 * mm, 16 * mm, 20 * mm], repeatRows=1)
    t.setStyle(_estilo_tabela())
    e.append(t)
    return _pdf_response("classificacao.pdf", e)


def recibo_pdf(inscricao) -> HttpResponse:
    """Comprovante (recibo) de inscrição para imprimir e entregar ao requerente."""
    estilos = getSampleStyleSheet()
    normal = estilos["BodyText"]
    centro = estilos["Title"]
    e = []

    # Brasão (se disponível nos estáticos).
    caminho_logo = finders.find("img/logo-prefeitura.jpg")
    if caminho_logo:
        img = Image(caminho_logo, width=32 * mm, height=32 * mm)
        img.hAlign = "CENTER"
        e.append(img)

    e.append(Paragraph("Prefeitura Municipal de Barão de Cocais/MG", estilos["Heading3"]))
    e.append(Paragraph("Secretaria Municipal de Assistência Social", normal))
    e.append(Spacer(1, 6))
    e.append(Paragraph("COMPROVANTE DE INSCRIÇÃO", centro))
    e.append(Paragraph(
        "Programa Minha Casa, Minha Vida — Faixa 02 · Edital de Chamamento nº 001/2026",
        normal,
    ))
    e.append(Spacer(1, 10))

    data_fin = inscricao.data_finalizacao
    dados = [
        ["Protocolo", inscricao.protocolo or "—"],
        ["Nº da inscrição", inscricao.numero_inscricao],
        ["Data/hora", data_fin.strftime("%d/%m/%Y %H:%M") if data_fin else "—"],
        ["Requerente", inscricao.requerente.nome],
        ["CPF", inscricao.requerente.cpf],
        ["Nº de integrantes do núcleo", str(inscricao.membros.count())],
        ["Situação", inscricao.get_status_display()],
    ]
    t = Table(dados, colWidths=[55 * mm, 120 * mm])
    t.setStyle(_estilo_tabela(cabecalho=False))
    e.append(t)

    e.append(Spacer(1, 12))
    e.append(Paragraph(
        "Declaramos, para os devidos fins, que a inscrição acima foi recebida nesta data. "
        "A inscrição e a eventual classificação <b>não geram direito</b> à contratação, ao "
        "financiamento ou à aquisição de unidade habitacional, que dependem de análise "
        "posterior da instituição financeira responsável, nos termos do Edital 001/2026.",
        normal,
    ))
    e.append(Paragraph(
        "É de responsabilidade exclusiva do candidato o acompanhamento das publicações "
        "oficiais referentes a este Edital.",
        normal,
    ))

    e.append(Spacer(1, 26))
    assinaturas = [
        ["_______________________________", "_______________________________"],
        ["Servidor responsável", "Requerente"],
    ]
    ta = Table(assinaturas, colWidths=[87 * mm, 87 * mm])
    ta.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
    ]))
    e.append(ta)

    e.append(Spacer(1, 16))
    rodape = estilos["Normal"]
    rodape.fontSize = 7.5
    rodape.textColor = colors.HexColor("#5a6672")
    e.append(Paragraph(
        "Departamento de Informática e Tecnologia — Prefeitura Municipal de Barão de "
        "Cocais/MG · Responsável: Aristides Ferreira Junior · Contato: (31) 3837-7661",
        rodape,
    ))
    return _pdf_response(f"recibo_{inscricao.protocolo or inscricao.numero_inscricao}.pdf", e)
