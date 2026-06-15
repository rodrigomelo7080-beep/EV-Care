import streamlit as st
import json
import csv
import io
from datetime import datetime
from supabase_client import testar_conexao_supabase, testar_cliente_autenticado
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

from veiculo_online_adapter import converter_veiculo_online
from ev_care_base import (
    VeiculoEV,
    MANUTENCOES_EV_DETALHADAS,
    carregar_dados,
    salvar_dados,
    carregar_veiculo_ativo,
    salvar_veiculo_ativo,
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

def inicializar_estado(usuario):
    """
    Carrega garagem e veículo ativo para o usuário informado.
    """
    if "usuario_atual" not in st.session_state or st.session_state.usuario_atual != usuario:
        st.session_state.usuario_atual = usuario
        st.session_state.garagem = carregar_dados(usuario)

        for veiculo in st.session_state.garagem:
            garantir_plano_manutencao_expandido(veiculo)
        st.session_state.veiculo_ativo = carregar_veiculo_ativo(usuario, st.session_state.garagem)
        

        if st.session_state.veiculo_ativo is None and st.session_state.garagem:
            st.session_state.veiculo_ativo = st.session_state.garagem[0]


def salvar_estado():
    """
    Salva garagem e veículo ativo.
    """
    usuario = st.session_state.usuario_atual
    garagem = st.session_state.garagem
    veiculo_ativo = st.session_state.veiculo_ativo

    salvar_dados(garagem, usuario)

    if veiculo_ativo:
        salvar_veiculo_ativo(usuario, garagem, veiculo_ativo)

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


def garantir_planos_garagem():
    """
    Aplica o plano expandido em todos os veículos da garagem.
    """
    alterou_algum = False

    for veiculo in st.session_state.get("garagem", []):
        if garantir_plano_manutencao_expandido(veiculo):
            alterou_algum = True

    if alterou_algum:
        salvar_estado()


def obter_data_ultima_manutencao(veiculo, item):
    """
    Busca a última data de manutenção registrada no histórico textual.
    """
    try:
        for registro in reversed(veiculo.historico):
            if f"] {item} aos " in registro:
                data_txt = registro.split("] ")[0][1:]
                return datetime.strptime(data_txt, "%d/%m/%Y %H:%M")
    except:
        return None

    return None


def obter_metadata_manutencao(veiculo, item):
    """
    Retorna metadados detalhados do serviço.
    """
    detalhes = veiculo.info.get("ManutencaoDetalhada", {})

    if item in detalhes:
        return detalhes[item]

    return {
        "categoria": "Personalizado",
        "intervalo_km": veiculo.plano.get(item, 10000),
        "intervalo_meses": 12,
        "criticidade": "Média",
        "descricao": "Serviço personalizado."
    }

def calcular_status_manutencao(veiculo, item):
    """
    Calcula o status da manutenção com base na última KM real
    em que o serviço foi realizado.

    Regra principal:
    próxima_km = última_km_registrada + intervalo_km

    Status:
    - Vencido: passou da KM ou do prazo
    - Próximo: faltam 20% ou menos do intervalo
    - Em dia: ainda está fora da janela de alerta
    """
    metadata = obter_metadata_manutencao(veiculo, item)

    intervalo_km = int(
        metadata.get(
            "intervalo_km",
            veiculo.plano.get(item, 10000)
        )
    )

    intervalo_meses = int(
        metadata.get(
            "intervalo_meses",
            0
        )
    )

    ultima_km = int(
        veiculo.ultima_revisao.get(item, 0)
    )

    proxima_km = ultima_km + intervalo_km
    km_restante = proxima_km - int(veiculo.km_atual)

    data_ultima = obter_data_ultima_manutencao(veiculo, item)
    dias_restantes = None

    if data_ultima and intervalo_meses > 0:
        dias_intervalo = intervalo_meses * 30
        dias_passados = (datetime.now() - data_ultima).days
        dias_restantes = dias_intervalo - dias_passados
    else:
        dias_intervalo = None

    # -----------------------------
    # Regra de vencimento por KM
    # -----------------------------
    vencido_por_km = km_restante <= 0

    # -----------------------------
    # Regra de proximidade por KM
    # Próximo somente quando faltar 20% ou menos do intervalo
    # Exemplo: intervalo 5000 km → próximo quando faltar 1000 km ou menos
    # -----------------------------
    limite_proximo_km = max(int(intervalo_km * 0.2), 100)
    proximo_por_km = 0 < km_restante <= limite_proximo_km

    # -----------------------------
    # Regra de vencimento por tempo
    # -----------------------------
    vencido_por_tempo = dias_restantes is not None and dias_restantes <= 0

    # -----------------------------
    # Regra de proximidade por tempo
    # Próximo somente quando faltar 20% ou menos do prazo
    # Exemplo: 12 meses ≈ 360 dias → próximo quando faltar 72 dias ou menos
    # Exemplo: 1 mês ≈ 30 dias → próximo quando faltar 6 dias ou menos
    # -----------------------------
    if dias_restantes is not None and dias_intervalo:
        limite_proximo_dias = max(int(dias_intervalo * 0.2), 3)
        proximo_por_tempo = 0 < dias_restantes <= limite_proximo_dias
    else:
        limite_proximo_dias = None
        proximo_por_tempo = False

    if vencido_por_km or vencido_por_tempo:
        status = "Vencido"
    elif proximo_por_km or proximo_por_tempo:
        status = "Próximo"
    else:
        status = "Em dia"

    return {
        "status": status,
        "categoria": metadata.get("categoria", "Geral"),
        "criticidade": metadata.get("criticidade", "Média"),
        "descricao": metadata.get("descricao", ""),
        "intervalo_km": intervalo_km,
        "intervalo_meses": intervalo_meses,
        "ultima_km": ultima_km,
        "proxima_km": proxima_km,
        "km_restante": km_restante,
        "data_ultima": data_ultima,
        "dias_restantes": dias_restantes,
        "limite_proximo_km": limite_proximo_km,
        "limite_proximo_dias": limite_proximo_dias
    }


def obter_veiculo_ativo():
    return st.session_state.get("veiculo_ativo", None)


def obter_garagem():
    return st.session_state.get("garagem", [])

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
    
def calcular_progresso_inicial(garagem, veiculo_ativo):
    """
    Calcula o progresso básico do usuário no primeiro uso do app.
    Não altera dados, apenas analisa o estado atual.
    """
    passos = {
        "Veículo cadastrado": bool(garagem),
        "Veículo ativo selecionado": veiculo_ativo is not None,
        "Primeira recarga registrada": False,
        "Quilometragem atualizada": False,
        "Manutenção configurada": False
    }

    if veiculo_ativo:
        passos["Primeira recarga registrada"] = len(veiculo_ativo.historico_recargas) > 0
        passos["Quilometragem atualizada"] = len(veiculo_ativo.historico_km) > 0
        passos["Manutenção configurada"] = len(veiculo_ativo.plano) > 0

    total = len(passos)
    concluidos = sum(1 for valor in passos.values() if valor)
    progresso = concluidos / total if total > 0 else 0

    return passos, progresso


def mostrar_onboarding_sem_veiculo():
    """
    Tela de boas-vindas para usuários sem veículo cadastrado.
    """
    st.markdown("## Bem-vindo ao EV Care ⚡")

    st.write(
        "O EV Care ajuda você a acompanhar **recargas, custos, autonomia, "
        "quilometragem e manutenções** do seu carro elétrico em um só lugar."
    )

    st.info(
        "Para começar, cadastre seu primeiro veículo em **Minha Garagem**."
    )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 1. Cadastre seu veículo")
        st.write(
            "Adicione um carro pelo catálogo ou manualmente informando bateria, "
            "consumo médio e quilometragem atual."
        )

    with col2:
        st.markdown("### 2. Registre recargas")
        st.write(
            "Cadastre suas recargas para acompanhar gasto total, preço médio "
            "do kWh e custo real por km."
        )

    with col3:
        st.markdown("### 3. Acompanhe manutenções")
        st.write(
            "Use o plano de manutenção EV para saber o que está em dia, próximo "
            "ou vencido."
        )

    st.divider()

    st.success(
        "Fluxo recomendado: Minha Garagem → Quilometragem → Recargas → Manutenções → Dashboard."
    )


def mostrar_guia_primeiro_uso(garagem, veiculo_ativo):
    """
    Mostra um guia de progresso para orientar o usuário.
    """
    passos, progresso = calcular_progresso_inicial(garagem, veiculo_ativo)

    st.subheader("Guia de primeiros passos")

    st.progress(progresso)

    for nome, concluido in passos.items():
        if concluido:
            st.success(f"✅ {nome}")
        else:
            st.warning(f"⬜ {nome}")

    if progresso < 1:
        st.info(
            "Complete os passos acima para aproveitar melhor os cálculos de custo, "
            "consumo real e manutenção."
        )
    else:
        st.success("Configuração inicial concluída. O EV Care já está pronto para uso diário.")


def mostrar_alertas_de_uso(veiculo_ativo):
    """
    Mostra orientações rápidas de uso dentro do Dashboard.
    """
    if not veiculo_ativo:
        return

    alertas = []

    if len(veiculo_ativo.historico_recargas) == 0:
        alertas.append(
            "Registre sua primeira recarga para calcular gastos e custo por km."
        )

    if len(veiculo_ativo.historico_km) == 0:
        alertas.append(
            "Atualize a quilometragem após usar o veículo para melhorar os cálculos reais."
        )

    resumo = veiculo_ativo.obter_resumo_recargas()

    if resumo["custo_real_km"] is None and len(veiculo_ativo.historico_recargas) > 0:
        alertas.append(
            "Para obter custo real por km, registre uma recarga e depois atualize a quilometragem."
        )

    if alertas:
        st.subheader("Orientações rápidas")

        for alerta in alertas:
            st.info(alerta)

def formatar_nome_veiculo(veiculo):
    return f"{veiculo.marca} {veiculo.modelo} - {veiculo.km_atual} km"


def atualizar_veiculo_ativo_por_indice(indice):
    garagem = obter_garagem()

    if garagem and 0 <= indice < len(garagem):
        st.session_state.veiculo_ativo = garagem[indice]
        salvar_estado()

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




# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.title("⚡ EV Care")
st.sidebar.caption("Gestão de carros elétricos")

usuario = "default"

inicializar_estado(usuario)

if st.session_state.get("auth_logado", False):
    carregar_veiculo_online_ativo_para_app()
else:
    inicializar_estado(usuario)

garagem = obter_garagem()
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

with st.sidebar.expander("Guia rápido"):
    passos_sidebar, progresso_sidebar = calcular_progresso_inicial(
        garagem,
        veiculo_ativo
    )

    st.progress(progresso_sidebar)

    for nome, concluido in passos_sidebar.items():
        if concluido:
            st.write(f"✅ {nome}")
        else:
            st.write(f"⬜ {nome}")

    st.caption(
        "Use este guia para completar a configuração inicial do EV Care."
    )


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
garagem = obter_garagem()
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
    if garagem:
        nomes_veiculos = [formatar_nome_veiculo(v) for v in garagem]

        indice_padrao = 0

        if veiculo_ativo in garagem:
            indice_padrao = garagem.index(veiculo_ativo)

        indice_escolhido = st.sidebar.selectbox(
            "Veículo ativo",
            range(len(garagem)),
            format_func=lambda i: nomes_veiculos[i],
            index=indice_padrao
        )

        if garagem[indice_escolhido] != veiculo_ativo:
            atualizar_veiculo_ativo_por_indice(indice_escolhido)
            veiculo_ativo = obter_veiculo_ativo()
    else:
        st.sidebar.warning("Nenhum veículo cadastrado.")


# =============================================================================
# DASHBOARD
# =============================================================================

if pagina == "Dashboard":
    st.header("Dashboard")

    if not validar_contexto_online("Dashboard"):
        st.stop()
    else:
        veiculo_ativo = obter_veiculo_ativo()

        garantir_plano_manutencao_expandido(veiculo_ativo)

        
        st.caption(
            "Garagem, quilometragem e recargas já estão sendo carregadas do banco online."
        )

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
        st.subheader(f"{veiculo_ativo.marca} {veiculo_ativo.modelo}")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "KM atual",
                f"{veiculo_ativo.km_atual:,} km".replace(",", ".")
            )

        with col2:
            st.metric(
                "Autonomia estimada",
                f"{autonomia:.0f} km"
            )

        with col3:
            st.metric(
                "Saúde estimada da bateria",
                f"{saude_bateria:.2f}%"
            )

        with col4:
            st.metric(
                "Recargas registradas",
                resumo_recargas["total_recargas"]
            )

        st.progress(min(max(saude_bateria / 100, 0), 1))

        st.divider()

        # ---------------------------------------------------------------------
        # CUSTOS E EFICIÊNCIA
        # ---------------------------------------------------------------------
        st.subheader("Custos e eficiência")

        col_custo1, col_custo2, col_custo3, col_custo4 = st.columns(4)

        with col_custo1:
            st.metric(
                "Gasto total em recargas",
                f"R$ {resumo_recargas['custo_total']:.2f}"
            )

        with col_custo2:
            st.metric(
                "Energia total carregada",
                f"{resumo_recargas['energia_total']:.2f} kWh"
            )

        with col_custo3:
            if resumo_recargas["custo_real_km"] is not None:
                st.metric(
                    "Custo real por km",
                    f"R$ {resumo_recargas['custo_real_km']:.4f}"
                )
            else:
                st.metric(
                    "Custo real por km",
                    "Indisponível"
                )

        with col_custo4:
            if resumo_recargas["consumo_real_km_kwh"] is not None:
                st.metric(
                    "Consumo real",
                    f"{resumo_recargas['consumo_real_km_kwh']:.2f} km/kWh"
                )
            else:
                st.metric(
                    "Consumo real",
                    "Indisponível"
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
        st.subheader("Última recarga")

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
        st.subheader("Manutenções e alertas")

        itens_manutencao = []

        for item in veiculo_ativo.plano.keys():
            dados_status = calcular_status_manutencao(veiculo_ativo, item)
            itens_manutencao.append((item, dados_status))

        ordem_status = {
            "Vencido": 0,
            "Próximo": 1,
            "Em dia": 2
        }

        itens_manutencao.sort(
            key=lambda x: (
                ordem_status.get(x[1]["status"], 3),
                x[1]["km_restante"]
            )
        )

        vencidos = [x for x in itens_manutencao if x[1]["status"] == "Vencido"]
        proximos = [x for x in itens_manutencao if x[1]["status"] == "Próximo"]
        em_dia = [x for x in itens_manutencao if x[1]["status"] == "Em dia"]

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
        else:
            st.success("Todas as manutenções estão em dia.")

        # ---------------------------------------------------------------------
        # PRÓXIMA MANUTENÇÃO MAIS IMPORTANTE
        # ---------------------------------------------------------------------
        st.write("### Próxima manutenção relevante")

        if itens_manutencao:
            item_mais_relevante, dados_mais_relevante = itens_manutencao[0]

            with st.container(border=True):
                col_p1, col_p2, col_p3 = st.columns(3)

                with col_p1:
                    st.write("**Serviço**")
                    st.write(item_mais_relevante)

                with col_p2:
                    st.write("**Status**")
                    st.write(dados_mais_relevante["status"])

                with col_p3:
                    st.write("**Próxima em**")
                    st.write(f"{dados_mais_relevante['proxima_km']} km")

                st.write(f"**Categoria:** {dados_mais_relevante['categoria']}")
                st.write(f"**Criticidade:** {dados_mais_relevante['criticidade']}")

                if dados_mais_relevante["km_restante"] >= 0:
                    st.write(f"Faltam **{dados_mais_relevante['km_restante']} km**")
                else:
                    st.write(f"Vencida há **{abs(dados_mais_relevante['km_restante'])} km**")

                if dados_mais_relevante["descricao"]:
                    st.caption(dados_mais_relevante["descricao"])
        else:
            st.info("Nenhum item de manutenção cadastrado no plano.")

        st.divider()

        # ---------------------------------------------------------------------
        # LISTA RESUMIDA DE ALERTAS
        # ---------------------------------------------------------------------
        st.subheader("Resumo dos principais alertas")

        if vencidos or proximos:
            for item, dados in itens_manutencao[:5]:
                if dados["status"] == "Vencido":
                    st.error(
                        f"{item}: vencida há {abs(dados['km_restante'])} km "
                        f"(próxima era em {dados['proxima_km']} km)."
                    )
                elif dados["status"] == "Próximo":
                    st.warning(
                        f"{item}: próxima em {dados['proxima_km']} km "
                        f"(faltam {dados['km_restante']} km)."
                    )
        else:
            st.success("Nenhum alerta crítico no momento.")

        st.divider()

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



# =============================================================================
# QUILOMETRAGEM
# =============================================================================

elif pagina == "Quilometragem":
    st.header("Quilometragem")

    if not validar_contexto_online("Quilometragem"):
        st.stop()

    veiculo_ativo = obter_veiculo_ativo()


    st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("KM atual", f"{veiculo_ativo.km_atual} km")

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

    st.subheader("Atualizar quilometragem")

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

    st.subheader("Histórico de quilometragem")

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

# =============================================================================
# RECARGAS
# =============================================================================

elif pagina == "Recargas":
    st.header("Recargas")

    if not validar_contexto_online("Recargas"):
        st.stop()

    veiculo_ativo = obter_veiculo_ativo()

    st.success("Modo online: as recargas serão salvas no Supabase.")

    st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

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
        st.subheader("Registrar nova recarga")

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
        st.subheader("Histórico de recargas online")

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
        st.subheader("Resumo de recargas")

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

        st.subheader("Exportação de recargas")

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

    # -------------------------------------------------------------------------
    # GARANTIR PLANO ONLINE
    # -------------------------------------------------------------------------
    servicos_online, erro_servicos_inicial = listar_servicos_manutencao_online(
        veiculo_ativo.id_online
    )

    if erro_servicos_inicial:
        st.error("Erro ao carregar plano de manutenção online.")
        st.write(erro_servicos_inicial)
        st.stop()

    if not servicos_online:
        ok_plano, resposta_plano = criar_plano_padrao_manutencao_online(
            user_id=st.session_state.auth_user_id,
            veiculo_id=veiculo_ativo.id_online,
            km_atual=veiculo_ativo.km_atual
        )

        if ok_plano:
            st.info("Plano padrão de manutenção online criado para este veículo.")
            servicos_online, erro_servicos_inicial = listar_servicos_manutencao_online(
                veiculo_ativo.id_online
            )
        else:
            st.error("Não foi possível criar o plano padrão de manutenção online.")
            st.write(resposta_plano)
            st.stop()

    resumo_manutencao, erro_resumo_manutencao = obter_resumo_manutencoes_online(
        veiculo_id=veiculo_ativo.id_online,
        km_atual=veiculo_ativo.km_atual
    )

    if erro_resumo_manutencao:
        st.error("Erro ao calcular resumo de manutenção online.")
        st.write(erro_resumo_manutencao)
        st.stop()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Painel de manutenção",
            "Registrar manutenção",
            "Plano manual",
            "Histórico"
        ]
    )

    # -------------------------------------------------------------------------
    # PAINEL DE MANUTENÇÃO ONLINE
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Painel de manutenção")

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
            st.info("Nenhum serviço de manutenção online cadastrado.")
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
                        st.error("Manutenção vencida.")
                    elif dados["status"] == "Próximo":
                        st.warning("Manutenção próxima.")
                    else:
                        st.success("Manutenção em dia.")

    # -------------------------------------------------------------------------
    # REGISTRAR MANUTENÇÃO ONLINE
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("Registrar manutenção realizada")

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

            if st.button("Registrar manutenção online"):
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
                        "Manutenção online registrada com sucesso. "
                        "O cálculo da próxima manutenção foi atualizado."
                    )
                    st.rerun()
                else:
                    st.error("Não foi possível registrar a manutenção online.")
                    st.write(resposta)

    # -------------------------------------------------------------------------
    # PLANO MANUAL ONLINE
    # -------------------------------------------------------------------------
    with tab3:
        st.subheader("Plano manual de manutenção online")

        subtab1, subtab2, subtab3 = st.tabs(
            [
                "Adicionar serviço",
                "Editar serviço",
                "Remover serviço do plano"
            ]
        )

        # ---------------------------------------------------------------------
        # ADICIONAR SERVIÇO ONLINE
        # ---------------------------------------------------------------------
        with subtab1:
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

                adicionar = st.form_submit_button("Adicionar serviço online")

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
                            st.success("Serviço online adicionado com sucesso.")
                            st.rerun()
                        else:
                            st.error("Não foi possível adicionar o serviço online.")
                            st.write(resposta)

        # ---------------------------------------------------------------------
        # EDITAR SERVIÇO ONLINE
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

                    criticidade_atual = servico_edicao.get("criticidade", "Média")

                    opcoes_criticidade = ["Baixa", "Média", "Alta"]

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

                    salvar_edicao = st.form_submit_button("Salvar alterações do serviço online")

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
                                st.success("Serviço online atualizado com sucesso.")
                                st.rerun()
                            else:
                                st.error("Não foi possível atualizar o serviço online.")
                                st.write(resposta)

        # ---------------------------------------------------------------------
        # REMOVER SERVIÇO ONLINE
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

                if st.button("Remover serviço online do plano"):
                    if confirmacao.strip().upper() != "REMOVER":
                        st.warning("Digite REMOVER para confirmar.")
                    else:
                        ok, resposta = desativar_servico_manutencao_online(
                            servico_remocao.get("id")
                        )

                        if ok:
                            st.success("Serviço online removido do plano.")
                            st.rerun()
                        else:
                            st.error("Não foi possível remover o serviço online.")
                            st.write(resposta)

    # -------------------------------------------------------------------------
    # HISTÓRICO DE MANUTENÇÕES ONLINE
    # -------------------------------------------------------------------------
    with tab4:
        st.subheader("Histórico online de manutenções")

        historico_manutencoes, erro_historico = listar_manutencoes_online(
            veiculo_ativo.id_online
        )

        if erro_historico:
            st.error("Erro ao carregar histórico online de manutenções.")
            st.write(erro_historico)
        elif not historico_manutencoes:
            st.info("Nenhuma manutenção online registrada.")
        else:
            for registro in historico_manutencoes:
                with st.container(border=True):
                    st.write(f"**Serviço:** {registro.get('nome_servico', 'Não informado')}")
                    st.write(f"**KM realizada:** {registro.get('km_realizada', 0)} km")
                    st.write(f"**Data:** {registro.get('data_realizada', 'Não informada')}")

                    if registro.get("observacao"):
                        st.write(f"**Observação:** {registro.get('observacao')}")


# =============================================================================
# VIAGENS
# =============================================================================

elif pagina == "Viagens":
    st.header("Planejar Viagem")

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
    st.header("Custos e Economia")

    if not validar_contexto_online("Custos e Economia"):
        st.stop()

    veiculo_ativo = obter_veiculo_ativo()


    st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

    resumo, erro_resumo = obter_resumo_recargas_online(
        veiculo_id=veiculo_ativo.id_online,
        km_atual_veiculo=veiculo_ativo.km_atual
    )

    if erro_resumo:
        st.error("Erro ao carregar resumo online de recargas.")
        st.write(erro_resumo)
        st.stop()

    consumo_ev = float(veiculo_ativo.info.get("Consumo", 6.0))

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

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Custo/km elétrico estimado", f"R$ {custo_ev_km_estimado:.4f}")

    with col2:
        st.metric("Custo/km gasolina", f"R$ {custo_gasolina_km:.4f}")

    with col3:
        st.metric("Gasto total online", f"R$ {resumo['custo_total']:.2f}")

    if custo_ev_km_estimado < custo_gasolina_km:
        st.success("Pela estimativa, o veículo elétrico está mais econômico.")
    else:
        st.warning("Neste cenário, o veículo elétrico não está mais econômico pela estimativa.")

    st.divider()

    st.subheader("Dados reais das recargas online")

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

    st.subheader("Economia real aproximada")

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
    st.header("Histórico")

    if not validar_contexto_online("Histórico"):
        st.stop()

    veiculo_ativo = obter_veiculo_ativo()


    st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

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
        st.subheader("Histórico online de quilometragem")

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
        st.subheader("Histórico de recargas")

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
        st.subheader("Histórico de manutenções")



# VIAGENS

# =============================================================================
# PLANOS
# =============================================================================

elif pagina == "Planos":
    st.header("Planos do EV Care")

    st.write(
        "O EV Care está em fase Beta e atualmente pode ser usado gratuitamente. "
        "No futuro, o aplicativo poderá contar com recursos avançados no plano Plus."
    )

    st.divider()

    col_free, col_plus = st.columns(2)

    with col_free:
        st.subheader("EV Care Free")
        st.caption("Disponível agora")

        st.markdown(
            """
            Ideal para quem quer começar a controlar seu veículo elétrico.

            Inclui:

            - Cadastro de 1 veículo
            - Registro de recargas
            - Atualização de quilometragem
            - Dashboard básico
            - Controle de manutenções
            - Simulação de viagens
            - Custos e economia
            - Histórico básico
            """
        )

        st.success("Plano atual: gratuito durante o Beta")

    with col_plus:
        st.subheader("EV Care Plus")
        st.caption("Em breve")

        st.markdown(
            """
            Pensado para usuários que desejam mais controle, relatórios e automação.

            Recursos planejados:

            - Veículos ilimitados
            - Backup em nuvem
            - Sincronização entre dispositivos
            - Relatórios mensais
            - Exportação em PDF ou Excel
            - Alertas inteligentes de manutenção
            - Gráficos avançados de consumo
            - Comparações mensais de economia
            - Histórico completo avançado
            """
        )

        st.info("Recurso planejado para uma próxima fase")

    st.divider()

    st.subheader("Por que existirão planos pagos?")

    st.write(
        "A proposta do EV Care é manter uma versão gratuita útil para o usuário comum "
        "e oferecer recursos avançados para quem deseja análises mais completas, "
        "relatórios, backup em nuvem e automações."
    )

    st.warning(
        "Durante a fase Beta, os recursos podem mudar conforme testes, feedbacks e evolução do produto."
    )

    st.divider()

    st.subheader("Próxima fase planejada")

    st.markdown(
        """
        A próxima grande evolução técnica será a implementação de:

        - Login de usuários
        - Banco de dados online
        - Dados separados por conta
        - Base para plano Free e Plus
        """
    )
    st.divider()

    st.subheader("Recursos Plus")

    st.write(
        "Estes recursos fazem parte da evolução planejada do EV Care Plus."
    )

    recursos_plus = obter_recursos_plus()

    for codigo_recurso, nome_recurso in recursos_plus.items():
        with st.container(border=True):
            st.write(f"### {nome_recurso}")

            if recurso_disponivel(codigo_recurso):
                st.success("Disponível no seu plano.")
                st.caption(
                    "Este recurso está liberado para usuários Plus ativos. "
                    "Algumas funcionalidades podem ser ativadas progressivamente."
                )
            else:
                st.warning(mensagem_recurso_plus(codigo_recurso))

                if st.session_state.get("auth_logado", False):
                    st.caption(
                        "Seu plano atual ainda não libera este recurso."
                    )
                else:
                    st.caption(
                        "Faça login para verificar seu plano."
                    )

# =============================================================================
# FEEDBACK
# =============================================================================

elif pagina == "Feedback":
    st.header("Feedback do EV Care")

    st.write(
        "O EV Care está em fase Beta. Seu feedback ajuda a melhorar o aplicativo "
        "e a definir quais recursos devem ser priorizados nas próximas versões."
    )

    st.divider()

    st.subheader("O que você pode enviar?")

    st.markdown(
        """
        - Sugestões de novas funcionalidades
        - Problemas encontrados durante o uso
        - Dificuldades em alguma tela
        - Ideias para melhorar recargas, manutenções ou custos
        - Interesse no futuro plano EV Care Plus
        """
    )

    st.divider()

    st.subheader("Interesse no EV Care Plus")

    interesse_plus = st.multiselect(
        "Quais recursos premium você considera mais úteis?",
        [
            "Veículos ilimitados",
            "Backup em nuvem",
            "Relatórios mensais",
            "Exportação em PDF",
            "Exportação em Excel",
            "Alertas inteligentes de manutenção",
            "Gráficos avançados de consumo",
            "Comparação mensal de economia",
            "Histórico avançado",
            "Sincronização entre dispositivos"
        ]
    )

    if interesse_plus:
        st.success("Obrigado! Esses interesses ajudam a priorizar o EV Care Plus.")
        st.write("Recursos selecionados:")
        for item in interesse_plus:
            st.write(f"- {item}")

    st.divider()

    st.subheader("Modelo de feedback")

    st.info(
        "Nesta versão Beta, o envio automático ainda será estruturado. "
        "Por enquanto, use este modelo para coletar opiniões e relatos de teste."
    )

    st.markdown(
        """
        **Modelo sugerido:**

        - Nome:
        - Modelo do veículo:
        - Página onde ocorreu o problema:
        - O que você tentou fazer:
        - O que aconteceu:
        - O que você esperava:
        - Sugestão de melhoria:
        - Você teria interesse no EV Care Plus? Sim/Não
        """
    )

    st.warning(
        "Não envie senhas, documentos pessoais, dados bancários ou informações sensíveis nesta fase Beta."
    )

    # =============================================================================
# CONTA
# =============================================================================

elif pagina == "Conta":
    st.header("Conta")

    if st.session_state.auth_logado:
        st.success("Usuário logado")

        st.write(f"**E-mail:** {st.session_state.auth_email}")
        st.write(f"**Nome:** {st.session_state.auth_nome}")
        st.write(f"**Plano atual:** {st.session_state.auth_plano}")
        st.write(f"**Status da assinatura:** {st.session_state.get('auth_status_assinatura', 'inactive')}")

        st.info(
            "Nesta fase, o login já está conectado ao Supabase. "
            "Nas próximas etapas, garagem, recargas e manutenções serão migradas para o banco online."
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
            senha_login = st.text_input("Senha", type="password", key="login_senha")

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
            senha_cadastro = st.text_input("Senha", type="password", key="cadastro_senha")

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

# =============================================================================
# MINHA GARAGEM
# =============================================================================

elif pagina == "Minha Garagem":
    st.header("Minha Garagem")

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

            st.subheader("Veículos cadastrados na nuvem")

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

            st.subheader("Cadastrar veículo online")

            pode_criar, mensagem_bloqueio = pode_criar_veiculo(quantidade)

            if not pode_criar:
                st.warning(mensagem_bloqueio)
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

elif pagina == "Configurações":
    st.header("Configurações")

    st.subheader("Conta")

    if st.session_state.get("auth_logado", False):
        st.write(f"**E-mail:** {st.session_state.auth_email}")
        st.write(f"**Plano atual:** {st.session_state.auth_plano}")
        st.write(
            f"**Status da assinatura:** "
            f"{st.session_state.get('auth_status_assinatura', 'inactive')}"
        )
    else:
        st.info("Faça login para visualizar as configurações da conta.")

    st.divider()

    st.subheader("Dados")

    st.write(
        "Os dados de veículos, quilometragem, recargas e manutenções "
        "são vinculados à sua conta."
    )

