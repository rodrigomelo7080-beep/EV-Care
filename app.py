import streamlit as st
import json
import csv
import io
from datetime import datetime, date
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from catalogo_veiculos_db import (
    listar_marcas_catalogo,
    listar_modelos_por_marca_catalogo,
    listar_versoes_catalogo,
    listar_modelos_catalogo,
    buscar_veiculo_catalogo
)
from auth_helpers import (
    inicializar_estado_auth,
    criar_conta,
    entrar_usuario,
    sair_usuario
)

from plano_helpers import (
    obter_plano_usuario,
    pode_criar_veiculo,
    recurso_disponivel,
    exibir_bloqueio_plus,
    exibir_resumo_plano,
    obter_recursos_plus,
    mensagem_recurso_plus,
    usuario_plus_ativo
)

from veiculos_db import (
    listar_veiculos_usuario,
    contar_veiculos_usuario,
    criar_veiculo_online,
    atualizar_veiculo_online,
    definir_veiculo_ativo_online,
    obter_veiculo_ativo_online,
    excluir_veiculo_online
)
from quilometragem_db import (
    atualizar_km_veiculo_online,
    listar_historico_km_online
)
from recargas_db import (
    listar_recargas_online,
    registrar_recarga_online,
    editar_recarga_online,
    excluir_recarga_online,
    obter_resumo_recargas_online
)
from manutencoes_db import (
    criar_plano_padrao_manutencao_online,
    listar_servicos_manutencao_online,
    criar_servico_manutencao_online,
    editar_servico_manutencao_online,
    desativar_servico_manutencao_online,
    registrar_manutencao_online,
    listar_manutencoes_online,
    obter_resumo_manutencoes_online
)
from feedback_db import (
    registrar_feedback_online,
    listar_meus_feedbacks
)

from veiculo_online_adapter import converter_veiculo_online
from ev_care_base import (
    MANUTENCOES_EV_DETALHADAS,
    buscar_preco_kwh
)


st.set_page_config(
    page_title="EV Care",
    page_icon="⚡",
    layout="wide"
)

inicializar_estado_auth()

# =============================================================================
# FUNÇÕES DE APOIO DO APP VISUAL
# =============================================================================

def garantir_plano_manutencao_expandido(veiculo):
    """
    Garante que veículos antigos também recebam o plano geral expandido,
    sem apagar serviços já existentes.
    """
    if not veiculo:
        return False

    alterou = False

    if "Revisao" not in veiculo.info or not isinstance(veiculo.info.get("Revisao"), dict):
        veiculo.info["Revisao"] = {}
        alterou = True

    if "ManutencaoDetalhada" not in veiculo.info or not isinstance(veiculo.info.get("ManutencaoDetalhada"), dict):
        veiculo.info["ManutencaoDetalhada"] = {}
        alterou = True

    for item, dados in MANUTENCOES_EV_DETALHADAS.items():
        if item not in veiculo.info["Revisao"]:
            veiculo.info["Revisao"][item] = dados["intervalo_km"]
            alterou = True

        if item not in veiculo.info["ManutencaoDetalhada"]:
            veiculo.info["ManutencaoDetalhada"][item] = dados
            alterou = True

        if item not in veiculo.ultima_revisao:
            veiculo.ultima_revisao[item] = 0
            alterou = True

    veiculo.plano = veiculo.info["Revisao"]

    return alterou


    return {
        "categoria": "Personalizado",
        "intervalo_km": veiculo.plano.get(item, 10000),
        "intervalo_meses": 12,
        "criticidade": "Média",
        "descricao": "Serviço personalizado."
    }




def obter_veiculo_ativo():
    return st.session_state.get("veiculo_ativo", None)


def gerar_csv_recargas(recargas):
    """
    Gera um arquivo CSV em texto com as recargas do veículo.
    Usa separador ';' para facilitar abertura no Excel em PT-BR.
    """
    saida = io.StringIO()

    # BOM UTF-8 para o Excel reconhecer acentos corretamente
    saida.write("\ufeff")

    escritor = csv.writer(saida, delimiter=";")

    escritor.writerow(
        [
            "Data da recarga",
            "KM atual",
            "Bateria inicial (%)",
            "Bateria final (%)",
            "Energia carregada (kWh)",
            "Preço do kWh (R$)",
            "Custo total (R$)",
            "Local",
            "Tipo",
            "Observação"
        ]
    )

    for recarga in recargas:
        escritor.writerow(
            [
                recarga.get("data_recarga", ""),
                recarga.get("km_atual", ""),
                recarga.get("bateria_inicial", ""),
                recarga.get("bateria_final", ""),
                recarga.get("energia_kwh", ""),
                recarga.get("preco_kwh", ""),
                recarga.get("custo_total", ""),
                recarga.get("local", ""),
                recarga.get("tipo", ""),
                recarga.get("observacao", "")
            ]
        )

    return saida.getvalue()

def gerar_csv_manutencoes(manutencoes):
    """
    Gera um arquivo CSV em texto com o histórico de manutenções do veículo.
    Usa separador ';' para facilitar abertura no Excel em PT-BR.
    """
    saida = io.StringIO()

    # BOM UTF-8 para o Excel reconhecer acentos corretamente
    saida.write("\ufeff")

    escritor = csv.writer(saida, delimiter=";")

    escritor.writerow(
        [
            "Data da manutenção",
            "Serviço",
            "KM realizada",
            "Observação"
        ]
    )

    for manutencao in manutencoes:
        escritor.writerow(
            [
                manutencao.get("data_realizada", ""),
                manutencao.get("nome_servico", ""),
                manutencao.get("km_realizada", ""),
                manutencao.get("observacao", "")
            ]
        )

    return saida.getvalue()

def gerar_csv_quilometragem(historico_km):
    """
    Gera um arquivo CSV em texto com o histórico de quilometragem do veículo.
    Usa separador ';' para facilitar abertura no Excel em PT-BR.
    """
    saida = io.StringIO()

    # BOM UTF-8 para o Excel reconhecer acentos corretamente
    saida.write("\ufeff")

    escritor = csv.writer(saida, delimiter=";")

    escritor.writerow(
        [
            "Data do registro",
            "KM anterior",
            "Nova KM",
            "Diferença registrada"
        ]
    )

    for registro in historico_km:
        km_anterior = int(registro.get("km_anterior", 0) or 0)
        km_nova = int(registro.get("km_nova", 0) or 0)
        diferenca = km_nova - km_anterior

        escritor.writerow(
            [
                registro.get("data_registro", ""),
                km_anterior,
                km_nova,
                diferenca
            ]
        )

    return saida.getvalue()

def gerar_pdf_resumo_veiculo(veiculo, resumo_recargas, resumo_manutencao):
    """
    Gera um PDF resumido do veículo com dados principais, recargas e manutenções.
    Retorna bytes prontos para uso em st.download_button.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    estilos = getSampleStyleSheet()
    elementos = []

    titulo = estilos["Title"]
    subtitulo = estilos["Heading2"]
    normal = estilos["BodyText"]

    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")

    elementos.append(Paragraph("EV Care — Relatório do Veículo", titulo))
    elementos.append(Spacer(1, 0.4 * cm))
    elementos.append(Paragraph(f"Gerado em: {data_geracao}", normal))
    elementos.append(Spacer(1, 0.6 * cm))

    marca_modelo = f"{veiculo.marca} {veiculo.modelo}"
    autonomia = veiculo.calcular_autonomia()
    saude_bateria = veiculo.calcular_saude_bateria()

    elementos.append(Paragraph("Dados do veículo", subtitulo))

    dados_veiculo = [
        ["Veículo", escape(marca_modelo)],
        ["KM atual", f"{veiculo.km_atual} km"],
        ["Autonomia estimada", f"{autonomia:.0f} km"],
        ["Saúde estimada da bateria", f"{saude_bateria:.2f}%"],
        ["Bateria", escape(str(veiculo.info.get("Bateria", "Não informada")))],
        ["Consumo", f"{veiculo.info.get('Consumo', 0)} km/kWh"],
    ]

    tabela_veiculo = Table(dados_veiculo, colWidths=[6 * cm, 9 * cm])
    tabela_veiculo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elementos.append(tabela_veiculo)
    elementos.append(Spacer(1, 0.7 * cm))

    elementos.append(Paragraph("Resumo de recargas", subtitulo))

    custo_real = resumo_recargas.get("custo_real_km")
    consumo_real = resumo_recargas.get("consumo_real_km_kwh")

    dados_recargas = [
        ["Total de recargas", resumo_recargas.get("total_recargas", 0)],
        ["Energia total", f"{resumo_recargas.get('energia_total', 0):.2f} kWh"],
        ["Gasto total", f"R$ {resumo_recargas.get('custo_total', 0):.2f}"],
        ["Preço médio kWh", f"R$ {resumo_recargas.get('preco_medio_kwh', 0):.2f}"],
        [
            "Custo real por km",
            f"R$ {custo_real:.4f}" if custo_real is not None else "Indisponível"
        ],
        [
            "Consumo real",
            f"{consumo_real:.2f} km/kWh" if consumo_real is not None else "Indisponível"
        ],
        ["KM considerados", f"{resumo_recargas.get('km_rodados', 0)} km"],
    ]

    tabela_recargas = Table(dados_recargas, colWidths=[6 * cm, 9 * cm])
    tabela_recargas.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elementos.append(tabela_recargas)
    elementos.append(Spacer(1, 0.7 * cm))

    elementos.append(Paragraph("Resumo de manutenções", subtitulo))

    total_servicos = resumo_manutencao.get("total_servicos", 0)
    vencidos = resumo_manutencao.get("vencidos", [])
    proximos = resumo_manutencao.get("proximos", [])
    em_dia = resumo_manutencao.get("em_dia", [])

    dados_manutencao = [
        ["Total de serviços", total_servicos],
        ["Vencidos", len(vencidos)],
        ["Próximos", len(proximos)],
        ["Em dia", len(em_dia)],
    ]

    tabela_manutencao = Table(dados_manutencao, colWidths=[6 * cm, 9 * cm])
    tabela_manutencao.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elementos.append(tabela_manutencao)
    elementos.append(Spacer(1, 0.7 * cm))

    def adicionar_tabela_manutencoes_pdf(titulo_secao, itens):
        """
        Adiciona ao PDF uma tabela com manutenções vencidas ou próximas.
        """
        if not itens:
            return

        elementos.append(Paragraph(titulo_secao, subtitulo))

        dados_tabela = [
            ["Serviço", "Status", "Última KM", "Próxima KM", "Situação"]
        ]

        for servico, dados in itens:
            km_restante = dados.get("km_restante", 0)

            if km_restante >= 0:
                situacao_txt = f"Faltam {km_restante} km"
            else:
                situacao_txt = f"Vencida há {abs(km_restante)} km"

            dados_tabela.append(
                [
                    Paragraph(escape(str(servico.get("nome", "Não informado"))), normal),
                    Paragraph(escape(str(dados.get("status", "Não informado"))), normal),
                    f"{dados.get('ultima_km', 0)} km",
                    f"{dados.get('proxima_km', 0)} km",
                    Paragraph(escape(situacao_txt), normal)
                ]
            )

        tabela = Table(
            dados_tabela,
            colWidths=[5.2 * cm, 2.6 * cm, 2.6 * cm, 2.8 * cm, 3.8 * cm],
            repeatRows=1
        )

        tabela.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        elementos.append(tabela)
        elementos.append(Spacer(1, 0.5 * cm))


    manuntencoes_vencidas_pdf = resumo_manutencao.get("vencidos", [])
    manutencoes_proximas_pdf = resumo_manutencao.get("proximos", [])

    if manuntencoes_vencidas_pdf or manutencoes_proximas_pdf:
        adicionar_tabela_manutencoes_pdf(
            "Manutenções vencidas",
            manuntencoes_vencidas_pdf
        )

        adicionar_tabela_manutencoes_pdf(
            "Manutenções próximas de vencer",
            manutencoes_proximas_pdf
        )
    else:
        elementos.append(Paragraph("Alertas de manutenção", subtitulo))
        elementos.append(
            Paragraph(
                "Nenhuma manutenção vencida ou próxima de vencer no momento.",
                normal
            )
        )

    elementos.append(Spacer(1, 0.7 * cm))
    elementos.append(
        Paragraph(
            "Relatório gerado pelo EV Care. Os valores são estimativas baseadas nos dados registrados pelo usuário.",
            normal
        )
    )

    doc.build(elementos)

    buffer.seek(0)
    return buffer.getvalue()

def gerar_pdf_relatorio_mensal(veiculo, resumo_mensal, mes_nome, ano):
    """
    Gera um PDF com o relatório mensal do veículo.
    Retorna bytes prontos para uso em st.download_button.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    estilos = getSampleStyleSheet()
    elementos = []

    titulo = estilos["Title"]
    subtitulo = estilos["Heading2"]
    normal = estilos["BodyText"]

    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")

    elementos.append(Paragraph("EV Care — Relatório Mensal", titulo))
    elementos.append(Spacer(1, 0.4 * cm))
    elementos.append(Paragraph(f"Período: {escape(str(mes_nome))}/{ano}", normal))
    elementos.append(Paragraph(f"Gerado em: {data_geracao}", normal))
    elementos.append(Spacer(1, 0.6 * cm))

    # -------------------------------------------------------------------------
    # DADOS DO VEÍCULO
    # -------------------------------------------------------------------------
    elementos.append(Paragraph("Dados do veículo", subtitulo))

    marca_modelo = f"{veiculo.marca} {veiculo.modelo}"

    dados_veiculo = [
        ["Veículo", Paragraph(escape(marca_modelo), normal)],
        ["KM atual", f"{veiculo.km_atual} km"],
        ["Autonomia estimada", f"{veiculo.calcular_autonomia():.0f} km"],
        ["Saúde estimada da bateria", f"{veiculo.calcular_saude_bateria():.2f}%"],
        ["Bateria", Paragraph(escape(str(veiculo.info.get("Bateria", "Não informada"))), normal)],
        ["Consumo de referência", f"{veiculo.info.get('Consumo', 0)} km/kWh"],
    ]

    tabela_veiculo = Table(
        dados_veiculo,
        colWidths=[6 * cm, 9 * cm]
    )

    tabela_veiculo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elementos.append(tabela_veiculo)
    elementos.append(Spacer(1, 0.7 * cm))

    # -------------------------------------------------------------------------
    # RESUMO DO MÊS
    # -------------------------------------------------------------------------
    elementos.append(Paragraph("Resumo do mês", subtitulo))

    custo_por_km = resumo_mensal.get("custo_por_km_mes")

    dados_resumo = [
        ["Recargas no mês", resumo_mensal.get("total_recargas", 0)],
        ["Energia carregada", f"{resumo_mensal.get('energia_total', 0):.2f} kWh"],
        ["Gasto no mês", f"R$ {resumo_mensal.get('custo_total', 0):.2f}"],
        ["Preço médio kWh", f"R$ {resumo_mensal.get('preco_medio_kwh', 0):.2f}"],
        ["Registros de KM", resumo_mensal.get("total_registros_km", 0)],
        ["KM registrados no mês", f"{resumo_mensal.get('km_registrados_mes', 0)} km"],
        ["Manutenções realizadas", resumo_mensal.get("total_manutencoes", 0)],
        [
            "Custo aproximado por km",
            f"R$ {custo_por_km:.4f}" if custo_por_km is not None else "Indisponível"
        ],
    ]

    tabela_resumo = Table(
        dados_resumo,
        colWidths=[7 * cm, 8 * cm]
    )

    tabela_resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elementos.append(tabela_resumo)
    elementos.append(Spacer(1, 0.7 * cm))

    # -------------------------------------------------------------------------
    # RECARGAS DO MÊS
    # -------------------------------------------------------------------------
    recargas_mes = resumo_mensal.get("recargas_mes", [])

    elementos.append(Paragraph("Recargas do mês", subtitulo))

    if recargas_mes:
        dados_recargas = [
            ["Data", "KM", "Energia", "Custo", "Local"]
        ]

        for recarga in recargas_mes:
            dados_recargas.append(
                [
                    Paragraph(escape(str(recarga.get("data_recarga", ""))), normal),
                    f"{recarga.get('km_atual', 0)} km",
                    f"{float(recarga.get('energia_kwh') or 0):.2f} kWh",
                    f"R$ {float(recarga.get('custo_total') or 0):.2f}",
                    Paragraph(escape(str(recarga.get("local", ""))), normal),
                ]
            )

        tabela_recargas = Table(
            dados_recargas,
            colWidths=[4 * cm, 3 * cm, 3 * cm, 3 * cm, 4 * cm],
            repeatRows=1
        )

        tabela_recargas.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        elementos.append(tabela_recargas)
    else:
        elementos.append(
            Paragraph(
                "Nenhuma recarga registrada no mês selecionado.",
                normal
            )
        )

    elementos.append(Spacer(1, 0.7 * cm))

    # -------------------------------------------------------------------------
    # QUILOMETRAGEM DO MÊS
    # -------------------------------------------------------------------------
    km_mes = resumo_mensal.get("km_mes", [])

    elementos.append(Paragraph("Quilometragem do mês", subtitulo))

    if km_mes:
        dados_km = [
            ["Data", "KM anterior", "Nova KM", "Diferença"]
        ]

        for registro in km_mes:
            km_anterior = int(registro.get("km_anterior") or 0)
            km_nova = int(registro.get("km_nova") or 0)
            diferenca = km_nova - km_anterior

            dados_km.append(
                [
                    Paragraph(escape(str(registro.get("data_registro", ""))), normal),
                    f"{km_anterior} km",
                    f"{km_nova} km",
                    f"{diferenca} km",
                ]
            )

        tabela_km = Table(
            dados_km,
            colWidths=[5 * cm, 4 * cm, 4 * cm, 4 * cm],
            repeatRows=1
        )

        tabela_km.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        elementos.append(tabela_km)
    else:
        elementos.append(
            Paragraph(
                "Nenhuma atualização de quilometragem registrada no mês selecionado.",
                normal
            )
        )

    elementos.append(Spacer(1, 0.7 * cm))

    # -------------------------------------------------------------------------
    # MANUTENÇÕES DO MÊS
    # -------------------------------------------------------------------------
    manutencoes_mes = resumo_mensal.get("manutencoes_mes", [])

    elementos.append(Paragraph("Manutenções realizadas no mês", subtitulo))

    if manutencoes_mes:
        dados_manutencoes = [
            ["Data", "Serviço", "KM", "Observação"]
        ]

        for manutencao in manutencoes_mes:
            dados_manutencoes.append(
                [
                    Paragraph(escape(str(manutencao.get("data_realizada", ""))), normal),
                    Paragraph(escape(str(manutencao.get("nome_servico", ""))), normal),
                    f"{manutencao.get('km_realizada', 0)} km",
                    Paragraph(escape(str(manutencao.get("observacao", ""))), normal),
                ]
            )

        tabela_manutencoes = Table(
            dados_manutencoes,
            colWidths=[4 * cm, 5 * cm, 3 * cm, 5 * cm],
            repeatRows=1
        )

        tabela_manutencoes.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        elementos.append(tabela_manutencoes)
    else:
        elementos.append(
            Paragraph(
                "Nenhuma manutenção registrada no mês selecionado.",
                normal
            )
        )

    elementos.append(Spacer(1, 0.7 * cm))

    elementos.append(
        Paragraph(
            "Relatório gerado pelo EV Care. Os valores são estimativas baseadas nos dados registrados pelo usuário.",
            normal
        )
    )

    doc.build(elementos)

    buffer.seek(0)
    return buffer.getvalue()


def converter_data_iso_para_datetime(valor):
    """
    Converte datas vindas do Supabase para datetime.
    Aceita formatos ISO com ou sem timezone.
    """
    if not valor:
        return None

    texto = str(valor).strip()

    try:
        texto = texto.replace("Z", "+00:00")
        return datetime.fromisoformat(texto)
    except Exception:
        pass

    try:
        return datetime.strptime(texto[:10], "%Y-%m-%d")
    except Exception:
        return None


def filtrar_registros_por_mes(registros, campo_data, ano, mes):
    """
    Filtra registros pelo ano e mês informados.
    """
    filtrados = []

    for registro in registros:
        data_registro = converter_data_iso_para_datetime(
            registro.get(campo_data)
        )

        if not data_registro:
            continue

        if data_registro.year == ano and data_registro.month == mes:
            filtrados.append(registro)

    return filtrados


def calcular_resumo_mensal_online(veiculo, ano, mes):
    """
    Calcula um resumo mensal usando dados online:
    recargas, quilometragem e manutenções.
    """
    recargas, erro_recargas = listar_recargas_online(veiculo.id_online)

    if erro_recargas:
        return None, erro_recargas

    historico_km, erro_km = listar_historico_km_online(veiculo.id_online)

    if erro_km:
        return None, erro_km

    manutencoes, erro_manutencoes = listar_manutencoes_online(
        veiculo.id_online
    )

    if erro_manutencoes:
        return None, erro_manutencoes

    recargas_mes = filtrar_registros_por_mes(
        recargas,
        "data_recarga",
        ano,
        mes
    )

    km_mes = filtrar_registros_por_mes(
        historico_km,
        "data_registro",
        ano,
        mes
    )

    manutencoes_mes = filtrar_registros_por_mes(
        manutencoes,
        "data_realizada",
        ano,
        mes
    )

    energia_total = sum(
        float(r.get("energia_kwh") or 0)
        for r in recargas_mes
    )

    custo_total = sum(
        float(r.get("custo_total") or 0)
        for r in recargas_mes
    )

    preco_medio_kwh = (
        custo_total / energia_total
        if energia_total > 0
        else 0
    )

    km_registrados_mes = 0

    for registro in km_mes:
        km_anterior = int(registro.get("km_anterior") or 0)
        km_nova = int(registro.get("km_nova") or 0)

        diferenca = km_nova - km_anterior

        if diferenca > 0:
            km_registrados_mes += diferenca

    custo_por_km_mes = (
        custo_total / km_registrados_mes
        if km_registrados_mes > 0
        else None
    )

    resumo = {
        "recargas_mes": recargas_mes,
        "km_mes": km_mes,
        "manutencoes_mes": manutencoes_mes,
        "total_recargas": len(recargas_mes),
        "energia_total": energia_total,
        "custo_total": custo_total,
        "preco_medio_kwh": preco_medio_kwh,
        "total_registros_km": len(km_mes),
        "km_registrados_mes": km_registrados_mes,
        "custo_por_km_mes": custo_por_km_mes,
        "total_manutencoes": len(manutencoes_mes),
    }

    return resumo, None

def validar_contexto_online(nome_pagina):
    """
    Valida se o usuário está logado e possui um veículo online ativo.

    Antes de bloquear, tenta carregar ou ativar automaticamente
    um veículo do usuário.
    """
    if not st.session_state.get("auth_logado", False):
        st.warning(
            f"Para usar **{nome_pagina}**, faça login na página **Conta**."
        )
        return False

    carregar_veiculo_online_ativo_para_app()

    veiculo = obter_veiculo_ativo()

    if not veiculo:
        st.warning(
            f"Para usar **{nome_pagina}**, cadastre ou ative um veículo em **Minha Garagem**."
        )
        return False

    if getattr(veiculo, "origem_dados", None) != "supabase":
        st.warning(
            f"Para usar **{nome_pagina}**, é necessário ter um veículo cadastrado "
            "na sua conta."
        )
        return False

    if not getattr(veiculo, "id_online", None):
        st.warning(
            f"O veículo ativo não possui identificação online. "
            "Acesse **Minha Garagem** e selecione um veículo."
        )
        return False

    return True

def carregar_veiculo_online_ativo_para_app():
    """
    Carrega o veículo ativo do usuário logado.

    Se nenhum veículo estiver marcado como ativo no Supabase,
    mas o usuário tiver veículos cadastrados, o app ativa automaticamente
    o primeiro veículo encontrado.
    """
    if not st.session_state.get("auth_logado", False):
        st.session_state.veiculo_ativo = None
        st.session_state.veiculo_ativo_origem = None
        st.session_state.erro_veiculo_online_ativo = None
        return False

    registro_online, erro = obter_veiculo_ativo_online()

    if erro:
        st.session_state.veiculo_ativo = None
        st.session_state.veiculo_ativo_origem = None
        st.session_state.erro_veiculo_online_ativo = erro
        return False

    # Se não houver veículo ativo, tenta ativar automaticamente o primeiro veículo da conta
    if not registro_online:
        veiculos_usuario, erro_lista = listar_veiculos_usuario()

        if erro_lista:
            st.session_state.veiculo_ativo = None
            st.session_state.veiculo_ativo_origem = None
            st.session_state.erro_veiculo_online_ativo = erro_lista
            return False

        if not veiculos_usuario:
            st.session_state.veiculo_ativo = None
            st.session_state.veiculo_ativo_origem = None
            st.session_state.erro_veiculo_online_ativo = None
            return False

        primeiro_veiculo = veiculos_usuario[0]
        primeiro_veiculo_id = primeiro_veiculo.get("id")

        if not primeiro_veiculo_id:
            st.session_state.veiculo_ativo = None
            st.session_state.veiculo_ativo_origem = None
            st.session_state.erro_veiculo_online_ativo = "Veículo sem ID online."
            return False

        ok_ativar, resposta_ativar = definir_veiculo_ativo_online(
            primeiro_veiculo_id
        )

        if not ok_ativar:
            st.session_state.veiculo_ativo = None
            st.session_state.veiculo_ativo_origem = None
            st.session_state.erro_veiculo_online_ativo = resposta_ativar
            return False

        registro_online, erro = obter_veiculo_ativo_online()

        if erro:
            st.session_state.veiculo_ativo = None
            st.session_state.veiculo_ativo_origem = None
            st.session_state.erro_veiculo_online_ativo = erro
            return False

    if not registro_online:
        st.session_state.veiculo_ativo = None
        st.session_state.veiculo_ativo_origem = None
        st.session_state.erro_veiculo_online_ativo = None
        return False

    user_id_registro = registro_online.get("user_id")
    user_id_sessao = st.session_state.get("auth_user_id")

    if user_id_registro and user_id_sessao and user_id_registro != user_id_sessao:
        st.session_state.veiculo_ativo = None
        st.session_state.veiculo_ativo_origem = None
        st.session_state.erro_veiculo_online_ativo = (
            "O veículo carregado não pertence ao usuário atual."
        )
        return False

    veiculo_convertido = converter_veiculo_online(registro_online)

    if veiculo_convertido is None:
        st.session_state.veiculo_ativo = None
        st.session_state.veiculo_ativo_origem = None
        st.session_state.erro_veiculo_online_ativo = (
            "Não foi possível converter o veículo ativo."
        )
        return False

    garantir_plano_manutencao_expandido(veiculo_convertido)

    st.session_state.veiculo_ativo = veiculo_convertido
    st.session_state.veiculo_ativo_origem = "supabase"
    st.session_state.erro_veiculo_online_ativo = None

    return True

def mostrar_cabecalho_pagina(titulo, descricao=None):
    """
    Mostra um cabeçalho padronizado para páginas do EV Care.
    """
    st.header(titulo)

    if descricao:
        st.caption(descricao)

    st.divider()

def mostrar_card_metrica(titulo, valor, descricao=None):
    """
    Mostra um card visual simples para métricas e indicadores.
    """
    with st.container(border=True):
        st.caption(titulo)
        st.markdown(f"### {valor}")

        if descricao:
            st.caption(descricao)


def mostrar_bloco_secao(titulo, descricao=None):
    """
    Mostra título e descrição padronizados para seções internas.
    """
    st.subheader(titulo)

    if descricao:
        st.caption(descricao)


def mostrar_status_plano_visual():
    """
    Mostra o plano atual do usuário de forma visual.
    """
    plano = str(st.session_state.get("auth_plano", "free")).lower()
    status = str(st.session_state.get("auth_status_assinatura", "inactive")).lower()

    if plano == "plus" and status == "active":
        st.success("Plano Plus ativo")
    elif plano == "plus":
        st.warning("Plano Plus sem assinatura ativa")
    else:
        st.info("Plano Free")


def formatar_moeda(valor):
    """
    Formata valores em reais.
    """
    try:
        return f"R$ {float(valor):.2f}"
    except Exception:
        return "R$ 0.00"


def formatar_km(valor):
    """
    Formata quilometragem.
    """
    try:
        return f"{int(valor):,} km".replace(",", ".")
    except Exception:
        return "0 km"


def formatar_numero(valor, casas=2):
    """
    Formata número com casas decimais.
    """
    try:
        return f"{float(valor):.{casas}f}"
    except Exception:
        return f"{0:.{casas}f}"


def mostrar_aviso_recurso_plus(nome_recurso):
    """
    Mostra aviso padronizado para recursos Plus bloqueados.
    """
    exibir_bloqueio_plus(nome_recurso)


def mostrar_estado_vazio(titulo, mensagem):
    """
    Mostra uma mensagem padronizada para telas sem dados.
    """
    with st.container(border=True):
        st.write(f"### {titulo}")
        st.info(mensagem)

def mostrar_onboarding_beta():
    """
    Mostra uma orientação inicial para usuários novos no EV Care.
    """
    st.markdown("## Bem-vindo ao EV Care ⚡")

    st.write(
        "O EV Care ajuda você a acompanhar recargas, quilometragem, custos, "
        "manutenções e relatórios do seu veículo elétrico em um só lugar."
    )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 1. Cadastre seu veículo")
        st.write(
            "Comece adicionando seu carro em **Minha Garagem**. "
            "O veículo será usado nas páginas de recargas, quilometragem, "
            "manutenções, custos e relatórios."
        )

    with col2:
        st.markdown("### 2. Registre seu uso")
        st.write(
            "Atualize a quilometragem, registre recargas e lance manutenções "
            "para gerar indicadores reais de custo, consumo e alertas."
        )

    with col3:
        st.markdown("### 3. Acompanhe os resultados")
        st.write(
            "Use o Dashboard, Histórico, Custos e relatórios Plus para acompanhar "
            "a evolução do veículo ao longo do tempo."
        )

    st.divider()

    st.success(
        "Fluxo recomendado: Minha Garagem → Quilometragem → Recargas → "
        "Manutenções → Dashboard."
    )





# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.title("⚡ EV Care")
st.sidebar.caption("Gestão de carros elétricos")

usuario = "default"

if st.session_state.get("auth_logado", False):
    carregar_veiculo_online_ativo_para_app()
else:
    st.session_state.veiculo_ativo = None
    st.session_state.veiculo_ativo_origem = None
    st.session_state.erro_veiculo_online_ativo = None

garagem = []
veiculo_ativo = obter_veiculo_ativo()



st.sidebar.divider()

pagina = st.sidebar.radio(
    "Menu principal",
    [
        "Dashboard",
        "Minha Garagem",
        "Quilometragem",
        "Recargas",
        "Manutenções",
        "Viagens",
        "Custos e Economia",
        "Histórico",
        "Planos",
        "Configurações",
        "Conta",
        "Feedback"
    ]
)

st.sidebar.divider()


if st.session_state.auth_logado:
    st.sidebar.success(f"Logado: {st.session_state.auth_email}")
    st.sidebar.caption(f"Plano atual: {st.session_state.auth_plano}")
else:
    st.sidebar.info("Usuário não logado")


# =============================================================================
# CABEÇALHO
# =============================================================================

st.title("⚡ EV Care")
st.caption("Aplicativo para gestão de veículos elétricos")

# Atualiza referências após possíveis mudanças
garagem = []
veiculo_ativo = obter_veiculo_ativo()

if st.session_state.get("auth_logado", False):
    if veiculo_ativo and getattr(veiculo_ativo, "origem_dados", None) == "supabase":
        st.sidebar.success(
            f"Veículo online ativo: {veiculo_ativo.marca} {veiculo_ativo.modelo}"
        )
        st.sidebar.caption(f"KM atual: {veiculo_ativo.km_atual} km")
    else:
        st.sidebar.warning(
            "Nenhum veículo online ativo. Acesse Minha Garagem para cadastrar ou ativar um veículo."
        )

    if st.session_state.get("erro_veiculo_online_ativo"):
        st.sidebar.error(st.session_state.erro_veiculo_online_ativo)

else:
    st.sidebar.info("Faça login para acessar seus dados.")


# =============================================================================
# DASHBOARD
# =============================================================================

if pagina == "Dashboard":
    mostrar_cabecalho_pagina(
        "Dashboard",
        "Resumo geral do veículo, recargas, custos e manutenções."
    )

    if not st.session_state.get("auth_logado", False):
        mostrar_onboarding_beta()
        st.warning("Faça login na página **Conta** para começar.")
        st.stop()

    carregar_veiculo_online_ativo_para_app()

    veiculo_ativo = obter_veiculo_ativo()

    if not veiculo_ativo:
        mostrar_onboarding_beta()

        st.warning(
            "Nenhum veículo cadastrado ainda. Acesse **Minha Garagem** "
            "para cadastrar seu primeiro veículo."
        )

        st.stop()

    if getattr(veiculo_ativo, "origem_dados", None) != "supabase":
        st.warning(
            "Acesse **Minha Garagem** para selecionar um veículo cadastrado na sua conta."
        )
        st.stop()

    if not getattr(veiculo_ativo, "id_online", None):
        st.warning(
            "Não foi possível identificar o veículo ativo. Acesse **Minha Garagem** "
            "e selecione um veículo."
        )
        st.stop()

    garantir_plano_manutencao_expandido(veiculo_ativo)

    st.divider()

    resumo_recargas, erro_resumo_dashboard = obter_resumo_recargas_online(
        veiculo_id=veiculo_ativo.id_online,
        km_atual_veiculo=veiculo_ativo.km_atual
    )

    if erro_resumo_dashboard:
        st.error("Erro ao carregar resumo online de recargas.")
        st.write(erro_resumo_dashboard)

        resumo_recargas = {
            "total_recargas": 0,
            "energia_total": 0,
            "custo_total": 0,
            "custo_medio_recarga": 0,
            "preco_medio_kwh": 0,
            "custo_real_km": None,
            "consumo_real_km_kwh": None,
            "km_rodados": 0
        }

    recargas_online, erro_recargas_dashboard = listar_recargas_online(
        veiculo_ativo.id_online
    )

    if erro_recargas_dashboard:
        st.error("Erro ao carregar última recarga online.")
        st.write(erro_recargas_dashboard)
        recargas_online = []

    ultima_recarga = recargas_online[0] if recargas_online else None

    autonomia = veiculo_ativo.calcular_autonomia()
    saude_bateria = veiculo_ativo.calcular_saude_bateria()

    # ---------------------------------------------------------------------
    # CABEÇALHO DO VEÍCULO
    # ---------------------------------------------------------------------
    with st.container(border=True):
        st.subheader(f"{veiculo_ativo.marca} {veiculo_ativo.modelo}")
        st.caption("Visão geral do veículo ativo")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "KM atual",
                formatar_km(veiculo_ativo.km_atual)
            )

        with col2:
            st.metric(
                "Autonomia estimada",
                f"{autonomia:.0f} km"
            )

        with col3:
            st.metric(
                "Saúde da bateria",
                f"{saude_bateria:.2f}%"
            )

        with col4:
            st.metric(
                "Recargas registradas",
                resumo_recargas["total_recargas"]
            )

        st.caption("Saúde estimada da bateria")
        st.progress(min(max(saude_bateria / 100, 0), 1))

    st.divider()

    # ---------------------------------------------------------------------
    # CUSTOS E EFICIÊNCIA
    # ---------------------------------------------------------------------
    mostrar_bloco_secao(
        "Custos e eficiência",
        "Resumo financeiro e energético com base nas recargas registradas."
    )

    col_custo1, col_custo2, col_custo3, col_custo4 = st.columns(4)

    with col_custo1:
        mostrar_card_metrica(
            "Gasto total em recargas",
            formatar_moeda(resumo_recargas["custo_total"])
        )

    with col_custo2:
        mostrar_card_metrica(
            "Energia total carregada",
            f"{formatar_numero(resumo_recargas['energia_total'], 2)} kWh"
        )

    with col_custo3:
        if resumo_recargas["custo_real_km"] is not None:
            mostrar_card_metrica(
                "Custo real por km",
                f"R$ {resumo_recargas['custo_real_km']:.4f}"
            )
        else:
            mostrar_card_metrica(
                "Custo real por km",
                "Indisponível",
                "Registre recargas e atualize a quilometragem."
            )

    with col_custo4:
        if resumo_recargas["consumo_real_km_kwh"] is not None:
            mostrar_card_metrica(
                "Consumo real",
                f"{resumo_recargas['consumo_real_km_kwh']:.2f} km/kWh"
            )
        else:
            mostrar_card_metrica(
                "Consumo real",
                "Indisponível",
                "Mais dados são necessários para o cálculo."
            )

    if resumo_recargas["custo_real_km"] is None:
        st.info(
            "Para calcular custo real por km, registre uma recarga, use o veículo "
            "e depois atualize a quilometragem."
        )

    st.divider()

    # ---------------------------------------------------------------------
    # ÚLTIMA RECARGA ONLINE
    # ---------------------------------------------------------------------
    mostrar_bloco_secao(
        "Última recarga",
        "Registro mais recente de carregamento do veículo."
    )

    if ultima_recarga:
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)

        with col_r1:
            st.write("**Data**")
            st.write(ultima_recarga.get("data_recarga", "Não informada"))

        with col_r2:
            st.write("**Local**")
            st.write(ultima_recarga.get("local", "Não informado"))

        with col_r3:
            st.write("**Energia**")
            st.write(f"{float(ultima_recarga.get('energia_kwh') or 0):.2f} kWh")

        with col_r4:
            st.write("**Custo**")
            st.write(f"R$ {float(ultima_recarga.get('custo_total') or 0):.2f}")

        st.write(
            f"**Bateria:** "
            f"{float(ultima_recarga.get('bateria_inicial') or 0):.1f}% → "
            f"{float(ultima_recarga.get('bateria_final') or 0):.1f}%"
        )

        st.write(f"**Tipo:** {ultima_recarga.get('tipo', 'Não informado')}")
        st.write(f"**KM no momento da recarga:** {ultima_recarga.get('km_atual', 0)} km")

        if ultima_recarga.get("observacao"):
            st.write(f"**Observação:** {ultima_recarga.get('observacao')}")
    else:
        st.info("Nenhuma recarga online registrada ainda.")

    st.divider()

    # ---------------------------------------------------------------------
    # MANUTENÇÕES E ALERTAS
    # ---------------------------------------------------------------------
    mostrar_bloco_secao(
        "Manutenções e alertas",
        "Acompanhe serviços vencidos, próximos e em dia."
    )

    resumo_manutencao_dashboard, erro_manutencao_dashboard = obter_resumo_manutencoes_online(
        veiculo_id=veiculo_ativo.id_online,
        km_atual=veiculo_ativo.km_atual
    )

    if erro_manutencao_dashboard:
        st.error("Erro ao carregar resumo de manutenções.")
        st.write(erro_manutencao_dashboard)

        resumo_manutencao_dashboard = {
            "itens_status": [],
            "vencidos": [],
            "proximos": [],
            "em_dia": [],
            "total_servicos": 0
        }

    itens_manutencao = resumo_manutencao_dashboard.get("itens_status", [])
    vencidos = resumo_manutencao_dashboard.get("vencidos", [])
    proximos = resumo_manutencao_dashboard.get("proximos", [])
    em_dia = resumo_manutencao_dashboard.get("em_dia", [])

    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        st.metric("Vencidas", len(vencidos))

    with col_m2:
        st.metric("Próximas", len(proximos))

    with col_m3:
        st.metric("Em dia", len(em_dia))

    if vencidos:
        st.error("Existem manutenções vencidas.")
    elif proximos:
        st.warning("Existem manutenções próximas.")
    elif itens_manutencao:
        st.success("Todas as manutenções estão em dia.")
    else:
        st.info("Nenhum serviço de manutenção cadastrado.")

    # ---------------------------------------------------------------------
    # PRÓXIMA MANUTENÇÃO MAIS IMPORTANTE
    # ---------------------------------------------------------------------
    mostrar_bloco_secao(
        "Próxima manutenção relevante",
        "Serviço mais urgente conforme quilometragem e plano de manutenção."
    )

    if itens_manutencao:
        servico_mais_relevante, dados_mais_relevante = itens_manutencao[0]

        with st.container(border=True):
            col_p1, col_p2, col_p3 = st.columns(3)

            with col_p1:
                st.write("**Serviço**")
                st.write(servico_mais_relevante.get("nome", "Não informado"))

            with col_p2:
                st.write("**Status**")
                st.write(dados_mais_relevante.get("status", "Não informado"))

            with col_p3:
                st.write("**Próxima em**")
                st.write(f"{dados_mais_relevante.get('proxima_km', 0)} km")

            st.write(f"**Categoria:** {dados_mais_relevante.get('categoria', 'Geral')}")
            st.write(f"**Criticidade:** {dados_mais_relevante.get('criticidade', 'Média')}")

            km_restante = dados_mais_relevante.get("km_restante", 0)

            if km_restante >= 0:
                st.write(f"Faltam **{km_restante} km**")
            else:
                st.write(f"Vencida há **{abs(km_restante)} km**")

            if dados_mais_relevante.get("descricao"):
                st.caption(dados_mais_relevante.get("descricao"))
    else:
        st.info("Nenhum item de manutenção cadastrado no plano.")

    st.divider()

    # ---------------------------------------------------------------------
    # LISTA RESUMIDA DE ALERTAS
    # ---------------------------------------------------------------------
    mostrar_bloco_secao(
        "Resumo dos principais alertas",
        "Lista rápida dos alertas mais importantes no momento."
    )

    if vencidos or proximos:
        for servico, dados in itens_manutencao[:5]:
            nome_servico = servico.get("nome", "Serviço não informado")
            status_servico = dados.get("status", "Não informado")
            km_restante = dados.get("km_restante", 0)
            proxima_km = dados.get("proxima_km", 0)

            if status_servico == "Vencido":
                st.error(
                    f"{nome_servico}: vencida há {abs(km_restante)} km "
                    f"(próxima era em {proxima_km} km)."
                )
            elif status_servico == "Próximo":
                st.warning(
                    f"{nome_servico}: próxima em {proxima_km} km "
                    f"(faltam {km_restante} km)."
                )
    elif itens_manutencao:
        st.success("Nenhum alerta crítico no momento.")
    else:
        st.info("Nenhum serviço de manutenção cadastrado.")

    # ---------------------------------------------------------------------
    # AÇÕES RÁPIDAS
    # ---------------------------------------------------------------------
    st.subheader("Ações rápidas recomendadas")

    col_a1, col_a2, col_a3 = st.columns(3)

    with col_a1:
        st.info("Para registrar uma nova recarga, acesse **Recargas**.")

    with col_a2:
        st.info("Para atualizar a KM, acesse **Quilometragem**.")

    with col_a3:
        st.info("Para lançar serviços realizados, acesse **Manutenções**.")

    st.caption(
        "Este dashboard usa os dados salvos da garagem, recargas, quilometragem "
        "e plano de manutenção do veículo ativo."
    )
    st.subheader("Orientações rápidas")

    if not recargas_online:
        st.info(
            "Registre sua primeira recarga em **Recargas** para calcular gasto total, "
            "preço médio do kWh, custo real por km e consumo real."
        )

    if resumo_recargas["custo_real_km"] is None and recargas_online:
        st.info(
            "Para melhorar o cálculo de custo real por km, registre recargas "
            "e mantenha a quilometragem atualizada."
        )

    if resumo_recargas["consumo_real_km_kwh"] is None and recargas_online:
        st.info(
            "O consumo real será calculado com mais precisão conforme você registrar "
            "recargas e atualizar a quilometragem."
        )
    st.divider()

    st.caption(
        "Este dashboard usa os dados salvos da garagem, recargas, quilometragem "
        "e plano de manutenção do veículo ativo."
    )

    st.divider()

    mostrar_bloco_secao(
        "Relatório do veículo",
        "Usuários Plus podem baixar um PDF com o resumo do veículo."
    )

    if recurso_disponivel("exportacao_pdf"):
        resumo_manutencao_pdf, erro_manutencao_pdf = obter_resumo_manutencoes_online(
            veiculo_id=veiculo_ativo.id_online,
            km_atual=veiculo_ativo.km_atual
        )

        if erro_manutencao_pdf:
            st.error("Não foi possível carregar os dados de manutenção para o relatório.")
            st.write(erro_manutencao_pdf)
        else:
            pdf_relatorio = gerar_pdf_resumo_veiculo(
                veiculo=veiculo_ativo,
                resumo_recargas=resumo_recargas,
                resumo_manutencao=resumo_manutencao_pdf
            )

            nome_arquivo_pdf = (
                f"ev_care_relatorio_"
                f"{veiculo_ativo.marca}_{veiculo_ativo.modelo}.pdf"
            )

            nome_arquivo_pdf = nome_arquivo_pdf.replace(" ", "_").lower()

            st.download_button(
                label="Baixar relatório PDF",
                data=pdf_relatorio,
                file_name=nome_arquivo_pdf,
                mime="application/pdf"
            )

            st.caption(
                "O relatório PDF reúne dados do veículo, recargas e manutenções."
            )
    else:
        exibir_bloqueio_plus("exportacao_pdf")

    
    st.divider()

    mostrar_bloco_secao(
        "Relatório mensal",
        "Resumo mensal de recargas, quilometragem e manutenções para usuários Plus."
    )

    if recurso_disponivel("relatorios_mensais"):
        meses = {
            1: "Janeiro",
            2: "Fevereiro",
            3: "Março",
            4: "Abril",
            5: "Maio",
            6: "Junho",
            7: "Julho",
            8: "Agosto",
            9: "Setembro",
            10: "Outubro",
            11: "Novembro",
            12: "Dezembro",
        }

        hoje = date.today()

        col_mes, col_ano = st.columns(2)

        with col_mes:
            mes_relatorio = st.selectbox(
                "Mês",
                list(meses.keys()),
                format_func=lambda m: meses[m],
                index=hoje.month - 1
            )

        with col_ano:
            ano_relatorio = st.number_input(
                "Ano",
                min_value=2020,
                max_value=2100,
                value=hoje.year,
                step=1
            )

        resumo_mensal, erro_resumo_mensal = calcular_resumo_mensal_online(
            veiculo_ativo,
            int(ano_relatorio),
            int(mes_relatorio)
        )

        if erro_resumo_mensal:
            st.error("Não foi possível gerar o relatório mensal.")
            st.write(erro_resumo_mensal)
        else:
            st.write(
                f"Resumo de **{meses[int(mes_relatorio)]}/{int(ano_relatorio)}**"
            )

            col_rm1, col_rm2, col_rm3, col_rm4 = st.columns(4)

            with col_rm1:
                st.metric(
                    "Recargas no mês",
                    resumo_mensal["total_recargas"]
                )

            with col_rm2:
                st.metric(
                    "Energia carregada",
                    f"{resumo_mensal['energia_total']:.2f} kWh"
                )

            with col_rm3:
                st.metric(
                    "Gasto no mês",
                    f"R$ {resumo_mensal['custo_total']:.2f}"
                )

            with col_rm4:
                st.metric(
                    "Preço médio kWh",
                    f"R$ {resumo_mensal['preco_medio_kwh']:.2f}"
                )

            col_rm5, col_rm6, col_rm7 = st.columns(3)

            with col_rm5:
                st.metric(
                    "Registros de KM",
                    resumo_mensal["total_registros_km"]
                )

            with col_rm6:
                st.metric(
                    "KM registrados no mês",
                    f"{resumo_mensal['km_registrados_mes']} km"
                )

            with col_rm7:
                st.metric(
                    "Manutenções realizadas",
                    resumo_mensal["total_manutencoes"]
                )

            if resumo_mensal["custo_por_km_mes"] is not None:
                st.success(
                    f"Custo aproximado por km no mês: "
                    f"R$ {resumo_mensal['custo_por_km_mes']:.4f}"
                )
            else:
                st.info(
                    "Para calcular custo por km no mês, registre recargas "
                    "e atualizações de quilometragem no mesmo período."
                )

            st.divider()

            st.write("### Exportar relatório mensal")

            pdf_mensal = gerar_pdf_relatorio_mensal(
                veiculo=veiculo_ativo,
                resumo_mensal=resumo_mensal,
                mes_nome=meses[int(mes_relatorio)],
                ano=int(ano_relatorio)
                )

            nome_arquivo_pdf_mensal = (
                f"ev_care_relatorio_mensal_"
                f"{veiculo_ativo.marca}_{veiculo_ativo.modelo}_"
                f"{int(mes_relatorio)}_{int(ano_relatorio)}.pdf"
            )

            nome_arquivo_pdf_mensal = (
                nome_arquivo_pdf_mensal
                .replace(" ", "_")
                .replace("/", "_")
                .lower()
            )

            st.download_button(
                label="Baixar relatório mensal em PDF",
                data=pdf_mensal,
                file_name=nome_arquivo_pdf_mensal,
                mime="application/pdf"
            )

            st.caption(
                "O PDF mensal reúne recargas, quilometragem e manutenções "
                "do mês selecionado."
            )

            if (
                resumo_mensal["total_recargas"] == 0
                and resumo_mensal["total_registros_km"] == 0
                and resumo_mensal["total_manutencoes"] == 0
            ):
                st.info(
                    "Nenhum dado encontrado para o mês selecionado."
                )
    else:
        exibir_bloqueio_plus("relatorios_mensais")



# =============================================================================
# QUILOMETRAGEM
# =============================================================================
elif pagina == "Quilometragem":
    mostrar_cabecalho_pagina(
        "Quilometragem",
        "Atualize e acompanhe o histórico de quilometragem do veículo."
    )

    if not validar_contexto_online("Quilometragem"):
        st.stop()

    veiculo_ativo = obter_veiculo_ativo()


    with st.container(border=True):
        st.subheader(f"{veiculo_ativo.marca} {veiculo_ativo.modelo}")
        st.caption("Veículo ativo para atualização e acompanhamento de quilometragem.")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("KM atual", formatar_km(veiculo_ativo.km_atual))

        with col2:
            st.metric(
                "Autonomia estimada",
                f"{veiculo_ativo.calcular_autonomia():.0f} km"
            )

        with col3:
            st.metric(
                "Saúde estimada da bateria",
                f"{veiculo_ativo.calcular_saude_bateria():.2f}%"
            )

    st.divider()

    mostrar_bloco_secao(
        "Atualizar quilometragem",
        "Informe a nova quilometragem para manter custos, histórico e manutenções atualizados."
    )

    with st.form("form_atualizar_quilometragem_online"):
        nova_km = st.number_input(
            "Nova quilometragem",
            min_value=0,
            step=100,
            value=int(veiculo_ativo.km_atual)
        )

        confirmar = st.form_submit_button("Atualizar KM")

        if confirmar:
            if nova_km < veiculo_ativo.km_atual:
                st.error(
                    f"A nova KM deve ser maior ou igual à atual "
                    f"({veiculo_ativo.km_atual} km)."
                )
            elif nova_km == veiculo_ativo.km_atual:
                st.info(
                    "A quilometragem informada é igual à atual. "
                    "Nenhuma alteração foi feita."
                )
            else:
                ok, mensagem = atualizar_km_veiculo_online(
                    user_id=st.session_state.auth_user_id,
                    veiculo_id=veiculo_ativo.id_online,
                    km_anterior=veiculo_ativo.km_atual,
                    km_nova=nova_km
                )

                if ok:
                    st.success(mensagem)
                    carregar_veiculo_online_ativo_para_app()
                    st.rerun()
                else:
                    st.error("Não foi possível atualizar a quilometragem online.")
                    st.write(mensagem)

    st.divider()

    mostrar_bloco_secao(
        "Histórico de quilometragem",
        "Consulte as atualizações de KM registradas para este veículo."
    )

    historico_online, erro_historico = listar_historico_km_online(
        veiculo_ativo.id_online
    )

    if erro_historico:
        st.error("Erro ao carregar histórico online de quilometragem.")
        st.write(erro_historico)
    elif not historico_online:
        st.info("Ainda não há registros online de alteração de quilometragem.")
    else:
        for registro in historico_online:
            km_anterior = int(registro.get("km_anterior", 0))
            km_nova = int(registro.get("km_nova", 0))
            diferenca = km_nova - km_anterior

            with st.container(border=True):
                st.write(f"**Data:** {registro.get('data_registro', 'Não informada')}")
                st.write(f"**KM anterior:** {km_anterior} km")
                st.write(f"**Nova KM:** {km_nova} km")

                if diferenca >= 0:
                    st.write(f"**Diferença registrada:** {diferenca} km")
    
    st.divider()

    mostrar_bloco_secao(
        "Exportação de quilometragem",
        "Usuários Plus podem baixar o histórico de KM em CSV para análise em planilhas."
    )

    if recurso_disponivel("exportacao_excel"):
        historico_exportacao, erro_exportacao = listar_historico_km_online(
            veiculo_ativo.id_online
        )

        if erro_exportacao:
            st.error("Não foi possível carregar a quilometragem para exportação.")
            st.write(erro_exportacao)
        elif not historico_exportacao:
            st.info("Ainda não há registros de quilometragem para exportar.")
        else:
            csv_quilometragem = gerar_csv_quilometragem(historico_exportacao)

            nome_arquivo_csv = (
                f"ev_care_quilometragem_"
                f"{veiculo_ativo.marca}_{veiculo_ativo.modelo}.csv"
            )

            nome_arquivo_csv = nome_arquivo_csv.replace(" ", "_").lower()

            st.download_button(
                label="Baixar quilometragem em CSV",
                data=csv_quilometragem,
                file_name=nome_arquivo_csv,
                mime="text/csv"
            )

            st.caption(
                "O arquivo CSV pode ser aberto no Excel, Google Planilhas "
                "ou outros aplicativos de planilha."
            )
    else:
        exibir_bloqueio_plus("exportacao_excel")

# =============================================================================
# RECARGAS
# =============================================================================

elif pagina == "Recargas":
    mostrar_cabecalho_pagina(
        "Recargas",
        "Registre recargas, acompanhe custos e exporte seus dados."
    )

    if not validar_contexto_online("Recargas"):
        st.stop()

    veiculo_ativo = obter_veiculo_ativo()

    st.caption("Registre e acompanhe suas recargas, custos e histórico de carregamento.")
    with st.container(border=True):
        st.subheader(f"{veiculo_ativo.marca} {veiculo_ativo.modelo}")
        st.caption("Veículo ativo para registro e acompanhamento de recargas.")

        col_v1, col_v2, col_v3 = st.columns(3)

        with col_v1:
            st.metric("KM atual", formatar_km(veiculo_ativo.km_atual))

        with col_v2:
            st.metric(
                "Autonomia estimada",
                f"{veiculo_ativo.calcular_autonomia():.0f} km"
            )

        with col_v3:
            st.metric(
                "Saúde da bateria",
                f"{veiculo_ativo.calcular_saude_bateria():.2f}%"
            )

    st.divider()
    tab1, tab2, tab3 = st.tabs(
        [
            "Registrar recarga",
            "Histórico / Editar / Excluir",
            "Resumo"
        ]
    )

    # -------------------------------------------------------------------------
    # REGISTRAR RECARGA ONLINE
    # -------------------------------------------------------------------------
    with tab1:
        mostrar_bloco_secao(
            "Registrar nova recarga",
            "Informe os dados da recarga para acompanhar custos, energia e histórico."
        )
        with st.form("form_registrar_recarga_online"):
            bateria_inicial = st.number_input(
                "Bateria inicial (%)",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key="online_bateria_inicial"
            )

            bateria_final = st.number_input(
                "Bateria final (%)",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key="online_bateria_final"
            )

            energia_kwh = st.number_input(
                "Energia carregada (kWh)",
                min_value=0.01,
                step=0.1,
                key="online_energia_kwh"
            )

            preco_kwh = st.number_input(
                "Preço do kWh (R$)",
                min_value=0.0,
                step=0.01,
                value=0.63,
                key="online_preco_kwh"
            )

            local = st.text_input(
                "Local da recarga",
                key="online_local_recarga"
            )

            tipo = st.selectbox(
                "Tipo de recarga",
                [
                    "Residencial",
                    "Pública lenta",
                    "Pública rápida",
                    "Gratuita",
                    "Outro"
                ],
                key="online_tipo_recarga"
            )

            observacao = st.text_area(
                "Observação",
                key="online_observacao_recarga"
            )

            salvar_recarga = st.form_submit_button("Registrar recarga online")

            if salvar_recarga:
                if bateria_final < bateria_inicial:
                    st.error("A bateria final não pode ser menor que a bateria inicial.")
                elif energia_kwh <= 0:
                    st.error("Informe uma energia carregada maior que zero.")
                else:
                    ok, resposta = registrar_recarga_online(
                        user_id=st.session_state.auth_user_id,
                        veiculo_id=veiculo_ativo.id_online,
                        km_atual=veiculo_ativo.km_atual,
                        bateria_inicial=bateria_inicial,
                        bateria_final=bateria_final,
                        energia_kwh=energia_kwh,
                        preco_kwh=preco_kwh,
                        local=local,
                        tipo=tipo,
                        observacao=observacao
                    )

                    if ok:
                        st.success(
                            f"Recarga online registrada. "
                            f"Custo total: R$ {energia_kwh * preco_kwh:.2f}"
                        )
                        st.rerun()
                    else:
                        st.error("Não foi possível registrar a recarga online.")
                        st.write(resposta)

    # -------------------------------------------------------------------------
    # HISTÓRICO, EDITAR E EXCLUIR ONLINE
    # -------------------------------------------------------------------------
    with tab2:
        mostrar_bloco_secao(
            "Histórico de recargas",
            "Consulte, edite ou remova registros de recarga do veículo."
        )

        recargas_online, erro_recargas = listar_recargas_online(
            veiculo_ativo.id_online
        )

        if erro_recargas:
            st.error("Erro ao carregar recargas online.")
            st.write(erro_recargas)
        elif not recargas_online:
            st.info("Nenhuma recarga online registrada.")
        else:
            for i, r in enumerate(recargas_online, 1):
                titulo = (
                    f"Recarga {i} - "
                    f"{r.get('data_recarga', 'Data não informada')} - "
                    f"{r.get('local', 'Local não informado')}"
                )

                with st.expander(titulo):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.write("**Data**")
                        st.write(r.get("data_recarga", "Não informada"))

                    with col2:
                        st.write("**Bateria**")
                        st.write(
                            f"{float(r.get('bateria_inicial') or 0):.1f}% → "
                            f"{float(r.get('bateria_final') or 0):.1f}%"
                        )

                    with col3:
                        st.write("**Energia**")
                        st.write(f"{float(r.get('energia_kwh') or 0):.2f} kWh")

                    with col4:
                        st.write("**Custo**")
                        st.write(f"R$ {float(r.get('custo_total') or 0):.2f}")

                    st.write(f"**Preço do kWh:** R$ {float(r.get('preco_kwh') or 0):.2f}")
                    st.write(f"**Local:** {r.get('local', 'Não informado')}")
                    st.write(f"**Tipo:** {r.get('tipo', 'Não informado')}")
                    st.write(f"**KM no momento da recarga:** {r.get('km_atual', 0)} km")

                    if r.get("observacao"):
                        st.write(f"**Observação:** {r.get('observacao')}")

                    st.divider()

                    # ---------------------------------------------------------
                    # EDITAR RECARGA ONLINE
                    # ---------------------------------------------------------
                    st.write("### Editar esta recarga")

                    with st.form(f"form_editar_recarga_online_{r.get('id')}"):
                        nova_bateria_inicial = st.number_input(
                            "Bateria inicial (%)",
                            min_value=0.0,
                            max_value=100.0,
                            step=1.0,
                            value=float(r.get("bateria_inicial") or 0),
                            key=f"editar_online_bateria_inicial_{r.get('id')}"
                        )

                        nova_bateria_final = st.number_input(
                            "Bateria final (%)",
                            min_value=0.0,
                            max_value=100.0,
                            step=1.0,
                            value=float(r.get("bateria_final") or 0),
                            key=f"editar_online_bateria_final_{r.get('id')}"
                        )

                        nova_energia_kwh = st.number_input(
                            "Energia carregada (kWh)",
                            min_value=0.01,
                            step=0.1,
                            value=float(r.get("energia_kwh") or 0.01),
                            key=f"editar_online_energia_{r.get('id')}"
                        )

                        novo_preco_kwh = st.number_input(
                            "Preço do kWh (R$)",
                            min_value=0.0,
                            step=0.01,
                            value=float(r.get("preco_kwh") or 0),
                            key=f"editar_online_preco_{r.get('id')}"
                        )

                        novo_local = st.text_input(
                            "Local da recarga",
                            value=r.get("local", ""),
                            key=f"editar_online_local_{r.get('id')}"
                        )

                        tipos_recarga = [
                            "Residencial",
                            "Pública lenta",
                            "Pública rápida",
                            "Gratuita",
                            "Outro"
                        ]

                        tipo_atual = r.get("tipo", "Outro")

                        if tipo_atual in tipos_recarga:
                            indice_tipo = tipos_recarga.index(tipo_atual)
                        else:
                            indice_tipo = 4

                        novo_tipo = st.selectbox(
                            "Tipo de recarga",
                            tipos_recarga,
                            index=indice_tipo,
                            key=f"editar_online_tipo_{r.get('id')}"
                        )

                        nova_observacao = st.text_area(
                            "Observação",
                            value=r.get("observacao", ""),
                            key=f"editar_online_observacao_{r.get('id')}"
                        )

                        novo_custo_total = nova_energia_kwh * novo_preco_kwh

                        st.info(f"Custo total recalculado: R$ {novo_custo_total:.2f}")

                        confirmar_edicao = st.form_submit_button(
                            "Salvar alterações desta recarga"
                        )

                        if confirmar_edicao:
                            if nova_bateria_final < nova_bateria_inicial:
                                st.error("A bateria final não pode ser menor que a inicial.")
                            else:
                                ok, resposta = editar_recarga_online(
                                    recarga_id=r.get("id"),
                                    bateria_inicial=nova_bateria_inicial,
                                    bateria_final=nova_bateria_final,
                                    energia_kwh=nova_energia_kwh,
                                    preco_kwh=novo_preco_kwh,
                                    local=novo_local,
                                    tipo=novo_tipo,
                                    observacao=nova_observacao
                                )

                                if ok:
                                    st.success("Recarga online editada com sucesso.")
                                    st.rerun()
                                else:
                                    st.error("Não foi possível editar a recarga online.")
                                    st.write(resposta)

                    st.divider()

                    # ---------------------------------------------------------
                    # EXCLUIR RECARGA ONLINE
                    # ---------------------------------------------------------
                    st.write("### Excluir esta recarga")

                    confirmar_exclusao = st.checkbox(
                        "Confirmo que desejo excluir esta recarga",
                        key=f"confirmar_excluir_online_{r.get('id')}"
                    )

                    if st.button(
                        "Excluir recarga online",
                        key=f"botao_excluir_recarga_online_{r.get('id')}"
                    ):
                        if confirmar_exclusao:
                            ok, resposta = excluir_recarga_online(r.get("id"))

                            if ok:
                                st.success("Recarga online excluída com sucesso.")
                                st.rerun()
                            else:
                                st.error("Não foi possível excluir a recarga online.")
                                st.write(resposta)
                        else:
                            st.warning("Marque a confirmação antes de excluir.")

    # -------------------------------------------------------------------------
    # RESUMO ONLINE
    # -------------------------------------------------------------------------
    with tab3:
        mostrar_bloco_secao(
            "Resumo de recargas",
            "Veja indicadores consolidados de energia, custo e consumo."
        )

        resumo, erro_resumo = obter_resumo_recargas_online(
            veiculo_id=veiculo_ativo.id_online,
            km_atual_veiculo=veiculo_ativo.km_atual
        )

        if erro_resumo:
            st.error("Erro ao calcular resumo online de recargas.")
            st.write(erro_resumo)
        else:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total de recargas", resumo["total_recargas"])

            with col2:
                st.metric("Energia total", f"{resumo['energia_total']:.2f} kWh")

            with col3:
                st.metric("Gasto total", f"R$ {resumo['custo_total']:.2f}")

            col4, col5, col6 = st.columns(3)

            with col4:
                st.metric(
                    "Custo médio por recarga",
                    f"R$ {resumo['custo_medio_recarga']:.2f}"
                )

            with col5:
                st.metric(
                    "Preço médio kWh",
                    f"R$ {resumo['preco_medio_kwh']:.2f}"
                )

            with col6:
                if resumo["custo_real_km"] is not None:
                    st.metric(
                        "Custo real por km",
                        f"R$ {resumo['custo_real_km']:.4f}"
                    )
                else:
                    st.metric("Custo real por km", "Indisponível")

            if resumo["consumo_real_km_kwh"] is not None:
                st.success(
                    f"Consumo real aproximado: "
                    f"{resumo['consumo_real_km_kwh']:.2f} km/kWh"
                )
                st.write(
                    f"KM considerados desde a primeira recarga: "
                    f"{resumo['km_rodados']} km"
                )
            else:
                st.info(
                    "Para calcular consumo real, registre recargas e atualize "
                    "a quilometragem após usar o veículo."
                )
    
        st.divider()

        mostrar_bloco_secao(
            "Exportação de recargas",
            "Usuários Plus podem baixar os registros em CSV para análise em planilhas."
        )

        if recurso_disponivel("exportacao_excel"):
            recargas_para_exportar, erro_exportacao = listar_recargas_online(
                veiculo_ativo.id_online
            )

            if erro_exportacao:
                st.error("Não foi possível carregar as recargas para exportação.")
                st.write(erro_exportacao)
            elif not recargas_para_exportar:
                st.info("Ainda não há recargas para exportar.")
            else:
                csv_recargas = gerar_csv_recargas(recargas_para_exportar)

                nome_arquivo_csv = (
                    f"ev_care_recargas_"
                    f"{veiculo_ativo.marca}_{veiculo_ativo.modelo}.csv"
                )

                nome_arquivo_csv = nome_arquivo_csv.replace(" ", "_").lower()

                st.download_button(
                    label="Baixar recargas em CSV",
                    data=csv_recargas,
                    file_name=nome_arquivo_csv,
                    mime="text/csv"
                )

                st.caption(
                    "O arquivo CSV pode ser aberto no Excel, Google Planilhas "
                    "ou outros aplicativos de planilha."
                )
        else:
            exibir_bloqueio_plus("exportacao_excel")



# =============================================================================
# MANUTENÇÕES
# =============================================================================

elif pagina == "Manutenções":
    mostrar_cabecalho_pagina(
        "Manutenções",
        "Acompanhe serviços, prazos e histórico de manutenção."
    )

    if not validar_contexto_online("Manutenções"):
        st.stop()

    veiculo_ativo = obter_veiculo_ativo()

    with st.container(border=True):
        st.subheader(f"{veiculo_ativo.marca} {veiculo_ativo.modelo}")
        st.caption("Veículo ativo para controle de plano e histórico de manutenção.")

        col_v1, col_v2, col_v3 = st.columns(3)

        with col_v1:
            st.metric("KM atual", formatar_km(veiculo_ativo.km_atual))

        with col_v2:
            st.metric(
                "Autonomia estimada",
                f"{veiculo_ativo.calcular_autonomia():.0f} km"
            )

        with col_v3:
            st.metric(
                "Saúde da bateria",
                f"{veiculo_ativo.calcular_saude_bateria():.2f}%"
            )

    st.divider()


    servicos_online, erro_servicos = listar_servicos_manutencao_online(
        veiculo_ativo.id_online
    )

    if erro_servicos:
        st.error("Erro ao carregar o plano de manutenção.")
        st.write(erro_servicos)
        st.stop()

    if not servicos_online:
        ok_plano, resposta_plano = criar_plano_padrao_manutencao_online(
            user_id=st.session_state.auth_user_id,
            veiculo_id=veiculo_ativo.id_online,
            km_atual=veiculo_ativo.km_atual
        )

        if ok_plano:
            st.info("Plano de manutenção criado para este veículo.")
            st.rerun()
        else:
            st.error("Não foi possível criar o plano de manutenção.")
            st.write(resposta_plano)
            st.stop()

    resumo_manutencao, erro_resumo_manutencao = obter_resumo_manutencoes_online(
        veiculo_id=veiculo_ativo.id_online,
        km_atual=veiculo_ativo.km_atual
    )

    if erro_resumo_manutencao:
        st.error("Erro ao calcular o resumo de manutenção.")
        st.write(erro_resumo_manutencao)
        st.stop()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Painel",
            "Registrar Manutenção",
            "Plano Manual",
            "Histórico"
        ]
    )

    # -------------------------------------------------------------------------
    # PAINEL
    # -------------------------------------------------------------------------
    with tab1:
        mostrar_bloco_secao(
            "Painel de manutenção",
            "Acompanhe serviços vencidos, próximos e em dia."
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de serviços", resumo_manutencao["total_servicos"])

        with col2:
            st.metric("Vencidos", len(resumo_manutencao["vencidos"]))

        with col3:
            st.metric("Próximos", len(resumo_manutencao["proximos"]))

        with col4:
            st.metric("Em dia", len(resumo_manutencao["em_dia"]))

        st.divider()

        if not resumo_manutencao["itens_status"]:
            st.info("Nenhum serviço de manutenção cadastrado.")
        else:
            for servico, dados in resumo_manutencao["itens_status"]:
                with st.container(border=True):
                    col_a, col_b, col_c = st.columns(3)

                    with col_a:
                        st.write(f"### {servico.get('nome', 'Serviço não informado')}")
                        st.write(f"Categoria: **{dados['categoria']}**")
                        st.write(f"Criticidade: **{dados['criticidade']}**")

                    with col_b:
                        st.write(f"Status: **{dados['status']}**")
                        st.write(f"Intervalo: **{dados['intervalo_km']} km**")

                        if dados["intervalo_meses"]:
                            st.write(f"Tempo: **{dados['intervalo_meses']} meses**")

                    with col_c:
                        st.write(f"Última feita em: **{dados['ultima_km']} km**")
                        st.write(f"Próxima em: **{dados['proxima_km']} km**")

                        if dados["km_restante"] >= 0:
                            st.write(f"Faltam: **{dados['km_restante']} km**")
                        else:
                            st.write(f"Vencida há: **{abs(dados['km_restante'])} km**")

                    if dados["descricao"]:
                        st.caption(dados["descricao"])

                    if dados["status"] == "Vencido":
                        st.error("Status: Vencido")
                    elif dados["status"] == "Próximo":
                        st.warning("Status: Próximo")
                    else:
                        st.success("Status: Em dia")

    # -------------------------------------------------------------------------
    # REGISTRAR MANUTENÇÃO
    # -------------------------------------------------------------------------
    with tab2:
        mostrar_bloco_secao(
            "Registrar manutenção realizada",
            "Lance serviços concluídos para atualizar automaticamente os próximos prazos."
        )

        servicos_ativos = resumo_manutencao["servicos"]

        if not servicos_ativos:
            st.info("Nenhum serviço disponível para registrar.")
        else:
            nomes_servicos = [
                servico.get("nome", "Serviço sem nome")
                for servico in servicos_ativos
            ]

            indice_servico = st.selectbox(
                "Serviço realizado",
                range(len(servicos_ativos)),
                format_func=lambda i: nomes_servicos[i],
                key="indice_servico_manutencao_online"
            )

            servico_escolhido = servicos_ativos[indice_servico]

            status_servico = None

            for servico, dados in resumo_manutencao["itens_status"]:
                if servico.get("id") == servico_escolhido.get("id"):
                    status_servico = dados
                    break

            if status_servico:
                st.info(
                    f"Serviço: {servico_escolhido.get('nome')} | "
                    f"Status atual: {status_servico['status']} | "
                    f"KM atual: {veiculo_ativo.km_atual} km | "
                    f"Próxima prevista em: {status_servico['proxima_km']} km"
                )

            observacao_manutencao = st.text_area(
                "Observação da manutenção",
                key="observacao_manutencao_online"
            )

            if st.button("Registrar manutenção"):
                ok, resposta = registrar_manutencao_online(
                    user_id=st.session_state.auth_user_id,
                    veiculo_id=veiculo_ativo.id_online,
                    servico_id=servico_escolhido.get("id"),
                    nome_servico=servico_escolhido.get("nome"),
                    km_realizada=veiculo_ativo.km_atual,
                    observacao=observacao_manutencao
                )

                if ok:
                    st.success(
                        "Manutenção registrada com sucesso. "
                        "O cálculo da próxima manutenção foi atualizado."
                    )
                    st.rerun()
                else:
                    st.error("Não foi possível registrar a manutenção.")
                    st.write(resposta)

    # -------------------------------------------------------------------------
    # PLANO MANUAL
    # -------------------------------------------------------------------------
    with tab3:
        mostrar_bloco_secao(
            "Plano manual de manutenção",
            "Adicione, edite ou remova serviços personalizados do plano do veículo."
        )

        subtab1, subtab2, subtab3 = st.tabs(
            [
                "Adicionar serviço",
                "Editar serviço",
                "Remover serviço"
            ]
        )

        # ---------------------------------------------------------------------
        # ADICIONAR SERVIÇO
        # ---------------------------------------------------------------------
        with subtab1:
            st.write(
                "Adicione serviços personalizados ao plano de manutenção deste veículo."
            )

            with st.form("form_adicionar_servico_online"):
                nome_servico = st.text_input("Nome do serviço")

                categoria = st.text_input(
                    "Categoria",
                    value="Personalizado"
                )

                intervalo_km = st.number_input(
                    "Intervalo em km",
                    min_value=1,
                    step=1000,
                    value=10000
                )

                intervalo_meses = st.number_input(
                    "Intervalo em meses",
                    min_value=0,
                    step=1,
                    value=12
                )

                criticidade = st.selectbox(
                    "Criticidade",
                    ["Baixa", "Média", "Alta"],
                    index=1
                )

                descricao = st.text_area(
                    "Descrição / observações",
                    value="Serviço personalizado adicionado pelo usuário."
                )

                adicionar = st.form_submit_button("Adicionar serviço")

                if adicionar:
                    nome_limpo = nome_servico.strip()

                    if not nome_limpo:
                        st.error("Informe o nome do serviço.")
                    else:
                        ok, resposta = criar_servico_manutencao_online(
                            user_id=st.session_state.auth_user_id,
                            veiculo_id=veiculo_ativo.id_online,
                            nome=nome_limpo,
                            categoria=categoria.strip() if categoria.strip() else "Personalizado",
                            intervalo_km=intervalo_km,
                            intervalo_meses=intervalo_meses,
                            criticidade=criticidade,
                            descricao=descricao.strip(),
                            ultima_km=0
                        )

                        if ok:
                            st.success("Serviço adicionado com sucesso.")
                            st.rerun()
                        else:
                            st.error("Não foi possível adicionar o serviço.")
                            st.write(resposta)

        # ---------------------------------------------------------------------
        # EDITAR SERVIÇO
        # ---------------------------------------------------------------------
        with subtab2:
            servicos_ativos = resumo_manutencao["servicos"]

            if not servicos_ativos:
                st.info("Nenhum serviço disponível para edição.")
            else:
                nomes_edicao = [
                    servico.get("nome", "Serviço sem nome")
                    for servico in servicos_ativos
                ]

                indice_edicao = st.selectbox(
                    "Selecione o serviço para editar",
                    range(len(servicos_ativos)),
                    format_func=lambda i: nomes_edicao[i],
                    key="indice_edicao_servico_online"
                )

                servico_edicao = servicos_ativos[indice_edicao]

                with st.form("form_editar_servico_online"):
                    novo_nome = st.text_input(
                        "Nome do serviço",
                        value=servico_edicao.get("nome", "")
                    )

                    nova_categoria = st.text_input(
                        "Categoria",
                        value=servico_edicao.get("categoria", "Geral")
                    )

                    novo_intervalo_km = st.number_input(
                        "Intervalo em km",
                        min_value=1,
                        step=1000,
                        value=int(servico_edicao.get("intervalo_km", 10000))
                    )

                    novo_intervalo_meses = st.number_input(
                        "Intervalo em meses",
                        min_value=0,
                        step=1,
                        value=int(servico_edicao.get("intervalo_meses", 0))
                    )

                    opcoes_criticidade = ["Baixa", "Média", "Alta"]
                    criticidade_atual = servico_edicao.get("criticidade", "Média")

                    if criticidade_atual in opcoes_criticidade:
                        indice_criticidade = opcoes_criticidade.index(criticidade_atual)
                    else:
                        indice_criticidade = 1

                    nova_criticidade = st.selectbox(
                        "Criticidade",
                        opcoes_criticidade,
                        index=indice_criticidade
                    )

                    nova_descricao = st.text_area(
                        "Descrição",
                        value=servico_edicao.get("descricao", "")
                    )

                    salvar_edicao = st.form_submit_button("Salvar alterações")

                    if salvar_edicao:
                        if not novo_nome.strip():
                            st.error("O nome do serviço não pode ficar vazio.")
                        else:
                            ok, resposta = editar_servico_manutencao_online(
                                servico_id=servico_edicao.get("id"),
                                nome=novo_nome.strip(),
                                categoria=nova_categoria.strip() if nova_categoria.strip() else "Geral",
                                intervalo_km=novo_intervalo_km,
                                intervalo_meses=novo_intervalo_meses,
                                criticidade=nova_criticidade,
                                descricao=nova_descricao.strip()
                            )

                            if ok:
                                st.success("Serviço atualizado com sucesso.")
                                st.rerun()
                            else:
                                st.error("Não foi possível atualizar o serviço.")
                                st.write(resposta)

        # ---------------------------------------------------------------------
        # REMOVER SERVIÇO
        # ---------------------------------------------------------------------
        with subtab3:
            servicos_ativos = resumo_manutencao["servicos"]

            if not servicos_ativos:
                st.info("Nenhum serviço disponível para remoção.")
            else:
                nomes_remocao = [
                    servico.get("nome", "Serviço sem nome")
                    for servico in servicos_ativos
                ]

                indice_remocao = st.selectbox(
                    "Selecione o serviço para remover do plano",
                    range(len(servicos_ativos)),
                    format_func=lambda i: nomes_remocao[i],
                    key="indice_remocao_servico_online"
                )

                servico_remocao = servicos_ativos[indice_remocao]

                st.warning(
                    "A remoção desativa o serviço do plano futuro, mas não apaga "
                    "registros antigos de manutenção."
                )

                confirmacao = st.text_input(
                    "Digite REMOVER para confirmar",
                    key="confirmacao_remover_servico_online"
                )

                if st.button("Remover serviço do plano"):
                    if confirmacao.strip().upper() != "REMOVER":
                        st.warning("Digite REMOVER para confirmar.")
                    else:
                        ok, resposta = desativar_servico_manutencao_online(
                            servico_remocao.get("id")
                        )

                        if ok:
                            st.success("Serviço removido do plano.")
                            st.rerun()
                        else:
                            st.error("Não foi possível remover o serviço.")
                            st.write(resposta)

    # -------------------------------------------------------------------------
    # HISTÓRICO
    # -------------------------------------------------------------------------
    with tab4:
        mostrar_bloco_secao(
            "Histórico de manutenções",
            "Consulte os serviços já realizados neste veículo."
        )

        historico_manutencoes, erro_historico = listar_manutencoes_online(
            veiculo_ativo.id_online
        )

        if erro_historico:
            st.error("Erro ao carregar histórico de manutenções.")
            st.write(erro_historico)
        elif not historico_manutencoes:
            st.info("Nenhuma manutenção registrada.")
        else:
            for registro in historico_manutencoes:
                with st.container(border=True):
                    st.write(f"**Serviço:** {registro.get('nome_servico', 'Não informado')}")
                    st.write(f"**KM realizada:** {registro.get('km_realizada', 0)} km")
                    st.write(f"**Data:** {registro.get('data_realizada', 'Não informada')}")

                    if registro.get("observacao"):
                        st.write(f"**Observação:** {registro.get('observacao')}")
        
        st.divider()

        mostrar_bloco_secao(
            "Exportação de manutenções",
            "Usuários Plus podem baixar o histórico em CSV para análise externa."
        )

        if recurso_disponivel("exportacao_excel"):
            historico_exportacao, erro_exportacao = listar_manutencoes_online(
                veiculo_ativo.id_online
            )

            if erro_exportacao:
                st.error("Não foi possível carregar as manutenções para exportação.")
                st.write(erro_exportacao)
            elif not historico_exportacao:
                st.info("Ainda não há manutenções para exportar.")
            else:
                csv_manutencoes = gerar_csv_manutencoes(historico_exportacao)

                nome_arquivo_csv = (
                    f"ev_care_manutencoes_"
                    f"{veiculo_ativo.marca}_{veiculo_ativo.modelo}.csv"
                )

                nome_arquivo_csv = nome_arquivo_csv.replace(" ", "_").lower()

                st.download_button(
                    label="Baixar manutenções em CSV",
                    data=csv_manutencoes,
                    file_name=nome_arquivo_csv,
                    mime="text/csv"
                )

                st.caption(
                    "O arquivo CSV pode ser aberto no Excel, Google Planilhas "
                    "ou outros aplicativos de planilha."
                )
        else:
            exibir_bloqueio_plus("exportacao_excel")



# =============================================================================
# VIAGENS
# =============================================================================

elif pagina == "Viagens":
    mostrar_cabecalho_pagina(
        "Planejar Viagem",
        "Simule autonomia, energia necessária e custo estimado da viagem."
    )

    if not veiculo_ativo:
        st.warning("Selecione ou cadastre um veículo antes de planejar viagens.")
    else:
        st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

        autonomia = veiculo_ativo.calcular_autonomia()
        consumo = float(veiculo_ativo.info.get("Consumo", 6.0))

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Autonomia estimada", f"{autonomia:.0f} km")

        with col2:
            st.metric("Consumo teórico", f"{consumo:.2f} km/kWh")

        with col3:
            st.metric("KM atual", f"{veiculo_ativo.km_atual} km")

        st.divider()

        distancia = st.number_input(
            "Distância da viagem em km",
            min_value=0.0,
            step=10.0,
            key="viagem_distancia"
        )

        margem = st.slider(
            "Margem de segurança (%)",
            min_value=0,
            max_value=50,
            value=10,
            key="viagem_margem"
        )

        estado_viagem = st.selectbox(
            "Estado para preço estimado do kWh",
            ["CE", "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "DF"],
            key="viagem_estado"
        )

        if st.button("Simular viagem", key="botao_simular_viagem"):
            if distancia <= 0:
                st.warning("Informe uma distância maior que zero.")
            elif consumo <= 0:
                st.error("Consumo inválido para cálculo.")
            else:
                preco_kwh = buscar_preco_kwh(estado_viagem)
                autonomia_com_margem = autonomia * (1 - margem / 100)
                energia_necessaria = distancia / consumo
                custo_estimado = energia_necessaria * preco_kwh

                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    st.metric("Energia necessária", f"{energia_necessaria:.2f} kWh")

                with col_b:
                    st.metric("Custo estimado", f"R$ {custo_estimado:.2f}")

                with col_c:
                    st.metric("Autonomia com margem", f"{autonomia_com_margem:.0f} km")

                if autonomia_com_margem >= distancia:
                    st.success("Viagem possível sem recarga, considerando a margem informada.")
                else:
                    deficit = distancia - autonomia_com_margem
                    st.error("Viagem não recomendada sem recarga.")
                    st.write(f"Déficit estimado de autonomia: **{deficit:.0f} km**")


# =============================================================================
# CUSTOS E ECONOMIA
# =============================================================================

elif pagina == "Custos e Economia":
    mostrar_cabecalho_pagina(
        "Custos e Economia",
        "Compare custos, consumo e economia do veículo elétrico."
    )

    if not validar_contexto_online("Custos e Economia"):
        st.stop()

    veiculo_ativo = obter_veiculo_ativo()


    with st.container(border=True):
        st.subheader(f"{veiculo_ativo.marca} {veiculo_ativo.modelo}")
        st.caption("Veículo ativo para análise de custos, consumo e economia.")

        col_v1, col_v2, col_v3 = st.columns(3)

        with col_v1:
            st.metric("KM atual", formatar_km(veiculo_ativo.km_atual))

        with col_v2:
            st.metric(
                "Autonomia estimada",
                f"{veiculo_ativo.calcular_autonomia():.0f} km"
            )

        with col_v3:
            st.metric(
                "Consumo de referência",
                f"{float(veiculo_ativo.info.get('Consumo', 6.0)):.2f} km/kWh"
            )

    st.divider()

    resumo, erro_resumo = obter_resumo_recargas_online(
        veiculo_id=veiculo_ativo.id_online,
        km_atual_veiculo=veiculo_ativo.km_atual
    )

    if erro_resumo:
        st.error("Erro ao carregar resumo online de recargas.")
        st.write(erro_resumo)
        st.stop()

    consumo_ev = float(veiculo_ativo.info.get("Consumo", 6.0))

    mostrar_bloco_secao(
        "Parâmetros de comparação",
        "Ajuste os valores de energia, gasolina e consumo para simular custos."
    )

    estado_custos = st.selectbox(
        "Estado para preço estimado do kWh",
        ["CE", "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "DF"],
        key="custos_estado"
    )

    preco_kwh = buscar_preco_kwh(estado_custos)

    preco_gasolina = st.number_input(
        "Preço da gasolina em R$",
        min_value=0.0,
        step=0.01,
        value=5.80,
        key="custos_preco_gasolina"
    )

    consumo_gasolina = st.number_input(
        "Consumo médio de carro a gasolina em km/l",
        min_value=1.0,
        step=0.1,
        value=10.5,
        key="custos_consumo_gasolina"
    )

    custo_ev_km_estimado = preco_kwh / consumo_ev if consumo_ev > 0 else 0
    custo_gasolina_km = preco_gasolina / consumo_gasolina if consumo_gasolina > 0 else 0

    mostrar_bloco_secao(
        "Comparativo principal",
        "Compare o custo estimado do veículo elétrico com um veículo a gasolina."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        mostrar_card_metrica(
            "Custo/km elétrico estimado",
            f"R$ {custo_ev_km_estimado:.4f}"
        )

    with col2:
        mostrar_card_metrica(
            "Custo/km gasolina",
            f"R$ {custo_gasolina_km:.4f}"
        )

    with col3:
        mostrar_card_metrica(
            "Gasto total em recargas",
            formatar_moeda(resumo["custo_total"])
        )

    if custo_ev_km_estimado < custo_gasolina_km:
        st.success("Pela estimativa, o veículo elétrico está mais econômico.")
    else:
        st.warning("Neste cenário, o veículo elétrico não está mais econômico pela estimativa.")

    st.divider()

    mostrar_bloco_secao(
        "Dados reais das recargas",
        "Indicadores calculados a partir das recargas registradas para o veículo."
    )

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.metric("Energia total", f"{resumo['energia_total']:.2f} kWh")

    with col_b:
        st.metric("Preço médio kWh", f"R$ {resumo['preco_medio_kwh']:.2f}")

    with col_c:
        if resumo["custo_real_km"] is not None:
            st.metric("Custo real por km", f"R$ {resumo['custo_real_km']:.4f}")
        else:
            st.metric("Custo real por km", "Indisponível")

    if resumo["consumo_real_km_kwh"] is not None:
        st.success(
            f"Consumo real aproximado: {resumo['consumo_real_km_kwh']:.2f} km/kWh"
        )
        st.write(f"KM considerados desde a primeira recarga: {resumo['km_rodados']} km")
    else:
        st.info(
            "Para calcular consumo real, registre recargas e mantenha a quilometragem atualizada."
        )

    st.divider()

    mostrar_bloco_secao(
        "Economia real aproximada",
        "Estimativa de economia com base no custo por km do elétrico e da gasolina."
    )

    if resumo["custo_real_km"] is not None:
        economia_real = (
            custo_gasolina_km - resumo["custo_real_km"]
        ) * resumo["km_rodados"]

        if economia_real >= 0:
            st.success(f"Economia real aproximada no período: R$ {economia_real:.2f}")
        else:
            st.warning(
                f"No período registrado, o elétrico ficou R$ {abs(economia_real):.2f} mais caro."
            )
    else:
        st.info(
            "Ainda não há dados suficientes para calcular economia real. "
            "Registre recargas e atualize a quilometragem para melhorar o cálculo."
        )


# =============================================================================
# HISTÓRICO
# =============================================================================

elif pagina == "Histórico":
    mostrar_cabecalho_pagina(
        "Histórico",
        "Consulte registros de quilometragem, recargas e manutenções."
    )

    if not validar_contexto_online("Histórico"):
        st.stop()

    veiculo_ativo = obter_veiculo_ativo()


    with st.container(border=True):
        st.subheader(f"{veiculo_ativo.marca} {veiculo_ativo.modelo}")
        st.caption("Histórico consolidado de quilometragem, recargas e manutenções.")

        col_h1, col_h2, col_h3 = st.columns(3)

        with col_h1:
            st.metric("KM atual", formatar_km(veiculo_ativo.km_atual))

        with col_h2:
            st.metric(
                "Autonomia estimada",
                f"{veiculo_ativo.calcular_autonomia():.0f} km"
            )

        with col_h3:
            st.metric(
                "Saúde da bateria",
                f"{veiculo_ativo.calcular_saude_bateria():.2f}%"
            )

    st.divider()

    tab1, tab2, tab3 = st.tabs(
        [
            "Quilometragem",
            "Recargas",
            "Manutenções"
        ]
    )

    # -------------------------------------------------------------------------
    # HISTÓRICO ONLINE DE QUILOMETRAGEM
    # -------------------------------------------------------------------------
    with tab1:
        mostrar_bloco_secao(
            "Histórico de quilometragem",
            "Lista de atualizações de KM feitas neste veículo."
        )

        historico_online, erro_historico = listar_historico_km_online(
            veiculo_ativo.id_online
        )

        if erro_historico:
            st.error("Erro ao carregar histórico online de quilometragem.")
            st.write(erro_historico)
        elif not historico_online:
            st.info("Ainda não há registros online de alteração de quilometragem.")
        else:
            for registro in historico_online:
                km_anterior = int(registro.get("km_anterior", 0))
                km_nova = int(registro.get("km_nova", 0))
                diferenca = km_nova - km_anterior

                with st.container(border=True):
                    st.write(f"**Data:** {registro.get('data_registro', 'Não informada')}")
                    st.write(f"**KM anterior:** {km_anterior} km")
                    st.write(f"**Nova KM:** {km_nova} km")

                    if diferenca >= 0:
                        st.write(f"**Diferença registrada:** {diferenca} km")

    # -------------------------------------------------------------------------
    # HISTÓRICO ONLINE DE RECARGAS
    # -------------------------------------------------------------------------
    with tab2:
        mostrar_bloco_secao(
            "Histórico de recargas",
            "Lista de recargas registradas para este veículo."
        )

        recargas_online, erro_recargas = listar_recargas_online(
            veiculo_ativo.id_online
        )

        if erro_recargas:
            st.error("Erro ao carregar histórico online de recargas.")
            st.write(erro_recargas)
        elif not recargas_online:
            st.info("Nenhuma recarga online registrada.")
        else:
            for i, recarga in enumerate(recargas_online, 1):
                with st.container(border=True):
                    st.write(f"### Recarga {i}")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.write("**Data**")
                        st.write(recarga.get("data_recarga", "Não informada"))

                    with col2:
                        st.write("**Local**")
                        st.write(recarga.get("local", "Não informado"))

                    with col3:
                        st.write("**Energia**")
                        st.write(f"{float(recarga.get('energia_kwh') or 0):.2f} kWh")

                    with col4:
                        st.write("**Custo**")
                        st.write(f"R$ {float(recarga.get('custo_total') or 0):.2f}")

                    st.write(
                        f"**Bateria:** "
                        f"{float(recarga.get('bateria_inicial') or 0):.1f}% → "
                        f"{float(recarga.get('bateria_final') or 0):.1f}%"
                    )

                    st.write(f"**Preço kWh:** R$ {float(recarga.get('preco_kwh') or 0):.2f}")
                    st.write(f"**Tipo:** {recarga.get('tipo', 'Não informado')}")
                    st.write(f"**KM no registro:** {recarga.get('km_atual', 0)} km")

                    if recarga.get("observacao"):
                        st.write(f"**Observação:** {recarga.get('observacao')}")

    # -------------------------------------------------------------------------
    # HISTÓRICO ONLINE DE MANUTENÇÕES
    # -------------------------------------------------------------------------
    with tab3:
        mostrar_bloco_secao(
            "Histórico de manutenções",
            "Lista de serviços de manutenção realizados neste veículo."
        )


# =============================================================================
# PLANOS
# =============================================================================

elif pagina == "Planos":
    mostrar_cabecalho_pagina(
        "Planos do EV Care",
        "Escolha o plano ideal para acompanhar seu veículo elétrico."
    )

    exibir_resumo_plano()

    with st.container(border=True):
        st.subheader("Seu plano atual")

        plano_atual = str(st.session_state.get("auth_plano", "free")).lower()
        status_assinatura = str(
            st.session_state.get("auth_status_assinatura", "inactive")
        ).lower()

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            st.metric("Plano", plano_atual.upper())

        with col_p2:
            st.metric("Status", status_assinatura.upper())

        if plano_atual == "plus" and status_assinatura == "active":
            st.success("Você está com recursos Plus ativos.")
        elif plano_atual == "plus":
            st.warning("Seu plano está como Plus, mas a assinatura não está ativa.")
        else:
            st.info("Você está usando o EV Care Free.")

    st.divider()

    col_free, col_plus = st.columns(2)

    with col_free:
        with st.container(border=True):
            st.subheader("EV Care Free")
            st.caption("Comece gratuitamente")

            st.markdown(
                """
                Ideal para acompanhar um veículo elétrico no dia a dia.

                Inclui:

                - 1 veículo cadastrado
                - Quilometragem
                - Recargas
                - Manutenções
                - Dashboard básico
                - Custos e economia
                - Histórico
                - Envio de feedback
                """
            )

            st.success("Disponível no Beta")

    with col_plus:
        with st.container(border=True):
            st.subheader("EV Care Plus")
            st.caption("Relatórios, exportações e recursos avançados")

            st.markdown(
                """
                Inclui tudo do Free, mais:

                - Veículos ilimitados
                - Exportação CSV de recargas
                - Exportação CSV de quilometragem
                - Exportação CSV de manutenções
                - Relatório PDF do veículo
                - Relatório mensal
                - Recursos avançados em evolução
                """
            )

            st.info("Disponível para testes controlados")

    st.divider()

    mostrar_bloco_secao(
        "Recursos Plus",
        "Veja quais recursos avançados estão disponíveis ou planejados para o seu plano."
    )

    recursos_plus = obter_recursos_plus()

    for codigo_recurso, nome_recurso in recursos_plus.items():
        with st.container(border=True):
            col_r1, col_r2 = st.columns([3, 1])

            with col_r1:
                st.write(f"### {nome_recurso}")

                if recurso_disponivel(codigo_recurso):
                    st.caption("Recurso liberado para sua conta.")
                else:
                    st.caption("Recurso reservado para usuários Plus ativos.")

            with col_r2:
                if recurso_disponivel(codigo_recurso):
                    st.success("Liberado")
                else:
                    st.warning("Plus")

    st.divider()

    st.info(
        "Durante o Beta, os planos e recursos podem evoluir com base nos testes "
        "e feedbacks dos usuários."
    )


# =============================================================================
# FEEDBACK
# =============================================================================

elif pagina == "Feedback":
    mostrar_cabecalho_pagina(
        "Feedback do EV Care",
        "Envie sugestões, relate problemas e ajude a melhorar o aplicativo."
    )

    if not st.session_state.get("auth_logado", False):
        st.warning("Faça login na página **Conta** para enviar feedback.")
        st.info(
            "O feedback é vinculado à sua conta para facilitar o acompanhamento "
            "de problemas, sugestões e melhorias."
        )
        st.stop()

    tab1, tab2 = st.tabs(["Enviar feedback", "Meus feedbacks"])

    # -------------------------------------------------------------------------
    # ENVIAR FEEDBACK
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Enviar feedback")

        st.write(
            "Use este formulário para relatar problemas, sugerir melhorias ou "
            "comentar sua experiência com o EV Care."
        )
        with st.container(border=True):
            st.write("### Como enviar um bom feedback")
            st.markdown(
                """
                Para ajudar na melhoria do EV Care, tente informar:

                - O que você tentou fazer
                - Em qual página aconteceu
                - O que ocorreu
                - O que você esperava que acontecesse
                - Se o problema aconteceu uma ou várias vezes
                """
            )

        with st.form("form_feedback_online"):
            pagina_feedback = st.selectbox(
                "Página relacionada",
                [
                    "Dashboard",
                    "Minha Garagem",
                    "Quilometragem",
                    "Recargas",
                    "Manutenções",
                    "Viagens",
                    "Custos e Economia",
                    "Histórico",
                    "Planos",
                    "Conta",
                    "Configurações",
                    "Outro"
                ]
            )

            tipo_feedback = st.selectbox(
                "Tipo de feedback",
                [
                    "Problema encontrado",
                    "Sugestão de melhoria",
                    "Dúvida",
                    "Elogio",
                    "Ideia para recurso Plus",
                    "Outro"
                ]
            )

            nota_feedback = st.slider(
                "Nota geral para sua experiência",
                min_value=1,
                max_value=5,
                value=4
            )

            interesse_plus = st.checkbox(
                "Tenho interesse em recursos Plus"
            )

            mensagem_feedback = st.text_area(
                "Descreva seu feedback",
                placeholder=(
                    "Exemplo: Na página Recargas, tentei editar uma recarga "
                    "e percebi que..."
                ),
                height=180
            )

            enviar_feedback = st.form_submit_button("Enviar feedback")

            if enviar_feedback:
                if not mensagem_feedback.strip():
                    st.warning("Escreva uma mensagem antes de enviar.")
                else:
                    ok, resposta = registrar_feedback_online(
                        user_id=st.session_state.auth_user_id,
                        email=st.session_state.auth_email,
                        nome=st.session_state.auth_nome,
                        pagina=pagina_feedback,
                        tipo=tipo_feedback,
                        mensagem=mensagem_feedback.strip(),
                        interesse_plus=interesse_plus,
                        nota=nota_feedback
                    )

                    if ok:
                        st.success(resposta)
                        st.rerun()
                    else:
                        st.error("Não foi possível enviar o feedback.")
                        st.write(resposta)

        st.warning(
            "Não envie senhas, documentos, dados bancários ou informações sensíveis."
        )

    # -------------------------------------------------------------------------
    # MEUS FEEDBACKS
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("Meus feedbacks enviados")

        feedbacks, erro_feedbacks = listar_meus_feedbacks()

        if erro_feedbacks:
            st.error("Não foi possível carregar seus feedbacks.")
            st.write(erro_feedbacks)
        elif not feedbacks:
            st.info("Você ainda não enviou feedbacks.")
        else:
            for feedback in feedbacks:
                with st.container(border=True):
                    st.write(f"**Página:** {feedback.get('pagina', 'Não informada')}")
                    st.write(f"**Tipo:** {feedback.get('tipo', 'Não informado')}")
                    st.write(f"**Nota:** {feedback.get('nota', 'Não informada')}")
                    st.write(f"**Status:** {feedback.get('status', 'novo')}")
                    st.write(f"**E-mail enviado:** {'Sim' if feedback.get('email_enviado') else 'Não'}")
                    st.write(f"**Enviado em:** {feedback.get('created_at', 'Não informado')}")

                    if feedback.get("interesse_plus"):
                        st.caption("Usuário demonstrou interesse em recursos Plus.")

                    st.write("**Mensagem:**")
                    st.write(feedback.get("mensagem", ""))

elif pagina == "Minha Garagem":
    mostrar_cabecalho_pagina(
        "Minha Garagem",
        "Gerencie os veículos vinculados à sua conta."
    )

    st.info(
        "Cadastre e gerencie os veículos vinculados à sua conta. "
        "O veículo ativo será usado nas páginas de quilometragem, recargas, "
        "manutenções, custos e relatórios."
    )


    if not st.session_state.auth_logado:
        st.warning("Faça login na página Conta para usar a Minha Garagem.")
    else:
        st.write(f"Usuário logado: **{st.session_state.auth_email}**")
        st.write(f"Plano atual: **{st.session_state.auth_plano}**")

        st.divider()

        quantidade, erro_quantidade = contar_veiculos_usuario()
        veiculos_online, erro_lista = listar_veiculos_usuario()
        veiculo_ativo_online, erro_ativo = obter_veiculo_ativo_online()

        if erro_quantidade:
            st.error("Erro ao contar veículos online.")
            st.write(erro_quantidade)
        elif erro_lista:
            st.error("Erro ao listar veículos online.")
            st.write(erro_lista)
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Veículos online", quantidade)

            with col2:
                if veiculo_ativo_online:
                    st.metric(
                        "Veículo ativo online",
                        f"{veiculo_ativo_online.get('marca', '')} {veiculo_ativo_online.get('modelo', '')}"
                    )
                else:
                    st.metric("Veículo ativo online", "Nenhum")

            st.divider()

            mostrar_bloco_secao(
            "Veículos cadastrados",
            "Veja os veículos da sua conta e escolha qual será usado como ativo."
            )

            if not veiculos_online:
                st.info("Nenhum veículo online cadastrado ainda.")
            else:
                for veiculo in veiculos_online:
                    with st.container(border=True):
                        st.write(
                            f"### {veiculo.get('marca', 'Marca não informada')} "
                            f"{veiculo.get('modelo', 'Modelo não informado')}"
                        )

                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            st.write(f"**KM atual:** {veiculo.get('km_atual', 0)} km")

                        with col_b:
                            st.write(f"**Bateria:** {veiculo.get('bateria_kwh', 0)} kWh")

                        with col_c:
                            st.write(f"**Consumo:** {veiculo.get('consumo_km_kwh', 0)} km/kWh")

                        if veiculo.get("veiculo_ativo"):
                            st.success("Veículo ativo")
                        else:
                            if st.button(
                                "Definir como ativo",
                                key=f"ativar_online_{veiculo.get('id')}"
                            ):
                                ok, resposta = definir_veiculo_ativo_online(veiculo.get("id"))

                                if ok:
                                    st.success("Veículo online definido como ativo.")
                                    st.rerun()
                                else:
                                    st.error("Não foi possível definir veículo ativo.")
                                    st.write(resposta)

                        st.divider()

                        confirmacao_excluir = st.text_input(
                            "Digite EXCLUIR para remover este veículo",
                            key=f"confirmar_excluir_online_{veiculo.get('id')}"
                        )

                        if st.button(
                            "Excluir veículo online",
                            key=f"excluir_online_{veiculo.get('id')}"
                        ):
                            if confirmacao_excluir.strip().upper() != "EXCLUIR":
                                st.warning("Digite EXCLUIR para confirmar a exclusão.")
                            else:
                                ok, resposta = excluir_veiculo_online(veiculo.get("id"))

                                if ok:
                                    st.success("Veículo online excluído com sucesso.")
                                    st.rerun()
                                else:
                                    st.error("Não foi possível excluir o veículo online.")
                                    st.write(resposta)
                        with st.expander("Editar veículo online"):
                            with st.form(f"form_editar_online_{veiculo.get('id')}"):
                                nova_marca_online = st.text_input(
                                    "Marca",
                                    value=veiculo.get("marca", ""),
                                    key=f"editar_marca_online_{veiculo.get('id')}"
                                )

                                novo_modelo_online = st.text_input(
                                    "Modelo",
                                    value=veiculo.get("modelo", ""),
                                    key=f"editar_modelo_online_{veiculo.get('id')}"
                                )

                                novo_km_online = st.number_input(
                                    "KM atual",
                                    min_value=0,
                                    step=100,
                                    value=int(veiculo.get("km_atual", 0)),
                                    key=f"editar_km_online_{veiculo.get('id')}"
                                )

                                nova_bateria_online = st.number_input(
                                    "Capacidade da bateria em kWh",
                                    min_value=0.1,
                                    step=0.1,
                                    value=float(veiculo.get("bateria_kwh") or 40.0),
                                    key=f"editar_bateria_online_{veiculo.get('id')}"
                                )

                                novo_consumo_online = st.number_input(
                                    "Consumo médio em km/kWh",
                                    min_value=0.1,
                                    step=0.1,
                                    value=float(veiculo.get("consumo_km_kwh") or 6.0),
                                    key=f"editar_consumo_online_{veiculo.get('id')}"
                                )

                                salvar_edicao_online = st.form_submit_button(
                                    "Salvar alterações online"
                                )

                                if salvar_edicao_online:
                                    if not nova_marca_online.strip() or not novo_modelo_online.strip():
                                        st.warning("Informe marca e modelo.")
                                    else:
                                        ok, resposta = atualizar_veiculo_online(
                                            veiculo_id=veiculo.get("id"),
                                            marca=nova_marca_online.strip().upper(),
                                            modelo=novo_modelo_online.strip().upper(),
                                            km_atual=novo_km_online,
                                            bateria_kwh=nova_bateria_online,
                                            consumo_km_kwh=novo_consumo_online,
                                            dados_tecnicos={
                                                "origem": "garagem_online_edicao",
                                                "plano_usuario": st.session_state.auth_plano
                                            }
                                        )

                                        if ok:
                                            st.success("Veículo online atualizado com sucesso.")
                                            st.rerun()
                                        else:
                                            st.error("Não foi possível atualizar o veículo online.")
                                            st.write(resposta)

            mostrar_bloco_secao(
            "Cadastrar veículo",
            "Adicione um veículo para começar a registrar quilometragem, recargas e manutenções."
            )

            pode_criar, mensagem_bloqueio = pode_criar_veiculo(quantidade)

            if not pode_criar:
                st.warning(mensagem_bloqueio)
                st.caption(
                    "Para cadastrar mais veículos, use uma conta Plus ativa."
                )
            else:
                with st.form("form_garagem_online"):
                    marca_online = st.text_input("Marca")
                    modelo_online = st.text_input("Modelo")

                    km_online = st.number_input(
                        "KM atual",
                        min_value=0,
                        step=100
                    )

                    bateria_online = st.number_input(
                        "Capacidade da bateria em kWh",
                        min_value=0.1,
                        step=0.1,
                        value=40.0
                    )

                    consumo_online = st.number_input(
                        "Consumo médio em km/kWh",
                        min_value=0.1,
                        step=0.1,
                        value=6.0
                    )

                    cadastrar_online = st.form_submit_button("Cadastrar veículo")

                    if cadastrar_online:
                        if not marca_online.strip() or not modelo_online.strip():
                            st.warning("Informe marca e modelo.")
                        else:
                            ok, resposta = criar_veiculo_online(
                            user_id=st.session_state.auth_user_id,
                            marca=marca_online.strip().upper(),
                            modelo=modelo_online.strip().upper(),
                            km_atual=km_online,
                            bateria_kwh=bateria_online,
                            consumo_km_kwh=consumo_online,
                            dados_tecnicos={
                                "origem": "garagem",
                                "plano_usuario": obter_plano_usuario()
                            },
                            veiculo_ativo=(quantidade == 0)
                            )

                            if ok:
                                st.success("Veículo cadastrado com sucesso.")
                                st.rerun()
                            else:
                                st.error("Não foi possível cadastrar o veículo.")
                                st.write(resposta)

    st.divider()

    mostrar_bloco_secao(
        "Adicionar veículo pelo catálogo",
        "Escolha marca, modelo e versão para preencher automaticamente bateria, consumo e autonomia de referência."
    )

    quantidade_catalogo, erro_quantidade_catalogo = contar_veiculos_usuario()

    if erro_quantidade_catalogo:
        st.error("Não foi possível verificar o limite de veículos.")
        st.write(erro_quantidade_catalogo)
        quantidade_catalogo = 0

    pode_criar_catalogo, mensagem_bloqueio_catalogo = pode_criar_veiculo(
        quantidade_catalogo
    )

    if not pode_criar_catalogo:
        st.warning(mensagem_bloqueio_catalogo)
        st.caption("Para cadastrar mais veículos, use uma conta Plus ativa.")
    else:
        marcas_catalogo, erro_marcas = listar_marcas_catalogo()

        if erro_marcas:
            st.error("Não foi possível carregar as marcas do catálogo.")
            st.write(erro_marcas)

        elif not marcas_catalogo:
            st.info("Nenhuma marca disponível no catálogo no momento.")

        else:
            marca_catalogo = st.selectbox(
                "Marca",
                marcas_catalogo,
                key="catalogo_ev_marca"
            )

            modelos_catalogo, erro_modelos = listar_modelos_por_marca_catalogo(
                marca_catalogo
            )

            if erro_modelos:
                st.error("Não foi possível carregar os modelos do catálogo.")
                st.write(erro_modelos)

            elif not modelos_catalogo:
                st.info("Nenhum modelo disponível para esta marca.")

            else:
                modelo_catalogo = st.selectbox(
                    "Modelo",
                    modelos_catalogo,
                    key="catalogo_ev_modelo_base"
                )

                versoes_catalogo, erro_versoes = listar_versoes_catalogo(
                    marca_catalogo,
                    modelo_catalogo
                )

                if erro_versoes:
                    st.error("Não foi possível carregar as versões do catálogo.")
                    st.write(erro_versoes)

                elif not versoes_catalogo:
                    st.info("Nenhuma versão disponível para este modelo.")

                else:
                    def formatar_versao_catalogo(indice):
                        item = versoes_catalogo[indice]

                        versao = (
                            item.get("versao_comercial")
                            or item.get("versao")
                            or "Versão de referência"
                        )

                        ano_modelo = item.get("ano_modelo")
                        bateria = item.get("bateria_kwh")
                        autonomia = item.get("autonomia_referencia_km")

                        detalhes = []

                        if ano_modelo:
                            detalhes.append(f"Ano {ano_modelo}")

                        if bateria is not None:
                            detalhes.append(f"{float(bateria):.1f} kWh")

                        if autonomia is not None:
                            detalhes.append(f"{int(autonomia)} km ref.")

                        detalhes_txt = " | ".join(detalhes)

                        if detalhes_txt:
                            return f"{versao} ({detalhes_txt})"

                        return versao

                    indice_versao_catalogo = st.selectbox(
                        "Versão",
                        range(len(versoes_catalogo)),
                        format_func=formatar_versao_catalogo,
                        key="catalogo_ev_versao"
                    )

                    veiculo_catalogo = versoes_catalogo[indice_versao_catalogo]

                    st.subheader("Dados de referência da versão selecionada")
                    st.caption(
                        "Esses dados ajudam a preencher automaticamente bateria e consumo. "
                        "Eles podem variar conforme versão, ano/modelo e ciclo de medição."
                    )

                    col_cat1, col_cat2, col_cat3 = st.columns(3)

                    with col_cat1:
                        st.metric(
                            "Bateria",
                            f"{float(veiculo_catalogo.get('bateria_kwh') or 0):.1f} kWh"
                        )

                    with col_cat2:
                        st.metric(
                            "Consumo ref.",
                            f"{float(veiculo_catalogo.get('consumo_km_kwh') or 0):.2f} km/kWh"
                        )

                    with col_cat3:
                        st.metric(
                            "Autonomia ref.",
                            f"{int(veiculo_catalogo.get('autonomia_referencia_km') or 0)} km"
                        )

                    col_cat4, col_cat5, col_cat6 = st.columns(3)

                    with col_cat4:
                        valor_inmetro = veiculo_catalogo.get("autonomia_inmetro_km")
                        st.metric(
                            "Autonomia Inmetro",
                            f"{int(valor_inmetro)} km" if valor_inmetro else "Não informada"
                        )

                    with col_cat5:
                        bateria_util = veiculo_catalogo.get("bateria_util_kwh")
                        st.metric(
                            "Bateria útil",
                            f"{float(bateria_util):.1f} kWh" if bateria_util else "Não informada"
                        )

                    with col_cat6:
                        tracao = veiculo_catalogo.get("tracao") or "Não informada"
                        st.metric("Tração", tracao)

                    status_validacao = veiculo_catalogo.get("status_validacao")

                    if status_validacao == "validado_oficial":
                        st.success("Dados técnicos validados por fonte oficial.")
                    elif status_validacao == "validado_parcialmente":
                        st.info(
                            "Dados técnicos validados parcialmente. Confira a versão e o ano do veículo."
                        )
                    elif status_validacao == "referencia_inicial":
                        st.warning(
                            "Dados técnicos de referência inicial. Podem variar conforme versão, ano/modelo e ciclo de medição."
                        )
                    else:
                        st.caption(
                            "Dados técnicos em validação. Use como referência inicial."
                        )

                    if veiculo_catalogo.get("fonte_tecnica"):
                        st.caption(
                            f"Fonte técnica: {veiculo_catalogo.get('fonte_tecnica')}"
                        )

                    if veiculo_catalogo.get("observacao"):
                        st.caption(veiculo_catalogo.get("observacao"))

                    with st.form("form_adicionar_veiculo_catalogo"):
                        km_catalogo = st.number_input(
                            "KM atual",
                            min_value=0,
                            step=100,
                            value=0,
                            key="catalogo_ev_km_atual"
                        )

                        confirmar_catalogo = st.form_submit_button(
                            "Cadastrar veículo pelo catálogo"
                        )

                        if confirmar_catalogo:
                            bateria_kwh = float(
                                veiculo_catalogo.get("bateria_kwh") or 0
                            )

                            consumo_km_kwh = float(
                                veiculo_catalogo.get("consumo_km_kwh") or 0
                            )

                            if bateria_kwh <= 0 or consumo_km_kwh <= 0:
                                st.error(
                                    "Esta versão ainda não possui dados técnicos suficientes. "
                                    "Use o cadastro manual ou revise o catálogo."
                                )
                            else:
                                versao_escolhida = (
                                    veiculo_catalogo.get("versao_comercial")
                                    or veiculo_catalogo.get("versao")
                                    or "Referência"
                                )

                                modelo_completo = (
                                    f"{veiculo_catalogo.get('modelo', '').strip().upper()} "
                                    f"{str(versao_escolhida).strip().upper()}"
                                ).strip()

                                ok, resposta = criar_veiculo_online(
                                    user_id=st.session_state.auth_user_id,
                                    marca=veiculo_catalogo.get("marca", "").strip().upper(),
                                    modelo=modelo_completo,
                                    km_atual=km_catalogo,
                                    bateria_kwh=bateria_kwh,
                                    consumo_km_kwh=consumo_km_kwh,
                                    dados_tecnicos={
                                        "origem": "catalogo_veiculos_ev",
                                        "catalogo_id": veiculo_catalogo.get("id"),
                                        "marca_catalogo": veiculo_catalogo.get("marca"),
                                        "modelo_catalogo": veiculo_catalogo.get("modelo"),
                                        "versao": versao_escolhida,
                                        "ano_modelo": veiculo_catalogo.get("ano_modelo"),
                                        "bateria_nominal_kwh": veiculo_catalogo.get("bateria_nominal_kwh"),
                                        "bateria_util_kwh": veiculo_catalogo.get("bateria_util_kwh"),
                                        "autonomia_referencia_km": veiculo_catalogo.get("autonomia_referencia_km"),
                                        "autonomia_inmetro_km": veiculo_catalogo.get("autonomia_inmetro_km"),
                                        "autonomia_wltp_km": veiculo_catalogo.get("autonomia_wltp_km"),
                                        "consumo_inmetro_kwh_100km": veiculo_catalogo.get("consumo_inmetro_kwh_100km"),
                                        "potencia_cv": veiculo_catalogo.get("potencia_cv"),
                                        "tracao": veiculo_catalogo.get("tracao"),
                                        "fonte_ranking": veiculo_catalogo.get("fonte_ranking"),
                                        "fonte_tecnica": veiculo_catalogo.get("fonte_tecnica"),
                                        "fonte_url": veiculo_catalogo.get("fonte_url"),
                                        "status_validacao": veiculo_catalogo.get("status_validacao"),
                                        "observacao_catalogo": veiculo_catalogo.get("observacao"),
                                        "plano_usuario": obter_plano_usuario()
                                    },
                                    veiculo_ativo=(quantidade_catalogo == 0)
                                )

                                if ok:
                                    st.success("Veículo cadastrado com sucesso pelo catálogo.")
                                    carregar_veiculo_online_ativo_para_app()
                                    st.rerun()
                                else:
                                    st.error("Não foi possível cadastrar o veículo.")
                                    st.write(resposta)

                                    st.divider()

# =============================================================================
# CONTA
# =============================================================================

elif pagina == "Conta":
    mostrar_cabecalho_pagina(
        "Conta",
        "Acesse sua conta, plano e informações de assinatura."
    )

    if st.session_state.get("auth_logado", False):
        st.success("Conta conectada")

        st.write(f"**E-mail:** {st.session_state.auth_email}")
        st.write(f"**Nome:** {st.session_state.auth_nome}")
        st.write(f"**Plano atual:** {st.session_state.auth_plano}")
        st.write(
            f"**Status da assinatura:** "
            f"{st.session_state.get('auth_status_assinatura', 'inactive')}"
        )

        st.info(
            "Sua conta está ativa. Os dados do veículo são vinculados ao seu login."
        )

        if st.button("Sair da conta"):
            sair_usuario()
            st.success("Você saiu da conta.")
            st.rerun()

    else:
        tab_login, tab_cadastro = st.tabs(["Entrar", "Criar conta"])

        with tab_login:
            st.subheader("Entrar")

            email_login = st.text_input("E-mail", key="login_email")
            senha_login = st.text_input(
                "Senha",
                type="password",
                key="login_senha"
            )

            if st.button("Entrar"):
                if not email_login or not senha_login:
                    st.warning("Informe e-mail e senha.")
                else:
                    ok, mensagem = entrar_usuario(email_login, senha_login)

                    if ok:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)

        with tab_cadastro:
            st.subheader("Criar conta")

            nome_cadastro = st.text_input("Nome", key="cadastro_nome")
            email_cadastro = st.text_input("E-mail", key="cadastro_email")
            senha_cadastro = st.text_input(
                "Senha",
                type="password",
                key="cadastro_senha"
            )

            st.caption("Use uma senha com pelo menos 6 caracteres.")

            if st.button("Criar conta"):
                if not email_cadastro or not senha_cadastro:
                    st.warning("Informe e-mail e senha.")
                elif len(senha_cadastro) < 6:
                    st.warning("A senha deve ter pelo menos 6 caracteres.")
                else:
                    ok, mensagem = criar_conta(
                        email_cadastro,
                        senha_cadastro,
                        nome_cadastro
                    )

                    if ok:
                        st.success(mensagem)

                        if st.session_state.get("auth_logado", False):
                            st.rerun()
                    else:
                        st.error(mensagem)

elif pagina == "Configurações":
    mostrar_cabecalho_pagina(
        "Configurações",
        "Ajustes gerais, informações do aplicativo e orientações do Beta."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Geral",
            "Dados",
            "Beta"
        ]
    )

    # -------------------------------------------------------------------------
    # GERAL
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Informações gerais")

        st.write(
            "O EV Care foi criado para ajudar no acompanhamento de veículos elétricos, "
            "incluindo quilometragem, recargas, custos, manutenções e relatórios."
        )

        st.divider()

        st.subheader("Resumo do uso")

        if st.session_state.get("auth_logado", False):
            veiculo_ativo = obter_veiculo_ativo()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Conta",
                    "Conectada"
                )

            with col2:
                st.metric(
                    "Plano",
                    str(st.session_state.get("auth_plano", "free")).upper()
                )

            with col3:
                if veiculo_ativo:
                    st.metric(
                        "Veículo ativo",
                        f"{veiculo_ativo.marca} {veiculo_ativo.modelo}"
                    )
                else:
                    st.metric(
                        "Veículo ativo",
                        "Nenhum"
                    )

            if not veiculo_ativo:
                st.info(
                    "Cadastre ou selecione um veículo em **Minha Garagem** "
                    "para usar todos os recursos do aplicativo."
                )
        else:
            st.info(
                "Faça login na página **Conta** para acessar seus veículos e registros."
            )

        st.divider()

        st.subheader("Preferências")

        st.write(
            "Nesta versão Beta, as preferências avançadas ainda estão em evolução."
        )

        estado_padrao = st.selectbox(
            "Estado padrão para estimativas de energia",
            ["CE", "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "DF"],
            index=0,
            key="config_estado_padrao"
        )

        st.caption(
            f"Estado selecionado para referência visual nesta sessão: {estado_padrao}"
        )

    # -------------------------------------------------------------------------
    # DADOS
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("Como seus dados são organizados")

        st.write(
            "Os registros do EV Care são vinculados à conta do usuário. "
            "Cada conta possui seus próprios veículos, recargas, quilometragem, "
            "manutenções e relatórios."
        )

        st.divider()

        st.subheader("Dados acompanhados pelo aplicativo")

        st.markdown(
            """
            Atualmente o EV Care acompanha:

            - Veículos cadastrados
            - Quilometragem e histórico de KM
            - Recargas e custos
            - Manutenções e plano de serviços
            - Histórico geral
            - Relatórios e exportações para usuários Plus
            """
        )

        st.divider()

        st.subheader("Troca de conta")

        st.info(
            "Ao sair de uma conta e entrar em outra, o aplicativo limpa os dados "
            "da sessão anterior para evitar mistura de informações entre usuários."
        )

    # -------------------------------------------------------------------------
    # BETA
    # -------------------------------------------------------------------------
    with tab3:
        st.subheader("Status do Beta")

        st.write(
            "O EV Care está em fase Beta. Isso significa que o aplicativo já possui "
            "funcionalidades principais, mas ainda pode receber ajustes de interface, "
            "regras de plano, relatórios e melhorias com base nos testes."
        )

        st.divider()

        st.subheader("Checklist recomendado para testes")

        st.markdown(
            """
            Durante os testes, recomendamos validar:

            - Criar conta e fazer login
            - Cadastrar veículo em Minha Garagem
            - Atualizar quilometragem
            - Registrar, editar e excluir recargas
            - Registrar manutenções
            - Adicionar serviço manual ao plano de manutenção
            - Conferir Dashboard
            - Conferir Custos e Economia
            - Conferir Histórico
            - Testar recursos Plus com conta Plus ativa
            """
        )

        st.divider()

        st.subheader("Aviso importante")

        st.warning(
            "Por estar em Beta, o EV Care pode passar por mudanças de layout, "
            "estrutura de planos e regras de uso. Evite inserir informações sensíveis "
            "em campos de observação."
        )

