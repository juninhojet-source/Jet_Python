"""Mapa de Viagem (Garagem).

Gera o mapa diário de viagens no mesmo formato usado pela Garagem: os
agendamentos do dia agrupados por veículo, com embarque, destino, local e
horário de saída, além da legenda de conferência (N/P/D/R).

O agrupamento usa o campo "Tipo de veículo" do agendamento (preenchimento
livre — ex.: "CARRO 1", "AMBULÂNCIA 2", "MICRO ITABIRA"). Agendamentos sem
veículo definido ficam no grupo "A DEFINIR", ao final.
"""
import re
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

NAVY = "16386E"
GOLD = "F2C230"
CINZA = "F2F6FC"

SEM_VEICULO = "A DEFINIR"

LEGENDA = [
    "N = não compareceu",
    "P = presente",
    "D = desceu do veículo",
    "R = retornou ao veículo",
]

COLUNAS = [
    "Veículo", "Nome do paciente", "Telefone", "Horário",
    "Embarque", "Destino", "Local", "Horário saída", "CPF",
]

# Posições (1-based) das colunas com tratamento especial.
COL_VEICULO = 1   # mesclada por grupo de veículo
COL_SAIDA = 8     # mesclada por grupo (horário de saída da garagem)
COL_CPF = 9       # por linha, sempre a última


def _cpf(valor):
    """Formata CPF (11 dígitos) como NNN.NNN.NNN-NN. Aceita vazio/None."""
    d = re.sub(r"\D", "", valor or "")
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return valor or ""

# Caracteres que iniciam uma fórmula no Excel/LibreOffice.
_GATILHOS_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def _sanitizar(valor):
    if isinstance(valor, str) and valor[:1] in _GATILHOS_FORMULA:
        return "'" + valor
    return valor


def _hhmm(t):
    return t.strftime("%H:%M") if t else ""


def _natural_key(texto):
    """Ordena de forma natural: CARRO 2 antes de CARRO 10."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", texto)]


def _local_destino(destino):
    partes = [destino.nome]
    if destino.endereco:
        partes.append(destino.endereco)
    return " — ".join(partes)


def agrupar_por_veiculo(qs):
    """Agrupa um queryset de agendamentos por veículo, pronto para render.

    Retorna uma lista de grupos, cada um com:
        {"veiculo": str, "saida": time|None, "linhas": [ {..paciente..}, {..AC..} ]}
    """
    grupos = {}
    for a in qs:
        if a.veiculo_id:
            chave = a.veiculo.nome
        else:
            chave = (a.tipo_veiculo or "").strip() or SEM_VEICULO
        grupo = grupos.setdefault(chave, {"veiculo": chave, "saida": None, "linhas": []})

        # Horário de saída da garagem = embarque mais cedo do grupo.
        if a.hora_embarque and (grupo["saida"] is None or a.hora_embarque < grupo["saida"]):
            grupo["saida"] = a.hora_embarque

        grupo["linhas"].append({
            "nome": a.paciente.nome,
            "cpf": _cpf(a.paciente.cpf),
            "telefone": a.contato or a.paciente.telefone_principal or "",
            "horario": _hhmm(a.horario),
            # Ponto de embarque: usa o local informado no agendamento e, se
            # estiver vazio, cai no endereço cadastrado do paciente.
            "embarque": a.local_embarque or a.paciente.endereco_resumido or "",
            "destino": a.destino.municipio.nome if a.destino.municipio_id else "",
            "local": _local_destino(a.destino),
            "ac": False,
        })
        if a.acompanhante.strip():
            grupo["linhas"].append({
                "nome": f"AC. {a.acompanhante.strip()}",
                "cpf": _cpf(getattr(a, "acompanhante_cpf", "")),
                "telefone": "", "horario": "", "embarque": "",
                "destino": "", "local": "", "ac": True,
            })

    reais = sorted(
        (g for k, g in grupos.items() if k != SEM_VEICULO),
        key=lambda g: _natural_key(g["veiculo"]),
    )
    if SEM_VEICULO in grupos:
        reais.append(grupos[SEM_VEICULO])
    return reais


# --------------------------------------------------------------------- Excel
def gerar_mapa_xlsx(dia, grupos, motorista=""):
    """Mapa de um único dia (uma aba)."""
    return gerar_mapa_xlsx_periodo([(dia, grupos)], motorista)


def gerar_mapa_xlsx_periodo(dias, motorista=""):
    """Mapa de um ou mais dias: uma aba por dia, cada uma no modelo da Garagem.

    `dias` é uma lista de (data, grupos).
    """
    wb = Workbook()
    varios = len(dias) > 1
    for i, (dia, grupos) in enumerate(dias):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = f"{dia:%d-%m-%Y}" if varios else "Mapa de Viagem"
        _preencher_planilha(ws, dia, grupos, motorista)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _preencher_planilha(ws, dia, grupos, motorista):
    n_cols = len(COLUNAS)
    ult = get_column_letter(n_cols)
    fina = Side(style="thin", color="B7C3D6")
    borda = Border(left=fina, right=fina, top=fina, bottom=fina)
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)
    esq = Alignment(horizontal="left", vertical="center", wrap_text=True)

    def fundir(c1, c2):
        ws.merge_cells(f"{c1}:{c2}")

    # Cabeçalho institucional
    fundir(f"A1", f"{ult}1")
    ws["A1"] = settings.ORGAO["SECRETARIA"] + " de " + "Barão de Cocais"
    ws["A1"].font = Font(name="Arial", bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
    ws["A1"].alignment = centro
    ws.row_dimensions[1].height = 26

    fundir(f"A2", f"{ult}2")
    ws["A2"] = "Agendamentos de transporte — GARAGEM"
    ws["A2"].font = Font(name="Arial", bold=True, size=11, color=NAVY)
    ws["A2"].fill = PatternFill("solid", fgColor=GOLD)
    ws["A2"].alignment = centro
    ws.row_dimensions[2].height = 20

    # Linha DATA / MOTORISTA
    ws["A4"] = "DATA:"
    ws["A4"].font = Font(name="Arial", bold=True)
    ws["B4"] = dia.strftime("%d/%m/%Y")
    ws["B4"].font = Font(name="Arial")
    ws["E4"] = "MOTORISTA:"
    ws["E4"].font = Font(name="Arial", bold=True)
    fundir("F4", ult + "4")
    ws["F4"] = motorista
    ws["F4"].font = Font(name="Arial")

    # Cabeçalho da tabela
    linha_cab = 6
    for c, nome in enumerate(COLUNAS, start=1):
        cel = ws.cell(row=linha_cab, column=c, value=nome)
        cel.font = Font(name="Arial", bold=True, color="FFFFFF")
        cel.fill = PatternFill("solid", fgColor=NAVY)
        cel.alignment = centro
        cel.border = borda
    ws.row_dimensions[linha_cab].height = 22

    # Colunas mescladas por grupo (veículo e saída) e colunas de dados por linha.
    saida_col = get_column_letter(COL_SAIDA)
    cols_dados = [c for c in range(2, n_cols + 1) if c not in (COL_VEICULO, COL_SAIDA)]

    # Dados agrupados por veículo
    r = linha_cab + 1
    for gi, grupo in enumerate(grupos):
        inicio = r
        for linha in grupo["linhas"]:
            valores = [
                "",  # 1 (veículo) — mesclado ao final do grupo
                linha["nome"], linha["telefone"], linha["horario"],
                linha["embarque"], linha["destino"], linha["local"],
                "",  # 8 (saída) — mesclado ao final do grupo
                linha["cpf"],  # 9 (CPF) — sempre a última coluna
            ]
            for c, v in enumerate(valores, start=1):
                cel = ws.cell(row=r, column=c, value=_sanitizar(v))
                cel.border = borda
                cel.alignment = esq if c in (2, 5, 7) else centro
                fonte_kwargs = {"name": "Arial", "size": 10}
                if linha["ac"]:
                    fonte_kwargs.update(italic=True, color="5B6B7B")
                cel.font = Font(**fonte_kwargs)
            if gi % 2 == 1:
                for c in cols_dados:  # não pinta veículo/saída (mesclados)
                    ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=CINZA)
            r += 1
        fim = r - 1
        if fim < inicio:
            continue
        # Veículo (coluna A) e Saída (coluna H) mesclados no bloco do grupo
        if fim > inicio:
            fundir(f"A{inicio}", f"A{fim}")
            fundir(f"{saida_col}{inicio}", f"{saida_col}{fim}")
        ws[f"A{inicio}"] = grupo["veiculo"]
        ws[f"A{inicio}"].font = Font(name="Arial", bold=True, size=10, color=NAVY)
        ws[f"A{inicio}"].alignment = centro
        ws[f"{saida_col}{inicio}"] = _hhmm(grupo["saida"])
        ws[f"{saida_col}{inicio}"].font = Font(name="Arial", bold=True, size=11, color="B02A24")
        ws[f"{saida_col}{inicio}"].alignment = centro
        for rr in range(inicio, fim + 1):
            ws[f"A{rr}"].border = borda
            ws[f"{saida_col}{rr}"].border = borda

    if not grupos:
        fundir(f"A{r}", f"{ult}{r}")
        ws.cell(row=r, column=1, value="Nenhum agendamento para a data selecionada.").alignment = centro
        r += 1

    # Legenda
    r += 1
    ws.cell(row=r, column=1, value="Legenda:").font = Font(name="Arial", bold=True)
    for texto in LEGENDA:
        r += 1
        ws.cell(row=r, column=1, value=texto).font = Font(name="Arial", size=9, color="5B6B7B")

    # Larguras
    larguras = {1: 15, 2: 32, 3: 14, 4: 9, 5: 32, 6: 13, 7: 38, 8: 10, 9: 16}
    for c, w in larguras.items():
        ws.column_dimensions[get_column_letter(c)].width = w

    ws.freeze_panes = f"A{linha_cab + 1}"

    # Impressão em paisagem, ajustado à largura da página
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"1:{linha_cab}"


# ----------------------------------------------------------------------- PDF
# Máximo de linhas por bloco mesclado no PDF. Um bloco mesclado (célula do
# veículo/saída) não pode ser quebrado entre páginas; grupos maiores que isso
# são divididos em blocos, repetindo o veículo com "(cont.)".
BLOCO_PDF = 15


def _blocos(linhas, tamanho=BLOCO_PDF):
    """Divide as linhas de um grupo em blocos de até `tamanho` linhas.

    Nunca separa o acompanhante (linha "ac") do seu paciente: só corta antes
    de uma linha de paciente.
    """
    blocos, atual = [], []
    for lin in linhas:
        if atual and not lin["ac"] and len(atual) >= tamanho - 1:
            blocos.append(atual)
            atual = []
        atual.append(lin)
    if atual:
        blocos.append(atual)
    return blocos


def _p(texto, estilo):
    """Paragraph com o texto escapado (evita erro com &, < e > nos dados)."""
    return Paragraph(escape(str(texto or "")), estilo)


def _estilos_pdf():
    estilos = getSampleStyleSheet()
    cel = ParagraphStyle("cel", parent=estilos["Normal"], fontSize=7.5, leading=9)
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=estilos["Title"], fontSize=14,
            textColor=colors.HexColor("#" + NAVY), spaceAfter=2,
        ),
        "sub": ParagraphStyle("sub", parent=estilos["Normal"], fontSize=9,
                              textColor=colors.HexColor("#5b6b7b")),
        "cel": cel,
        "cel_ac": ParagraphStyle("celac", parent=cel, textColor=colors.HexColor("#5b6b7b"),
                                 fontName="Helvetica-Oblique"),
    }


def gerar_mapa_pdf(dia, grupos, motorista=""):
    """Mapa de um único dia."""
    return gerar_mapa_pdf_periodo([(dia, grupos)], motorista)


def gerar_mapa_pdf_periodo(dias, motorista=""):
    """Mapa de um ou mais dias: cada dia começa em uma página nova."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
        title="Mapa de Viagem",
    )
    st = _estilos_pdf()
    elementos = []
    for i, (dia, grupos) in enumerate(dias):
        if i:
            elementos.append(PageBreak())
        elementos += _elementos_dia(dia, grupos, motorista, st)
    doc.build(elementos)
    return buf.getvalue()


def _elementos_dia(dia, grupos, motorista, st):
    cel, cel_ac, sub = st["cel"], st["cel_ac"], st["sub"]
    elementos = [
        Paragraph(settings.ORGAO["SECRETARIA"] + " de Barão de Cocais", st["titulo"]),
        Paragraph("Agendamentos de transporte — GARAGEM", sub),
        Paragraph(
            f"<b>DATA:</b> {dia:%d/%m/%Y} &nbsp;&nbsp; <b>MOTORISTA:</b> "
            f"{escape(motorista) if motorista else '________________'}", sub,
        ),
        Spacer(1, 8),
    ]

    dados = [[Paragraph(f"<b>{c}</b>", cel) for c in COLUNAS]]
    estilo_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#" + NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b7c3d6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]

    linha_atual = 1
    for grupo in grupos:
        for bi, bloco in enumerate(_blocos(grupo["linhas"])):
            inicio = linha_atual
            for lin in bloco:
                est = cel_ac if lin["ac"] else cel
                dados.append([
                    Paragraph("", cel),  # veículo — preenchido via SPAN
                    _p(lin["nome"], est), _p(lin["telefone"], est),
                    _p(lin["horario"], est), _p(lin["embarque"], est),
                    _p(lin["destino"], est), _p(lin["local"], est),
                    Paragraph("", cel),  # saída — preenchido via SPAN
                    _p(lin["cpf"], est),  # CPF — sempre a última coluna
                ])
                linha_atual += 1
            fim = linha_atual - 1
            nome_veiculo = escape(grupo["veiculo"]) + (" (cont.)" if bi else "")
            dados[inicio][0] = Paragraph(f"<b>{nome_veiculo}</b>", cel)
            dados[inicio][7] = Paragraph(f"<b>{_hhmm(grupo['saida'])}</b>", cel)
            estilo_cmds += [
                ("SPAN", (0, inicio), (0, fim)),
                ("SPAN", (7, inicio), (7, fim)),
            ]
            if bi == 0:
                estilo_cmds.append(
                    ("LINEABOVE", (0, inicio), (-1, inicio), 0.8, colors.HexColor("#" + NAVY))
                )

    if not grupos:
        dados.append([Paragraph("Nenhum agendamento para a data selecionada.", cel)] + [""] * (len(COLUNAS) - 1))
        estilo_cmds.append(("SPAN", (0, 1), (-1, 1)))

    larguras = [52, 132, 58, 34, 128, 52, 148, 40, 74]
    tabela = Table(dados, repeatRows=1, colWidths=larguras)
    tabela.setStyle(TableStyle(estilo_cmds))
    elementos.append(tabela)

    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph("<b>Legenda:</b> " + " · ".join(LEGENDA), sub))
    return elementos
