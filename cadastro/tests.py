"""Testes de integração da Fase 2 (Django): pontuação ponta a ponta, trilha de
auditoria e bloqueio pós-finalização.

Rodar: ``python manage.py test``
(Os testes do motor puro ficam em ``tests/`` e rodam com ``pytest``.)
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from auditoria.models import Auditoria

from . import services
from .models import Inscricao, MembroNucleo, Pessoa, Renda

REF = date(2026, 9, 15)


def nasc(idade):
    return date(REF.year - idade, REF.month, REF.day)


class PontuacaoIntegracaoTest(TestCase):
    def _criar_inscricao_exemplo(self):
        req = Pessoa.objects.create(nome="João", cpf="111", data_nascimento=nasc(40), sexo="M")
        conj = Pessoa.objects.create(nome="Maria", cpf="222", data_nascimento=nasc(38), sexo="F")
        f1 = Pessoa.objects.create(nome="Pedro", cpf="333", data_nascimento=nasc(5), sexo="M")
        f2 = Pessoa.objects.create(nome="Ana", cpf="444", data_nascimento=nasc(8), sexo="F")

        insc = Inscricao.objects.create(
            requerente=req,
            data_referencia=REF,
            habitacao_precaria_ou_risco=True,
            matricula_comprovada=True,
            aluguel_mes_1=Decimal("1000"),
            aluguel_mes_2=Decimal("1100"),
            aluguel_mes_3=Decimal("1000"),
            status=Inscricao.Status.APTO,
        )
        m_req = MembroNucleo.objects.create(
            inscricao=insc, pessoa=req, parentesco="REQUERENTE", arrimo=True
        )
        Renda.objects.create(membro=m_req, tipo="FORMAL", valor=Decimal("3000"))
        MembroNucleo.objects.create(inscricao=insc, pessoa=conj, parentesco="COMPANHEIRO")
        MembroNucleo.objects.create(inscricao=insc, pessoa=f1, parentesco="FILHO")
        MembroNucleo.objects.create(inscricao=insc, pessoa=f2, parentesco="FILHO")
        return insc

    def test_exemplo_141_pontos_ponta_a_ponta(self):
        insc = self._criar_inscricao_exemplo()
        r = services.calcular_e_salvar(insc)

        insc.refresh_from_db()
        self.assertEqual(insc.pontos_legais, 120)
        self.assertEqual(insc.pontos_complementares, 21)
        self.assertEqual(insc.pontuacao_total, 141)
        self.assertEqual(r.pontuacao_total, 141)

        # Critérios legais persistidos
        self.assertEqual(insc.criterios_legais.get(inciso="CL_III").pontos, 0)
        self.assertEqual(insc.criterios_legais.get(inciso="CL_IV").pontos, 40)
        # Classificação criada com chaves de desempate
        self.assertEqual(insc.classificacao.dependentes_ate_12, 2)
        self.assertEqual(insc.classificacao.idosos, 0)

    def test_numero_inscricao_gerado(self):
        insc = self._criar_inscricao_exemplo()
        self.assertTrue(insc.numero_inscricao)
        self.assertEqual(insc.numero_inscricao, f"{insc.pk:06d}")


class AuditoriaTest(TestCase):
    def test_criacao_gera_registro(self):
        Pessoa.objects.create(nome="Zé", cpf="999", data_nascimento=nasc(30))
        self.assertTrue(
            Auditoria.objects.filter(
                tabela="cadastro.Pessoa", operacao=Auditoria.Operacao.CRIACAO
            ).exists()
        )

    def test_alteracao_registra_campo(self):
        p = Pessoa.objects.create(nome="Zé", cpf="998", data_nascimento=nasc(30))
        p.nome = "José"
        p.save()
        reg = Auditoria.objects.get(
            tabela="cadastro.Pessoa",
            operacao=Auditoria.Operacao.ALTERACAO,
            campo="nome",
        )
        self.assertEqual(reg.valor_anterior, "Zé")
        self.assertEqual(reg.valor_novo, "José")

    def test_auditoria_e_imutavel(self):
        p = Pessoa.objects.create(nome="Zé", cpf="997", data_nascimento=nasc(30))
        reg = Auditoria.objects.filter(registro_id=str(p.pk)).first()
        with self.assertRaises(RuntimeError):
            reg.justificativa = "x"
            reg.save()


class BloqueioTest(TestCase):
    def test_inscricao_bloqueada_nao_edita(self):
        req = Pessoa.objects.create(nome="A", cpf="1", data_nascimento=nasc(40))
        insc = Inscricao.objects.create(requerente=req)
        insc.bloqueada = True
        insc.data_finalizacao = timezone.now()
        insc.save()  # a transição para bloqueada é permitida

        insc.telefone = "99999-9999"
        with self.assertRaises(ValidationError):
            insc.save()

    def test_alteracao_autorizada_passa(self):
        req = Pessoa.objects.create(nome="B", cpf="2", data_nascimento=nasc(40))
        insc = Inscricao.objects.create(requerente=req, bloqueada=True)
        insc.telefone = "1234"
        insc._alteracao_autorizada = True
        insc.save()  # não deve levantar
        insc.refresh_from_db()
        self.assertEqual(insc.telefone, "1234")


class ClassificacaoTest(TestCase):
    def _apta(self, cpf, filhos_ate_12):
        req = Pessoa.objects.create(nome=f"R{cpf}", cpf=cpf, data_nascimento=nasc(40))
        insc = Inscricao.objects.create(
            requerente=req,
            data_referencia=REF,
            habitacao_precaria_ou_risco=True,
            matricula_comprovada=True,
            status=Inscricao.Status.APTO,
        )
        m = MembroNucleo.objects.create(inscricao=insc, pessoa=req, parentesco="REQUERENTE")
        Renda.objects.create(membro=m, tipo="FORMAL", valor=Decimal("3000"))
        for i in range(filhos_ate_12):
            f = Pessoa.objects.create(
                nome=f"F{cpf}{i}", cpf=f"{cpf}f{i}", data_nascimento=nasc(5)
            )
            MembroNucleo.objects.create(inscricao=insc, pessoa=f, parentesco="FILHO")
        services.calcular_e_salvar(insc)
        return insc

    def test_desempate_por_filhos(self):
        a = self._apta("10", filhos_ate_12=2)
        b = self._apta("20", filhos_ate_12=1)
        services.classificar_todos()
        a.refresh_from_db(); b.refresh_from_db()
        # Mesma pontuação; A tem mais filhos <=12 → posição melhor (menor número).
        self.assertLess(a.classificacao.posicao, b.classificacao.posicao)

    def test_empate_marcado_para_sorteio(self):
        a = self._apta("30", filhos_ate_12=1)
        b = self._apta("40", filhos_ate_12=1)
        services.classificar_todos()
        a.refresh_from_db(); b.refresh_from_db()
        self.assertTrue(a.classificacao.empate_pendente_sorteio)
        self.assertTrue(b.classificacao.empate_pendente_sorteio)
