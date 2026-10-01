"""Testes dos relatórios (agendamentos, BPA, indicadores e exportação)."""
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.agendamentos.models import Agendamento, StatusAgendamento
from apps.core.models import Municipio
from apps.destinos.models import Destino
from apps.pacientes.models import Paciente

from .filtros import filtrar

User = get_user_model()


def proxima_sexta(base=None):
    d = base or date.today()
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


class BaseDados(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="c", password="x", perfil="CONSULTA")
        self.mun = Municipio.objects.create(codigo_ibge="3131307", nome="Itabira")
        self.pac = Paciente.objects.create(
            nome="Maria", cpf="52998224725", data_nascimento=date(1970, 1, 1),
            sexo="F", telefone_principal="31999990000", municipio=self.mun, raca_cor="03",
        )
        self.dst = Destino.objects.create(nome="Hospital X", municipio=self.mun)
        self.dia = proxima_sexta()
        self.ag = Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(7, 0),
            procedimento="Cardiologia", status=StatusAgendamento.FINALIZADO,
        )
        Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(8, 0),
            status=StatusAgendamento.CANCELADO,
        )


class FiltroTest(BaseDados):
    def test_filtra_por_dia(self):
        qs, resumo = filtrar({"dia": self.dia.strftime("%Y-%m-%d")}, incluir_cancelados=True)
        self.assertEqual(qs.count(), 2)

    def test_exclui_cancelados_por_padrao(self):
        qs, _ = filtrar({}, incluir_cancelados=False)
        self.assertEqual(qs.count(), 1)

    def test_filtra_por_horario(self):
        # BaseDados tem um agendamento as 07:00 e outro (cancelado) as 08:00.
        qs, _ = filtrar({"hora_inicio": "07:00", "hora_fim": "07:30"}, incluir_cancelados=True)
        self.assertEqual(qs.count(), 1)
        qs2, _ = filtrar({"hora_inicio": "07:30"}, incluir_cancelados=True)
        self.assertEqual(qs2.count(), 1)  # so o das 08:00
        qs3, _ = filtrar({"hora_fim": "06:59"}, incluir_cancelados=True)
        self.assertEqual(qs3.count(), 0)

    def test_filtra_por_nome_e_procedimento(self):
        qs, _ = filtrar({"q": "mar", "procedimento": "cardio"}, incluir_cancelados=True)
        self.assertEqual(qs.count(), 1)

    def test_filtra_por_cidade_destino(self):
        outra = Municipio.objects.create(codigo_ibge="3106200", nome="Belo Horizonte")
        dst_bh = Destino.objects.create(nome="Hospital BH", municipio=outra)
        Agendamento.objects.create(
            paciente=self.pac, destino=dst_bh, data=self.dia, horario=time(9, 0),
        )
        qs, resumo = filtrar({"municipio": str(outra.id)}, incluir_cancelados=True)
        self.assertEqual(qs.count(), 1)
        self.assertTrue(any(k == "Cidade" and "Belo Horizonte" in v for k, v in resumo))

    def test_filtra_por_veiculo_fk_e_texto(self):
        from apps.veiculos.models import Veiculo
        v = Veiculo.objects.create(nome="CARRO 1", tipo="UTILITARIO")
        # Um agendamento ligado pelo cadastro (FK)...
        Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(9, 0),
            veiculo=v,
        )
        # ...e outro que guarda o nome do veiculo apenas no texto.
        Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(9, 30),
            tipo_veiculo="carro 1",
        )
        qs, resumo = filtrar({"veiculo": str(v.id)}, incluir_cancelados=True)
        self.assertEqual(qs.count(), 2)
        self.assertIn(("Veículo", "CARRO 1"), resumo)


class ViewsTest(BaseDados):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_paginas_carregam(self):
        for nome in ["index", "agendamentos", "bpa", "indicadores"]:
            self.assertEqual(self.client.get(reverse(f"relatorios:{nome}")).status_code, 200)

    def test_exige_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("relatorios:agendamentos")).status_code, 302)

    def test_export_xlsx(self):
        r = self.client.get(reverse("relatorios:agendamentos"), {"export": "xlsx"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheet", r["Content-Type"])
        self.assertEqual(r.content[:2], b"PK")  # xlsx é um zip

    def test_export_pdf_bpa(self):
        r = self.client.get(reverse("relatorios:bpa"), {"export": "pdf", "mes": self.dia.strftime("%Y-%m")})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))


class MapaViagemTest(TestCase):
    """Mapa de Viagem: agrupamento por veículo e exportação."""

    def setUp(self):
        self.user = User.objects.create_user(username="c", password="x", perfil="CONSULTA")
        self.mun = Municipio.objects.create(codigo_ibge="3106200", nome="Belo Horizonte")
        self.pac = Paciente.objects.create(
            nome="José Silva", cpf="52998224725", data_nascimento=date(1960, 1, 1),
            sexo="M", telefone_principal="31988887777", municipio=self.mun, raca_cor="01",
        )
        self.pac2 = Paciente.objects.create(
            nome="Ana Souza", cns="700000000000000", data_nascimento=date(1975, 2, 2),
            sexo="F", telefone_principal="31977776666", municipio=self.mun, raca_cor="03",
        )
        self.dst = Destino.objects.create(
            nome="Hospital das Clínicas", municipio=self.mun, endereco="Av. Alfredo Balena 190",
        )
        self.dia = proxima_sexta()
        # CARRO 10 e CARRO 2 para checar ordenação natural (2 antes de 10).
        Agendamento.objects.create(
            paciente=self.pac2, destino=self.dst, data=self.dia, horario=time(9, 0),
            tipo_veiculo="CARRO 10", local_embarque="Rua A 100", hora_embarque=time(6, 30),
        )
        self.ag = Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(8, 0),
            tipo_veiculo="CARRO 2", local_embarque="Rua B 200", hora_embarque=time(5, 0),
            acompanhante="Maria Acompanhante",
        )
        # Sem veículo → grupo "A DEFINIR", ao final.
        Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(10, 0),
        )
        # Cancelado não entra no mapa.
        Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(11, 0),
            tipo_veiculo="CARRO 2", status=StatusAgendamento.CANCELADO,
        )

    def _grupos(self):
        from .mapa import agrupar_por_veiculo
        qs = (
            Agendamento.objects.filter(data=self.dia)
            .exclude(status=StatusAgendamento.CANCELADO)
            .select_related("paciente", "destino", "destino__municipio")
        )
        return agrupar_por_veiculo(qs)

    def test_agrupamento_ordem_natural_e_sem_veiculo_ao_final(self):
        grupos = self._grupos()
        nomes = [g["veiculo"] for g in grupos]
        self.assertEqual(nomes, ["CARRO 2", "CARRO 10", "A DEFINIR"])

    def test_acompanhante_vira_linha_e_saida_e_a_mais_cedo(self):
        grupos = {g["veiculo"]: g for g in self._grupos()}
        carro2 = grupos["CARRO 2"]
        # 1 paciente + 1 acompanhante = 2 linhas.
        self.assertEqual(len(carro2["linhas"]), 2)
        self.assertTrue(carro2["linhas"][1]["ac"])
        self.assertEqual(carro2["linhas"][1]["nome"], "AC. Maria Acompanhante")
        self.assertEqual(carro2["saida"], time(5, 0))

    def test_cpf_do_paciente_sai_formatado_no_mapa(self):
        grupos = {g["veiculo"]: g for g in self._grupos()}
        linha_paciente = grupos["CARRO 2"]["linhas"][0]
        self.assertEqual(linha_paciente["cpf"], "529.982.247-25")

    def test_mapa_xlsx_e_pdf_geram_com_coluna_cpf(self):
        from .mapa import COLUNAS, gerar_mapa_pdf, gerar_mapa_xlsx
        self.assertIn("CPF", COLUNAS)
        grupos = self._grupos()
        xlsx = gerar_mapa_xlsx(self.dia, grupos, motorista="João")
        pdf = gerar_mapa_pdf(self.dia, grupos, motorista="João")
        self.assertTrue(xlsx and pdf)
        self.assertTrue(pdf[:4] == b"%PDF")

    def test_embarque_cai_no_endereco_do_paciente_quando_vazio(self):
        pac = Paciente.objects.create(
            nome="Pedro Endereço", cpf="11144477735",
            data_nascimento=date(1970, 5, 5), sexo="M",
            telefone_principal="31955554444", municipio=self.mun,
            logradouro="Rua das Flores", numero="123", bairro="Centro",
        )
        Agendamento.objects.create(
            paciente=pac, destino=self.dst, data=self.dia, horario=time(7, 0),
            tipo_veiculo="VAN BH",  # sem local_embarque
        )
        grupos = {g["veiculo"]: g for g in self._grupos()}
        linha = grupos["VAN BH"]["linhas"][0]
        self.assertEqual(linha["embarque"], "Rua das Flores, 123, Centro")

    def test_cancelado_nao_entra(self):
        total = sum(1 for g in self._grupos() for lin in g["linhas"] if not lin["ac"])
        self.assertEqual(total, 3)  # 4 agendamentos, 1 cancelado

    def test_local_inclui_endereco(self):
        grupos = {g["veiculo"]: g for g in self._grupos()}
        self.assertIn("Av. Alfredo Balena 190", grupos["CARRO 10"]["linhas"][0]["local"])

    def test_veiculo_do_cadastro_tem_precedencia(self):
        from apps.veiculos.models import Veiculo
        v = Veiculo.objects.create(nome="AMBULÂNCIA 1")
        # Mesmo com texto livre diferente, o agrupamento usa o veículo do cadastro.
        Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(6, 0),
            veiculo=v, tipo_veiculo="texto ignorado",
        )
        nomes = [g["veiculo"] for g in self._grupos()]
        self.assertIn("AMBULÂNCIA 1", nomes)
        self.assertNotIn("texto ignorado", nomes)
        # Ambulância vem antes de CARRO na ordem natural/alfabética.
        self.assertEqual(nomes[0], "AMBULÂNCIA 1")

    def test_pagina_carrega(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("relatorios:mapa_viagem"), {"data": self.dia.strftime("%Y-%m-%d")})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "CARRO 2")
        self.assertContains(r, "AC. Maria Acompanhante")

    def test_export_xlsx(self):
        self.client.force_login(self.user)
        r = self.client.get(
            reverse("relatorios:mapa_viagem"),
            {"data": self.dia.strftime("%Y-%m-%d"), "export": "xlsx", "motorista": "João"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheet", r["Content-Type"])
        self.assertEqual(r.content[:2], b"PK")

    def test_filtro_por_veiculo_no_mapa(self):
        from apps.veiculos.models import Veiculo
        self.client.force_login(self.user)
        v = Veiculo.objects.create(nome="CARRO 2", tipo="UTILITARIO")
        r = self.client.get(
            reverse("relatorios:mapa_viagem"),
            {"data": self.dia.strftime("%Y-%m-%d"), "veiculo": str(v.id)},
        )
        self.assertEqual(r.status_code, 200)
        # So o grupo CARRO 2 (por texto) deve sair; CARRO 10 fica de fora.
        self.assertContains(r, "CARRO 2")
        self.assertNotContains(r, "CARRO 10")

    def test_filtro_multiplos_veiculos_no_mapa(self):
        from apps.veiculos.models import Veiculo
        self.client.force_login(self.user)
        v2 = Veiculo.objects.create(nome="CARRO 2", tipo="UTILITARIO")
        v10 = Veiculo.objects.create(nome="CARRO 10", tipo="UTILITARIO")
        # getlist: vários valores com o mesmo nome de parâmetro.
        r = self.client.get(
            reverse("relatorios:mapa_viagem"),
            {"data": self.dia.strftime("%Y-%m-%d"), "veiculo": [str(v2.id), str(v10.id)]},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "CARRO 2")
        self.assertContains(r, "CARRO 10")

    def test_filtro_sem_veiculo_mostra_a_definir(self):
        from apps.veiculos.models import Veiculo
        self.client.force_login(self.user)
        v2 = Veiculo.objects.create(nome="CARRO 2", tipo="UTILITARIO")
        # Paciente distinto num agendamento sem veiculo (grupo A DEFINIR).
        sem_carro = Paciente.objects.create(
            nome="Paciente Sem Carro", cpf="11144477735",
            data_nascimento=date(1980, 3, 3), sexo="M",
            telefone_principal="31955550000", municipio=self.mun,
        )
        Agendamento.objects.create(
            paciente=sem_carro, destino=self.dst, data=self.dia, horario=time(7, 0),
        )
        # Filtrando só por CARRO 2, o paciente sem carro NAO aparece...
        r1 = self.client.get(
            reverse("relatorios:mapa_viagem"),
            {"data": self.dia.strftime("%Y-%m-%d"), "veiculo": str(v2.id)},
        )
        self.assertNotContains(r1, "Paciente Sem Carro")
        # ...mas marcando também "sem", ele volta a aparecer (junto com CARRO 2).
        r2 = self.client.get(
            reverse("relatorios:mapa_viagem"),
            {"data": self.dia.strftime("%Y-%m-%d"), "veiculo": [str(v2.id), "sem"]},
        )
        self.assertContains(r2, "Paciente Sem Carro")
        self.assertContains(r2, "CARRO 2")

    def test_pacientes_numerados_por_veiculo_na_ordem_do_horario(self):
        # Mais um paciente no CARRO 2, mais tarde que o das 08:00.
        Agendamento.objects.create(
            paciente=self.pac2, destino=self.dst, data=self.dia, horario=time(13, 0),
            tipo_veiculo="CARRO 2",
        )
        grupos = {g["veiculo"]: g for g in self._grupos()}
        carro2 = grupos["CARRO 2"]["linhas"]
        # 08:00 (José) = 1, seu acompanhante sem número, 13:00 (Ana) = 2.
        self.assertEqual([lin["ordem"] for lin in carro2], [1, "", 2])
        self.assertEqual(carro2[0]["horario"], "08:00")
        self.assertEqual(carro2[2]["horario"], "13:00")
        # A numeração recomeça em cada veículo.
        self.assertEqual(grupos["CARRO 10"]["linhas"][0]["ordem"], 1)

    def test_excel_tem_coluna_numero(self):
        from io import BytesIO
        from openpyxl import load_workbook
        from .mapa import gerar_mapa_xlsx
        ws = load_workbook(BytesIO(gerar_mapa_xlsx(self.dia, self._grupos()))).active
        self.assertEqual(ws.cell(row=6, column=2).value, "Nº")
        self.assertEqual(ws.cell(row=7, column=2).value, 1)

    def test_cpf_e_a_ultima_coluna_do_mapa(self):
        from .mapa import COLUNAS
        self.assertEqual(COLUNAS[-1], "CPF")
        self.assertEqual(COLUNAS[-2], "Horário saída")

    def test_export_pdf(self):
        self.client.force_login(self.user)
        r = self.client.get(
            reverse("relatorios:mapa_viagem"),
            {"data": self.dia.strftime("%Y-%m-%d"), "export": "pdf"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_dia_sem_agendamentos_nao_quebra(self):
        self.client.force_login(self.user)
        vazio = (self.dia + timedelta(days=7)).strftime("%Y-%m-%d")
        for exp in ["xlsx", "pdf"]:
            r = self.client.get(reverse("relatorios:mapa_viagem"), {"data": vazio, "export": exp})
            self.assertEqual(r.status_code, 200)

    def test_pdf_com_grupo_grande_nao_da_erro_500(self):
        # Regressao: um grupo com muitos pacientes (ex.: "A DEFINIR") gerava
        # LayoutError no PDF (celula mesclada maior que a pagina) -> erro 500.
        self.client.force_login(self.user)
        for i in range(60):
            Agendamento.objects.create(
                paciente=self.pac, destino=self.dst, data=self.dia, horario=time(6, 0),
                acompanhante="Acomp" if i % 2 else "",
            )
        r = self.client.get(
            reverse("relatorios:mapa_viagem"),
            {"data_inicio": self.dia.strftime("%Y-%m-%d"), "export": "pdf"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))

    def _segundo_dia(self):
        outro = self.dia + timedelta(days=1)
        Agendamento.objects.create(
            paciente=self.pac2, destino=self.dst, data=outro, horario=time(8, 0),
            tipo_veiculo="VAN BH",
        )
        return outro

    def test_periodo_mostra_os_dias_separados(self):
        self.client.force_login(self.user)
        outro = self._segundo_dia()
        r = self.client.get(reverse("relatorios:mapa_viagem"), {
            "data_inicio": self.dia.strftime("%Y-%m-%d"),
            "data_fim": outro.strftime("%Y-%m-%d"),
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["dias"]), 2)
        self.assertContains(r, "CARRO 2")   # 1º dia
        self.assertContains(r, "VAN BH")    # 2º dia

    def test_periodo_excel_tem_uma_aba_por_dia(self):
        from io import BytesIO
        from openpyxl import load_workbook
        self.client.force_login(self.user)
        outro = self._segundo_dia()
        r = self.client.get(reverse("relatorios:mapa_viagem"), {
            "data_inicio": self.dia.strftime("%Y-%m-%d"),
            "data_fim": outro.strftime("%Y-%m-%d"), "export": "xlsx",
        })
        self.assertEqual(r.status_code, 200)
        wb = load_workbook(BytesIO(r.content))
        self.assertEqual(wb.sheetnames, [f"{self.dia:%d-%m-%Y}", f"{outro:%d-%m-%Y}"])
        r2 = self.client.get(reverse("relatorios:mapa_viagem"), {
            "data_inicio": self.dia.strftime("%Y-%m-%d"),
            "data_fim": outro.strftime("%Y-%m-%d"), "export": "pdf",
        })
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.content.startswith(b"%PDF"))

    def test_periodo_invertido_e_limitado(self):
        self.client.force_login(self.user)
        # "Até" antes de "De": inverte automaticamente.
        outro = self._segundo_dia()
        r = self.client.get(reverse("relatorios:mapa_viagem"), {
            "data_inicio": outro.strftime("%Y-%m-%d"),
            "data_fim": self.dia.strftime("%Y-%m-%d"),
        })
        self.assertEqual(r.context["ini"], self.dia)
        self.assertEqual(r.context["fim"], outro)
        # Período maior que o máximo: limita.
        r2 = self.client.get(reverse("relatorios:mapa_viagem"), {
            "data_inicio": self.dia.strftime("%Y-%m-%d"),
            "data_fim": (self.dia + timedelta(days=200)).strftime("%Y-%m-%d"),
        })
        self.assertTrue(r2.context["limitado"])
        self.assertEqual((r2.context["fim"] - r2.context["ini"]).days, 30)


class FormulaInjectionTest(TestCase):
    def test_sanitiza_gatilhos_de_formula(self):
        from openpyxl import load_workbook
        from io import BytesIO

        from .exports import _sanitizar, exportar_xlsx

        # Campo de texto malicioso que iniciaria uma fórmula no Excel.
        self.assertEqual(_sanitizar("=HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(_sanitizar("+1+1"), "'+1+1")
        self.assertEqual(_sanitizar("texto normal"), "texto normal")

        conteudo = exportar_xlsx("T", ["A"], [["=1+1"], ["ok"]])
        wb = load_workbook(BytesIO(conteudo))
        ws = wb.active
        # A célula é armazenada como texto neutralizado, não como fórmula.
        self.assertEqual(ws["A2"].value, "'=1+1")
        self.assertEqual(ws["A2"].data_type, "s")
