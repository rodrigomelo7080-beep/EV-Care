import streamlit as st
import json
from datetime import datetime

from ev_care_base import (
    VeiculoEV,
    DADOS_VEICULOS,
    REVISAO_PADRAO_GENERICA,
    MANUTENCOES_EV_DETALHADAS,
    FATOR_DEGRADACAO_PADRAO,
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


# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.title("⚡ EV Care")
st.sidebar.caption("Gestão de carros elétricos")

usuario = st.sidebar.text_input("Usuário", value="default")
usuario = usuario.strip() if usuario.strip() else "default"

inicializar_estado(usuario)

garagem = obter_garagem()
veiculo_ativo = obter_veiculo_ativo()

st.sidebar.divider()

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
        "Configurações"
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

if st.sidebar.button("Recarregar dados"):
    st.session_state.garagem = carregar_dados(usuario)
    st.session_state.veiculo_ativo = carregar_veiculo_ativo(usuario, st.session_state.garagem)

    if st.session_state.veiculo_ativo is None and st.session_state.garagem:
        st.session_state.veiculo_ativo = st.session_state.garagem[0]

    st.rerun()


# =============================================================================
# CABEÇALHO
# =============================================================================

st.title("⚡ EV Care")
st.caption("Aplicativo para gestão de veículos elétricos")

# Atualiza referências após possíveis mudanças
garagem = obter_garagem()
veiculo_ativo = obter_veiculo_ativo()


# =============================================================================
# DASHBOARD
# =============================================================================

if pagina == "Dashboard":
    st.header("Dashboard")

    if not veiculo_ativo:
        mostrar_onboarding_sem_veiculo()
    else:
        # Garante que o plano de manutenção esteja atualizado para veículos antigos
        garantir_plano_manutencao_expandido(veiculo_ativo)
        mostrar_guia_primeiro_uso(garagem, veiculo_ativo)        
        st.divider()



        resumo_recargas = veiculo_ativo.obter_resumo_recargas()
        ultima_recarga = veiculo_ativo.obter_ultima_recarga()

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
        # ÚLTIMA RECARGA
        # ---------------------------------------------------------------------
        st.subheader("Última recarga")

        if ultima_recarga:
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)

            with col_r1:
                st.write("**Data**")
                st.write(ultima_recarga.get("data", "Não informada"))

            with col_r2:
                st.write("**Local**")
                st.write(ultima_recarga.get("local", "Não informado"))

            with col_r3:
                st.write("**Energia**")
                st.write(f"{ultima_recarga.get('energia_kwh', 0):.2f} kWh")

            with col_r4:
                st.write("**Custo**")
                st.write(f"R$ {ultima_recarga.get('custo_total', 0):.2f}")

            st.write(
                f"**Bateria:** "
                f"{ultima_recarga.get('bateria_inicial', 0):.1f}% → "
                f"{ultima_recarga.get('bateria_final', 0):.1f}%"
            )

            st.write(f"**Tipo:** {ultima_recarga.get('tipo', 'Não informado')}")
        else:
            st.info("Nenhuma recarga registrada ainda.")

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
        mostrar_alertas_de_uso(veiculo_ativo)

        st.divider()

        st.caption(
            "Este dashboard usa os dados salvos da garagem, recargas, quilometragem "
            "e plano de manutenção do veículo ativo."
        )


# =============================================================================
# MINHA GARAGEM
# =============================================================================

elif pagina == "Minha Garagem":
    st.header("Minha Garagem")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Veículos cadastrados",
        "Adicionar pelo catálogo",
        "Cadastro manual",
        "Editar veículo",
        "Excluir veículo"
    ]
)

    # -------------------------------------------------------------------------
    # EXCLUIR VEÍCULO
    # -------------------------------------------------------------------------
    with tab5:
        st.subheader("Excluir veículo")

        if not garagem:
            st.info("Nenhum veículo cadastrado para excluir.")
        else:
            st.warning(
                "Atenção: excluir um veículo apagará também suas recargas, "
                "manutenções e histórico de quilometragem."
            )

            nomes_veiculos_exclusao = [
                f"{v.marca} {v.modelo} - {v.km_atual} km"
                for v in garagem
            ]

            indice_exclusao = st.selectbox(
                "Selecione o veículo que deseja excluir",
                range(len(garagem)),
                format_func=lambda i: nomes_veiculos_exclusao[i],
                key="indice_exclusao_veiculo"
            )

            veiculo_exclusao = garagem[indice_exclusao]

            st.divider()

            st.write("### Dados do veículo selecionado")
            st.write(f"**Marca/modelo:** {veiculo_exclusao.marca} {veiculo_exclusao.modelo}")
            st.write(f"**KM atual:** {veiculo_exclusao.km_atual} km")
            st.write(f"**Bateria:** {veiculo_exclusao.info.get('Bateria', 'Não informada')}")
            st.write(f"**Consumo:** {veiculo_exclusao.info.get('Consumo', 0)} km/kWh")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Recargas", len(veiculo_exclusao.historico_recargas))

            with col2:
                st.metric("Manutenções", len(veiculo_exclusao.historico))

            with col3:
                st.metric("Registros de KM", len(veiculo_exclusao.historico_km))

            st.divider()

            st.error(
                "Esta ação não pode ser desfeita dentro do aplicativo. "
                "Se tiver dúvida, exporte um backup JSON antes de excluir."
            )

            confirmacao = st.text_input(
                "Para confirmar, digite EXCLUIR",
                key="confirmacao_excluir_veiculo"
            )

            if st.button("Excluir veículo selecionado", type="primary"):
                if confirmacao.strip().upper() != "EXCLUIR":
                    st.warning("Digite EXCLUIR para confirmar a exclusão.")
                else:
                    era_veiculo_ativo = veiculo_ativo is veiculo_exclusao

                    garagem.pop(indice_exclusao)

                    if era_veiculo_ativo:
                        if garagem:
                            st.session_state.veiculo_ativo = garagem[0]
                        else:
                            st.session_state.veiculo_ativo = None

                    salvar_estado()

                    st.success("Veículo excluído com sucesso.")
                    st.rerun()

    # -------------------------------------------------------------------------
    # VEÍCULOS CADASTRADOS
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Veículos cadastrados")

        if not garagem:
            st.info("Nenhum veículo cadastrado ainda.")
        else:
            for i, v in enumerate(garagem):
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.write("**Veículo**")
                        st.write(f"{v.marca} {v.modelo}")

                    with col2:
                        st.write("**KM atual**")
                        st.write(f"{v.km_atual} km")

                    with col3:
                        st.write("**Autonomia estimada**")
                        st.write(f"{v.calcular_autonomia():.0f} km")

                    with col4:
                        if st.button("Selecionar", key=f"selecionar_{i}"):
                            st.session_state.veiculo_ativo = v
                            salvar_estado()
                            st.success("Veículo ativo atualizado.")
                            st.rerun()

                    st.write(f"**Bateria:** {v.info.get('Bateria', 'Não informada')}")
                    st.write(f"**Consumo:** {v.info.get('Consumo', 0)} km/kWh")
                    st.write(f"**Recargas registradas:** {len(v.historico_recargas)}")
                    st.write(f"**Manutenções registradas:** {len(v.historico)}")

    # -------------------------------------------------------------------------
    # ADICIONAR PELO CATÁLOGO
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("Adicionar veículo do catálogo")

        marcas = sorted(list(DADOS_VEICULOS.keys()))

        marca = st.selectbox("Marca", marcas, key="catalogo_marca")
        modelos = sorted(list(DADOS_VEICULOS[marca].keys()))
        modelo = st.selectbox("Modelo", modelos, key="catalogo_modelo")
        km = st.number_input("KM atual", min_value=0, step=100, key="km_catalogo")

        dados_modelo = DADOS_VEICULOS[marca][modelo]

        st.write("**Dados técnicos:**")
        st.write(f"Bateria: {dados_modelo.get('Bateria')}")
        st.write(f"Potência: {dados_modelo.get('Potencia')}")
        st.write(f"Torque: {dados_modelo.get('Torque')}")
        st.write(f"Consumo: {dados_modelo.get('Consumo')} km/kWh")

        if st.button("Adicionar veículo do catálogo"):
            novo = VeiculoEV(marca, modelo, km, dados_modelo)
            garagem.append(novo)
            st.session_state.veiculo_ativo = novo
            salvar_estado()
            st.success(f"{marca} {modelo} adicionado com sucesso.")
            st.rerun()

    # -------------------------------------------------------------------------
    # CADASTRO MANUAL
    # -------------------------------------------------------------------------
    with tab3:
        st.subheader("Cadastro manual")

        with st.form("form_cadastro_manual"):
            marca_manual = st.text_input("Marca")
            modelo_manual = st.text_input("Modelo")
            km_manual = st.number_input("KM atual", min_value=0, step=100)
            bateria_manual = st.number_input("Capacidade da bateria em kWh", min_value=0.1, step=0.1)
            consumo_manual = st.number_input("Consumo médio em km/kWh", min_value=0.1, step=0.1)

            enviar_manual = st.form_submit_button("Cadastrar veículo manualmente")

            if enviar_manual:
                if not marca_manual.strip() or not modelo_manual.strip():
                    st.error("Marca e modelo são obrigatórios.")
                else:
                    info_custom = {
                        "Bateria": f"{bateria_manual} kWh",
                        "Potencia": "Não informada",
                        "Torque": "Não informado",
                        "Consumo": consumo_manual,
                        "Revisao": REVISAO_PADRAO_GENERICA,
                        "FatorDegradacao": FATOR_DEGRADACAO_PADRAO
                    }

                    novo = VeiculoEV(
                        marca_manual.strip(),
                        modelo_manual.strip(),
                        km_manual,
                        info_custom
                    )

                    garagem.append(novo)
                    st.session_state.veiculo_ativo = novo
                    salvar_estado()
                    st.success("Veículo cadastrado com sucesso.")
                    st.rerun()

    # -------------------------------------------------------------------------
    # EDITAR VEÍCULO
    # -------------------------------------------------------------------------
    with tab4:
        st.subheader("Editar veículo")

        if not garagem:
            st.info("Nenhum veículo cadastrado para editar.")
        else:
            nomes_veiculos_edicao = [
                f"{v.marca} {v.modelo} - {v.km_atual} km"
                for v in garagem
            ]

            indice_edicao = st.selectbox(
                "Selecione o veículo que deseja editar",
                range(len(garagem)),
                format_func=lambda i: nomes_veiculos_edicao[i],
                key="indice_edicao_veiculo"
            )

            veiculo_edicao = garagem[indice_edicao]

            st.info(
                "A edição preserva recargas, manutenções e histórico. "
                "A quilometragem só pode ser aumentada para manter a consistência dos dados."
            )

            # Tenta extrair a capacidade da bateria atual
            try:
                bateria_atual = float(str(veiculo_edicao.info.get("Bateria", "0")).split()[0])
            except:
                bateria_atual = 0.1

            try:
                consumo_atual = float(veiculo_edicao.info.get("Consumo", 6.0))
            except:
                consumo_atual = 6.0

            with st.form("form_editar_veiculo"):
                nova_marca = st.text_input(
                    "Marca",
                    value=veiculo_edicao.marca
                )

                novo_modelo = st.text_input(
                    "Modelo",
                    value=veiculo_edicao.modelo
                )

                nova_km = st.number_input(
                    "Quilometragem atual",
                    min_value=0,
                    step=100,
                    value=int(veiculo_edicao.km_atual)
                )

                nova_bateria = st.number_input(
                    "Capacidade da bateria em kWh",
                    min_value=0.1,
                    step=0.1,
                    value=float(bateria_atual) if bateria_atual > 0 else 0.1
                )

                novo_consumo = st.number_input(
                    "Consumo médio em km/kWh",
                    min_value=0.1,
                    step=0.1,
                    value=float(consumo_atual) if consumo_atual > 0 else 6.0
                )

                confirmar_edicao = st.form_submit_button("Salvar alterações do veículo")

                if confirmar_edicao:
                    if not nova_marca.strip() or not novo_modelo.strip():
                        st.error("Marca e modelo não podem ficar vazios.")
                    elif nova_km < veiculo_edicao.km_atual:
                        st.error(
                            f"A nova KM não pode ser menor que a atual "
                            f"({veiculo_edicao.km_atual} km)."
                        )
                    else:
                        # Atualiza marca e modelo
                        veiculo_edicao.marca = nova_marca.strip().upper()
                        veiculo_edicao.modelo = novo_modelo.strip().upper()

                        # Atualiza KM usando o método existente para preservar histórico
                        if nova_km > veiculo_edicao.km_atual:
                            veiculo_edicao.atualizar_km(nova_km)

                        # Preserva dados técnicos já existentes e atualiza bateria/consumo
                        veiculo_edicao.info["Bateria"] = f"{nova_bateria} kWh"
                        veiculo_edicao.info["Consumo"] = novo_consumo

                        # Garante que campos essenciais continuem existindo
                        if "Revisao" not in veiculo_edicao.info:
                            veiculo_edicao.info["Revisao"] = REVISAO_PADRAO_GENERICA

                        if "FatorDegradacao" not in veiculo_edicao.info:
                            veiculo_edicao.info["FatorDegradacao"] = FATOR_DEGRADACAO_PADRAO

                        # Atualiza referências internas do plano e fator
                        veiculo_edicao.plano = veiculo_edicao.info.get(
                            "Revisao",
                            REVISAO_PADRAO_GENERICA
                        )

                        veiculo_edicao.fator_degradacao = veiculo_edicao.info.get(
                            "FatorDegradacao",
                            FATOR_DEGRADACAO_PADRAO
                        )

                        # Se o veículo editado for o ativo, mantém como ativo
                        if veiculo_ativo is veiculo_edicao:
                            st.session_state.veiculo_ativo = veiculo_edicao

                        salvar_estado()

                        st.success("Veículo editado com sucesso.")
                        st.rerun()

            st.divider()

            st.subheader("Dados preservados")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Recargas", len(veiculo_edicao.historico_recargas))

            with col2:
                st.metric("Manutenções", len(veiculo_edicao.historico))

            with col3:
                st.metric("Registros de KM", len(veiculo_edicao.historico_km))

            st.write("Esses dados não serão apagados ao editar o veículo.")




# =============================================================================
# QUILOMETRAGEM
# =============================================================================

elif pagina == "Quilometragem":
    st.header("Quilometragem")

    if not veiculo_ativo:
        st.warning("Selecione ou cadastre um veículo antes de atualizar a quilometragem.")
    else:
        st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("KM atual", f"{veiculo_ativo.km_atual} km")

        with col2:
            st.metric("Autonomia estimada", f"{veiculo_ativo.calcular_autonomia():.0f} km")

        with col3:
            st.metric("Saúde estimada da bateria", f"{veiculo_ativo.calcular_saude_bateria():.2f}%")

        st.divider()

        st.subheader("Atualizar quilometragem")

        with st.form("form_atualizar_quilometragem"):
            nova_km = st.number_input(
                "Nova quilometragem",
                min_value=0,
                step=100,
                value=int(veiculo_ativo.km_atual)
            )

            confirmar = st.form_submit_button("Atualizar KM")

            if confirmar:
                if nova_km < veiculo_ativo.km_atual:
                    st.error(f"A nova KM deve ser maior ou igual à atual ({veiculo_ativo.km_atual} km).")
                elif nova_km == veiculo_ativo.km_atual:
                    st.info("A quilometragem informada é igual à atual. Nenhuma alteração foi feita.")
                else:
                    if veiculo_ativo.atualizar_km(nova_km):
                        salvar_estado()
                        st.success("Quilometragem atualizada com sucesso.")
                        st.rerun()
                    else:
                        st.error("Não foi possível atualizar a quilometragem.")

        st.divider()

        st.subheader("Histórico de quilometragem")

        if not veiculo_ativo.historico_km:
            st.info("Ainda não há registros de alteração de quilometragem.")
        else:
            for registro in reversed(veiculo_ativo.historico_km):
                with st.container(border=True):
                    st.write(f"**Data:** {registro.get('data', 'Não informada')}")
                    st.write(f"**KM anterior:** {registro.get('km_anterior', 0)} km")
                    st.write(f"**Nova KM:** {registro.get('km_nova', 0)} km")

                    diferenca = int(registro.get("km_nova", 0)) - int(registro.get("km_anterior", 0))

                    if diferenca >= 0:
                        st.write(f"**Diferença registrada:** {diferenca} km")

# =============================================================================
# RECARGAS
# =============================================================================

elif pagina == "Recargas":
    st.header("Recargas")

    if not veiculo_ativo:
        st.warning("Cadastre ou selecione um veículo antes de registrar recargas.")
    else:
        st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

        tab1, tab2, tab3 = st.tabs(
            [
                "Registrar recarga",
                "Histórico / Editar / Excluir",
                "Resumo"
            ]
        )

        # ---------------------------------------------------------------------
        # REGISTRAR RECARGA
        # ---------------------------------------------------------------------
        with tab1:
            st.subheader("Registrar nova recarga")

            with st.form("form_registrar_recarga"):
                bateria_inicial = st.number_input(
                    "Bateria inicial (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    key="nova_bateria_inicial"
                )

                bateria_final = st.number_input(
                    "Bateria final (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    key="nova_bateria_final"
                )

                energia_kwh = st.number_input(
                    "Energia carregada (kWh)",
                    min_value=0.01,
                    step=0.1,
                    key="nova_energia_kwh"
                )

                preco_kwh = st.number_input(
                    "Preço do kWh (R$)",
                    min_value=0.0,
                    step=0.01,
                    value=0.63,
                    key="novo_preco_kwh"
                )

                local = st.text_input(
                    "Local da recarga",
                    key="novo_local_recarga"
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
                    key="novo_tipo_recarga"
                )

                salvar_recarga = st.form_submit_button("Registrar recarga")

                if salvar_recarga:
                    if veiculo_ativo.registrar_recarga(
                        bateria_inicial,
                        bateria_final,
                        energia_kwh,
                        preco_kwh,
                        local,
                        tipo
                    ):
                        salvar_estado()
                        st.success(f"Recarga registrada. Custo total: R$ {energia_kwh * preco_kwh:.2f}")
                        st.rerun()
                    else:
                        st.error("Não foi possível registrar a recarga. Verifique os dados informados.")

        # ---------------------------------------------------------------------
        # HISTÓRICO, EDITAR E EXCLUIR
        # ---------------------------------------------------------------------
        with tab2:
            st.subheader("Histórico de recargas")

            if not veiculo_ativo.historico_recargas:
                st.info("Nenhuma recarga registrada.")
            else:
                for i, r in enumerate(veiculo_ativo.historico_recargas):
                    titulo = (
                        f"Recarga {i + 1} - "
                        f"{r.get('data', 'Data não informada')} - "
                        f"{r.get('local', 'Local não informado')}"
                    )

                    with st.expander(titulo):
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.write("**Data**")
                            st.write(r.get("data", "Não informada"))

                            if r.get("data_edicao"):
                                st.caption(f"Editada em: {r.get('data_edicao')}")

                        with col2:
                            st.write("**Bateria**")
                            st.write(
                                f"{r.get('bateria_inicial', 0):.1f}% → "
                                f"{r.get('bateria_final', 0):.1f}%"
                            )

                        with col3:
                            st.write("**Energia**")
                            st.write(f"{r.get('energia_kwh', 0):.2f} kWh")

                        with col4:
                            st.write("**Custo**")
                            st.write(f"R$ {r.get('custo_total', 0):.2f}")

                        st.write(f"**Preço do kWh:** R$ {r.get('preco_kwh', 0):.2f}")
                        st.write(f"**Local:** {r.get('local', 'Não informado')}")
                        st.write(f"**Tipo:** {r.get('tipo', 'Não informado')}")
                        st.write(f"**KM no momento da recarga:** {r.get('km_atual', 0)} km")

                        st.divider()

                        # -----------------------------------------------------
                        # EDITAR RECARGA
                        # -----------------------------------------------------
                        st.write("### Editar esta recarga")

                        with st.form(f"form_editar_recarga_{i}"):
                            nova_bateria_inicial = st.number_input(
                                "Bateria inicial (%)",
                                min_value=0.0,
                                max_value=100.0,
                                step=1.0,
                                value=float(r.get("bateria_inicial", 0)),
                                key=f"editar_bateria_inicial_{i}"
                            )

                            nova_bateria_final = st.number_input(
                                "Bateria final (%)",
                                min_value=0.0,
                                max_value=100.0,
                                step=1.0,
                                value=float(r.get("bateria_final", 0)),
                                key=f"editar_bateria_final_{i}"
                            )

                            nova_energia_kwh = st.number_input(
                                "Energia carregada (kWh)",
                                min_value=0.01,
                                step=0.1,
                                value=float(r.get("energia_kwh", 0.01)),
                                key=f"editar_energia_{i}"
                            )

                            novo_preco_kwh = st.number_input(
                                "Preço do kWh (R$)",
                                min_value=0.0,
                                step=0.01,
                                value=float(r.get("preco_kwh", 0)),
                                key=f"editar_preco_{i}"
                            )

                            novo_local = st.text_input(
                                "Local da recarga",
                                value=r.get("local", "Não informado"),
                                key=f"editar_local_{i}"
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
                                key=f"editar_tipo_{i}"
                            )

                            novo_custo_total = nova_energia_kwh * novo_preco_kwh

                            st.info(f"Custo total recalculado: R$ {novo_custo_total:.2f}")

                            confirmar_edicao = st.form_submit_button("Salvar alterações desta recarga")

                            if confirmar_edicao:
                                if veiculo_ativo.editar_recarga(
                                    i,
                                    nova_bateria_inicial,
                                    nova_bateria_final,
                                    nova_energia_kwh,
                                    novo_preco_kwh,
                                    novo_local,
                                    novo_tipo
                                ):
                                    salvar_estado()
                                    st.success("Recarga editada com sucesso.")
                                    st.rerun()
                                else:
                                    st.error("Não foi possível editar a recarga. Verifique os dados.")

                        st.divider()

                        # -----------------------------------------------------
                        # EXCLUIR RECARGA
                        # -----------------------------------------------------
                        st.write("### Excluir esta recarga")

                        confirmar_exclusao = st.checkbox(
                            "Confirmo que desejo excluir esta recarga",
                            key=f"confirmar_excluir_{i}"
                        )

                        if st.button("Excluir recarga", key=f"botao_excluir_recarga_{i}"):
                            if confirmar_exclusao:
                                if veiculo_ativo.excluir_recarga(i):
                                    salvar_estado()
                                    st.success("Recarga excluída com sucesso.")
                                    st.rerun()
                                else:
                                    st.error("Não foi possível excluir a recarga.")
                            else:
                                st.warning("Marque a confirmação antes de excluir.")

        # ---------------------------------------------------------------------
        # RESUMO
        # ---------------------------------------------------------------------
        with tab3:
            st.subheader("Resumo de recargas")

            resumo = veiculo_ativo.obter_resumo_recargas()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total de recargas", resumo["total_recargas"])

            with col2:
                st.metric("Energia total", f"{resumo['energia_total']:.2f} kWh")

            with col3:
                st.metric("Gasto total", f"R$ {resumo['custo_total']:.2f}")

            col4, col5, col6 = st.columns(3)

            with col4:
                st.metric("Custo médio por recarga", f"R$ {resumo['custo_medio_recarga']:.2f}")

            with col5:
                st.metric("Preço médio kWh", f"R$ {resumo['preco_medio_kwh']:.2f}")

            with col6:
                if resumo["custo_real_km"] is not None:
                    st.metric("Custo real por km", f"R$ {resumo['custo_real_km']:.4f}")
                else:
                    st.metric("Custo real por km", "Indisponível")

            if resumo["consumo_real_km_kwh"] is not None:
                st.success(f"Consumo real aproximado: {resumo['consumo_real_km_kwh']:.2f} km/kWh")
                st.write(f"KM considerados desde a primeira recarga: {resumo['km_rodados']} km")
            else:
                st.info("Para calcular consumo real, registre recargas e atualize a quilometragem após usar o veículo.")

   

# =============================================================================
# MANUTENÇÕES
# =============================================================================

elif pagina == "Manutenções":
    st.header("Manutenções")

    if not veiculo_ativo:
        st.warning("Selecione um veículo primeiro.")
    else:
        garantir_plano_manutencao_expandido(veiculo_ativo)

        st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "Painel de manutenção",
                "Registrar manutenção",
                "Plano manual",
                "Histórico"
            ]
        )

        # ---------------------------------------------------------------------
        # PAINEL DE MANUTENÇÃO
        # ---------------------------------------------------------------------
        with tab1:
            st.subheader("Painel de manutenção")

            itens_status = []

            for item in veiculo_ativo.plano.keys():
                dados_status = calcular_status_manutencao(veiculo_ativo, item)
                itens_status.append((item, dados_status))

            ordem = {
                "Vencido": 0,
                "Próximo": 1,
                "Em dia": 2
            }

            itens_status.sort(key=lambda x: ordem.get(x[1]["status"], 3))

            vencidos = sum(1 for _, d in itens_status if d["status"] == "Vencido")
            proximos = sum(1 for _, d in itens_status if d["status"] == "Próximo")
            em_dia = sum(1 for _, d in itens_status if d["status"] == "Em dia")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Vencidos", vencidos)

            with col2:
                st.metric("Próximos", proximos)

            with col3:
                st.metric("Em dia", em_dia)

            st.divider()

        for item, dados in itens_status:
                with st.container(border=True):
                    col_a, col_b, col_c = st.columns(3)

                    with col_a:
                        st.write(f"### {item}")
                        st.write(f"Categoria: **{dados['categoria']}**")
                        st.write(f"Criticidade: **{dados['criticidade']}**")

                    with col_b:
                        st.write(f"Status: **{dados['status']}**")
                        st.write(f"Intervalo: {dados['intervalo_km']} km")

                        if dados["intervalo_meses"]:
                            st.write(f"Tempo: {dados['intervalo_meses']} meses")

                    with col_c:
                        st.write(f"Última feita em: **{dados['ultima_km']} km**")
                        st.write(f"Próxima em: **{dados['proxima_km']} km**")

                        if dados["km_restante"] >= 0:
                            st.write(f"Faltam: **{dados['km_restante']} km**")
                        else:
                            st.write(f"Vencida há: **{abs(dados['km_restante'])} km**")

                        if dados["dias_restantes"] is not None:
                            if dados["dias_restantes"] >= 0:
                                st.write(f"Dias restantes: **{dados['dias_restantes']}**")
                            else:
                                st.write(f"Vencida há: **{abs(dados['dias_restantes'])} dias**")

                        with st.expander("Detalhes do cálculo"):
                            st.write(f"Intervalo KM: {dados['intervalo_km']}")
                            st.write(f"Limite para status Próximo por KM: {dados['limite_proximo_km']} km")
                            st.write(f"Intervalo em meses: {dados['intervalo_meses']}")
                            st.write(f"Limite para status Próximo por tempo: {dados['limite_proximo_dias']} dias")

                    if dados["descricao"]:
                        st.caption(dados["descricao"])

                    if dados["status"] == "Vencido":
                        st.error("Manutenção vencida.")
                    elif dados["status"] == "Próximo":
                        st.warning("Manutenção próxima.")
                    else:
                        st.success("Manutenção em dia.")

        # ---------------------------------------------------------------------
        # REGISTRAR MANUTENÇÃO
        # ---------------------------------------------------------------------
        with tab2:
            st.subheader("Registrar manutenção realizada")

            itens = sorted(list(veiculo_ativo.plano.keys()))

            if not itens:
                st.info("Nenhum serviço cadastrado no plano.")
            else:
                item_escolhido = st.selectbox(
                    "Serviço realizado",
                    itens,
                    key="item_manutencao_registro"
                )

                dados = calcular_status_manutencao(veiculo_ativo, item_escolhido)

                st.info(
                    f"Serviço: {item_escolhido} | "
                    f"Status atual: {dados['status']} | "
                    f"KM atual: {veiculo_ativo.km_atual} km"
                )

                if st.button("Registrar manutenção"):
                    if veiculo_ativo.registrar_servico(item_escolhido):
                        # Garante que a última revisão foi gravada na KM atual real
                        veiculo_ativo.ultima_revisao[item_escolhido] = int(veiculo_ativo.km_atual)

                        salvar_estado()

                        dados_atualizados = calcular_status_manutencao(
                            veiculo_ativo,
                            item_escolhido
                        )

                        st.success(
                            f"Manutenção registrada com sucesso. "
                            f"Próxima em {dados_atualizados['proxima_km']} km."
                        )

                        st.rerun()
                    else:
                        st.error("Não foi possível registrar a manutenção.")

        # ---------------------------------------------------------------------
        # PLANO MANUAL
        # ---------------------------------------------------------------------
        with tab3:
            st.subheader("Plano manual de manutenção")

            st.write(
                "Aqui você pode adicionar serviços que não estão no plano padrão "
                "ou editar intervalos de serviços existentes."
            )

            subtab1, subtab2, subtab3 = st.tabs(
                [
                    "Adicionar serviço",
                    "Editar serviço",
                    "Remover serviço do plano"
                ]
            )

            # ADICIONAR SERVIÇO
            with subtab1:
                with st.form("form_adicionar_servico_manual"):
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

                    adicionar = st.form_submit_button("Adicionar ao plano")

                    if adicionar:
                        nome_limpo = nome_servico.strip()

                        if not nome_limpo:
                            st.error("Informe o nome do serviço.")
                        elif nome_limpo in veiculo_ativo.plano:
                            st.warning("Esse serviço já existe no plano.")
                        else:
                            if "ManutencaoDetalhada" not in veiculo_ativo.info:
                                veiculo_ativo.info["ManutencaoDetalhada"] = {}

                            if "Revisao" not in veiculo_ativo.info:
                                veiculo_ativo.info["Revisao"] = {}

                            veiculo_ativo.info["Revisao"][nome_limpo] = int(intervalo_km)

                            veiculo_ativo.info["ManutencaoDetalhada"][nome_limpo] = {
                                "categoria": categoria.strip() if categoria.strip() else "Personalizado",
                                "intervalo_km": int(intervalo_km),
                                "intervalo_meses": int(intervalo_meses),
                                "criticidade": criticidade,
                                "descricao": descricao.strip()
                            }

                            veiculo_ativo.plano = veiculo_ativo.info["Revisao"]
                            veiculo_ativo.ultima_revisao[nome_limpo] = 0

                            salvar_estado()

                            st.success("Serviço manual adicionado com sucesso.")
                            st.rerun()

            # EDITAR SERVIÇO
            with subtab2:
                itens_edicao = sorted(list(veiculo_ativo.plano.keys()))

                if not itens_edicao:
                    st.info("Nenhum serviço disponível para edição.")
                else:
                    item_edicao = st.selectbox(
                        "Selecione o serviço para editar",
                        itens_edicao,
                        key="item_edicao_manutencao"
                    )

                    meta = obter_metadata_manutencao(veiculo_ativo, item_edicao)

                    with st.form("form_editar_servico_manutencao"):
                        nova_categoria = st.text_input(
                            "Categoria",
                            value=meta.get("categoria", "Geral")
                        )

                        novo_intervalo_km = st.number_input(
                            "Intervalo em km",
                            min_value=1,
                            step=1000,
                            value=int(meta.get("intervalo_km", veiculo_ativo.plano.get(item_edicao, 10000)))
                        )

                        novo_intervalo_meses = st.number_input(
                            "Intervalo em meses",
                            min_value=0,
                            step=1,
                            value=int(meta.get("intervalo_meses", 12))
                        )

                        nova_criticidade = st.selectbox(
                            "Criticidade",
                            ["Baixa", "Média", "Alta"],
                            index=["Baixa", "Média", "Alta"].index(meta.get("criticidade", "Média"))
                            if meta.get("criticidade", "Média") in ["Baixa", "Média", "Alta"]
                            else 1
                        )

                        nova_descricao = st.text_area(
                            "Descrição",
                            value=meta.get("descricao", "")
                        )

                        salvar_edicao = st.form_submit_button("Salvar alterações do serviço")

                        if salvar_edicao:
                            if "ManutencaoDetalhada" not in veiculo_ativo.info:
                                veiculo_ativo.info["ManutencaoDetalhada"] = {}

                            if "Revisao" not in veiculo_ativo.info:
                                veiculo_ativo.info["Revisao"] = {}

                            veiculo_ativo.info["Revisao"][item_edicao] = int(novo_intervalo_km)

                            veiculo_ativo.info["ManutencaoDetalhada"][item_edicao] = {
                                "categoria": nova_categoria.strip() if nova_categoria.strip() else "Geral",
                                "intervalo_km": int(novo_intervalo_km),
                                "intervalo_meses": int(novo_intervalo_meses),
                                "criticidade": nova_criticidade,
                                "descricao": nova_descricao.strip()
                            }

                            veiculo_ativo.plano = veiculo_ativo.info["Revisao"]

                            if item_edicao not in veiculo_ativo.ultima_revisao:
                                veiculo_ativo.ultima_revisao[item_edicao] = 0

                            salvar_estado()

                            st.success("Serviço atualizado com sucesso.")
                            st.rerun()

            # REMOVER SERVIÇO DO PLANO
            with subtab3:
                itens_remocao = sorted(list(veiculo_ativo.plano.keys()))

                if not itens_remocao:
                    st.info("Nenhum serviço disponível para remoção.")
                else:
                    item_remocao = st.selectbox(
                        "Selecione o serviço para remover do plano",
                        itens_remocao,
                        key="item_remocao_manutencao"
                    )

                    st.warning(
                        "A remoção tira o serviço do plano futuro, mas não apaga "
                        "registros antigos do histórico."
                    )

                    confirmacao = st.text_input(
                        "Digite REMOVER para confirmar",
                        key="confirmacao_remover_servico"
                    )

                    if st.button("Remover serviço do plano"):
                        if confirmacao.strip().upper() != "REMOVER":
                            st.warning("Digite REMOVER para confirmar.")
                        else:
                            if item_remocao in veiculo_ativo.info.get("Revisao", {}):
                                del veiculo_ativo.info["Revisao"][item_remocao]

                            if item_remocao in veiculo_ativo.info.get("ManutencaoDetalhada", {}):
                                del veiculo_ativo.info["ManutencaoDetalhada"][item_remocao]

                            if item_remocao in veiculo_ativo.plano:
                                del veiculo_ativo.plano[item_remocao]

                            if item_remocao in veiculo_ativo.ultima_revisao:
                                del veiculo_ativo.ultima_revisao[item_remocao]

                            salvar_estado()

                            st.success("Serviço removido do plano.")
                            st.rerun()

        # ---------------------------------------------------------------------
        # HISTÓRICO
        # ---------------------------------------------------------------------
        with tab4:
            st.subheader("Histórico de manutenções")

            if not veiculo_ativo.historico:
                st.info("Nenhuma manutenção registrada.")
            else:
                for registro in reversed(veiculo_ativo.historico):
                    with st.container(border=True):
                        st.write(registro)


# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
# =============================================================================# =============================================================================

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

    if not veiculo_ativo:
        st.warning("Selecione ou cadastre um veículo antes de calcular custos.")
    else:
        st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

        resumo = veiculo_ativo.obter_resumo_recargas()
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

        custo_ev_km = preco_kwh / consumo_ev if consumo_ev > 0 else 0
        custo_gasolina_km = preco_gasolina / consumo_gasolina if consumo_gasolina > 0 else 0

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Custo/km elétrico estimado", f"R$ {custo_ev_km:.4f}")

        with col2:
            st.metric("Custo/km gasolina", f"R$ {custo_gasolina_km:.4f}")

        with col3:
            st.metric("Gasto total em recargas", f"R$ {resumo['custo_total']:.2f}")

        if custo_ev_km < custo_gasolina_km:
            st.success("Pela estimativa, o veículo elétrico está mais econômico.")
        else:
            st.warning("Neste cenário, o veículo elétrico não está mais econômico pela estimativa.")

        st.divider()

        st.subheader("Dados reais das recargas")

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

        if resumo["custo_real_km"] is not None:
            economia_real = (custo_gasolina_km - resumo["custo_real_km"]) * resumo["km_rodados"]

            if economia_real >= 0:
                st.success(f"Economia real aproximada no período: R$ {economia_real:.2f}")
            else:
                st.warning(f"No período registrado, o elétrico ficou R$ {abs(economia_real):.2f} mais caro.")
        else:
            st.info("Atualize recargas e quilometragem para calcular custo real por km.")


# =============================================================================
# HISTÓRICO
# =============================================================================

elif pagina == "Histórico":
    st.header("Histórico")

    if not veiculo_ativo:
        st.warning("Selecione ou cadastre um veículo antes de consultar o histórico.")
    else:
        st.write(f"Veículo ativo: **{veiculo_ativo.marca} {veiculo_ativo.modelo}**")

        tab1, tab2, tab3 = st.tabs(
            [
                "Manutenções",
                "Quilometragem",
                "Recargas"
            ]
        )

        with tab1:
            st.subheader("Histórico de manutenções")

            if not veiculo_ativo.historico:
                st.info("Nenhuma manutenção registrada.")
            else:
                for registro in reversed(veiculo_ativo.historico):
                    st.write(f"- {registro}")

        with tab2:
            st.subheader("Histórico de quilometragem")

            if not veiculo_ativo.historico_km:
                st.info("Nenhuma alteração de quilometragem registrada.")
            else:
                for registro in reversed(veiculo_ativo.historico_km):
                    st.write(
                        f"- {registro.get('data', 'Sem data')}: "
                        f"{registro.get('km_anterior', 0)} km → "
                        f"{registro.get('km_nova', 0)} km"
                    )

        with tab3:
            st.subheader("Histórico de recargas")

            if not veiculo_ativo.historico_recargas:
                st.info("Nenhuma recarga registrada.")
            else:
                for i, recarga in enumerate(reversed(veiculo_ativo.historico_recargas), 1):
                    st.write(
                        f"{i}. {recarga.get('data', 'Sem data')} | "
                        f"{recarga.get('local', 'Não informado')} | "
                        f"{recarga.get('energia_kwh', 0):.2f} kWh | "
                        f"R$ {recarga.get('custo_total', 0):.2f}"
                    )
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

elif pagina == "Configurações":
    st.header("Configurações")

    tab1, tab2, tab3 = st.tabs(
        [
            "Diagnóstico",
            "Backup",
            "Importar dados"
        ]
    )

    # -------------------------------------------------------------------------
    # DIAGNÓSTICO
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Diagnóstico do sistema")

        arquivo_garagem = f"{usuario}_garagem.json"
        arquivo_config = f"{usuario}_config.json"

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Usuário atual", usuario)

        with col2:
            st.metric("Veículos cadastrados", len(garagem))

        with col3:
            if veiculo_ativo:
                st.metric("Veículo ativo", f"{veiculo_ativo.marca} {veiculo_ativo.modelo}")
            else:
                st.metric("Veículo ativo", "Nenhum")

        st.divider()

        st.write("### Arquivos do sistema")
        st.write(f"Arquivo da garagem: `{arquivo_garagem}`")
        st.write(f"Arquivo de configuração: `{arquivo_config}`")

        st.divider()

        if veiculo_ativo:
            st.write("### Dados do veículo ativo")

            col_a, col_b, col_c, col_d = st.columns(4)

            with col_a:
                st.metric("KM atual", f"{veiculo_ativo.km_atual} km")

            with col_b:
                st.metric("Autonomia", f"{veiculo_ativo.calcular_autonomia():.0f} km")

            with col_c:
                st.metric("Saúde bateria", f"{veiculo_ativo.calcular_saude_bateria():.2f}%")

            with col_d:
                st.metric("Recargas", len(veiculo_ativo.historico_recargas))

            st.write(f"Manutenções registradas: `{len(veiculo_ativo.historico)}`")
            st.write(f"Registros de quilometragem: `{len(veiculo_ativo.historico_km)}`")

            pendentes = veiculo_ativo.verificar_revisoes_pendentes()

            if pendentes:
                st.warning(f"{len(pendentes)} manutenção(ões) pendente(s):")
                for item in pendentes:
                    st.write(f"- {item}")
            else:
                st.success("Nenhuma manutenção pendente.")

            resumo = veiculo_ativo.obter_resumo_recargas()

            st.write("### Resumo das recargas do veículo ativo")
            st.write(f"Energia total registrada: `{resumo['energia_total']:.2f} kWh`")
            st.write(f"Gasto total registrado: `R$ {resumo['custo_total']:.2f}`")

            if resumo["custo_real_km"] is not None:
                st.write(f"Custo real aproximado por km: `R$ {resumo['custo_real_km']:.4f}`")
                st.write(f"Consumo real aproximado: `{resumo['consumo_real_km_kwh']:.2f} km/kWh`")
            else:
                st.info("Ainda não há dados suficientes para custo real por km.")
        else:
            st.info("Nenhum veículo ativo selecionado.")

        st.divider()

        st.write("### Resumo da garagem")

        if not garagem:
            st.info("Nenhum veículo cadastrado.")
        else:
            for i, v in enumerate(garagem, 1):
                with st.container(border=True):
                    st.write(f"**{i}. {v.marca} {v.modelo}**")
                    st.write(f"KM atual: {v.km_atual} km")
                    st.write(f"Recargas: {len(v.historico_recargas)}")
                    st.write(f"Manutenções: {len(v.historico)}")
                    st.write(f"Registros de KM: {len(v.historico_km)}")

    # -------------------------------------------------------------------------
    # BACKUP
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("Backup dos dados")

        st.write(
            "Aqui você pode salvar manualmente os dados e baixar uma cópia "
            "da garagem em formato JSON."
        )

        if st.button("Salvar dados agora"):
            salvar_estado()
            st.success("Dados salvos com sucesso.")

        st.divider()

        st.write("### Baixar backup da garagem")

        dados_backup = [v.to_dict() for v in garagem]

        backup_json = json.dumps(
            dados_backup,
            indent=4,
            ensure_ascii=False
        )

        nome_backup = f"{usuario}_garagem_backup.json"

        st.download_button(
            label="Baixar backup JSON",
            data=backup_json,
            file_name=nome_backup,
            mime="application/json"
        )

        st.info(
            "Guarde esse arquivo em local seguro. Ele contém os veículos, "
            "recargas, manutenções e histórico de quilometragem."
        )

        st.divider()

        st.write("### Backup do veículo ativo")

        if veiculo_ativo:
            dados_veiculo = json.dumps(
                veiculo_ativo.to_dict(),
                indent=4,
                ensure_ascii=False
            )

            nome_veiculo = f"{veiculo_ativo.marca}_{veiculo_ativo.modelo}_backup.json"
            nome_veiculo = nome_veiculo.replace(" ", "_")

            st.download_button(
                label="Baixar backup apenas do veículo ativo",
                data=dados_veiculo,
                file_name=nome_veiculo,
                mime="application/json"
            )
        else:
            st.info("Nenhum veículo ativo para exportar individualmente.")

    # -------------------------------------------------------------------------
    # IMPORTAR DADOS
    # -------------------------------------------------------------------------
    with tab3:
        st.subheader("Importar backup JSON")

        st.warning(
            "Use esta função com cuidado. A importação pode adicionar veículos "
            "à garagem atual ou substituir todos os dados existentes."
        )

        arquivo_importado = st.file_uploader(
            "Selecione um arquivo JSON de backup da garagem",
            type=["json"]
        )

        modo_importacao = st.radio(
            "Como deseja importar?",
            [
                "Adicionar veículos ao que já existe",
                "Substituir garagem atual"
            ]
        )

        if arquivo_importado is not None:
            try:
                conteudo = arquivo_importado.read().decode("utf-8")
                dados_importados = json.loads(conteudo)

                if not isinstance(dados_importados, list):
                    st.error("Arquivo inválido. O backup da garagem deve conter uma lista de veículos.")
                else:
                    st.success(f"Arquivo lido com sucesso. Veículos encontrados: {len(dados_importados)}")

                    st.write("### Prévia dos veículos encontrados")

                    for i, item in enumerate(dados_importados, 1):
                        marca_prev = item.get("marca", "Marca não informada")
                        modelo_prev = item.get("modelo", "Modelo não informado")
                        km_prev = item.get("km_atual", 0)

                        st.write(f"{i}. {marca_prev} {modelo_prev} - {km_prev} km")

                    if modo_importacao == "Substituir garagem atual":
                        confirmacao = st.text_input(
                            "Para substituir a garagem atual, digite SUBSTITUIR",
                            key="confirmacao_substituir_garagem"
                        )
                    else:
                        confirmacao = "ADICIONAR"

                    if st.button("Importar backup"):
                        if modo_importacao == "Substituir garagem atual" and confirmacao.strip().upper() != "SUBSTITUIR":
                            st.warning("Digite SUBSTITUIR para confirmar a substituição da garagem.")
                        else:
                            nova_garagem = []

                            for item in dados_importados:
                                try:
                                    novo_veiculo = VeiculoEV(**item)
                                    nova_garagem.append(novo_veiculo)
                                except Exception as erro:
                                    st.error(f"Erro ao importar um veículo: {erro}")

                            if nova_garagem:
                                if modo_importacao == "Substituir garagem atual":
                                    st.session_state.garagem = nova_garagem
                                    st.session_state.veiculo_ativo = nova_garagem[0]
                                else:
                                    st.session_state.garagem.extend(nova_garagem)

                                    if st.session_state.veiculo_ativo is None:
                                        st.session_state.veiculo_ativo = st.session_state.garagem[0]

                                salvar_estado()

                                st.success("Backup importado com sucesso.")
                                st.rerun()
                            else:
                                st.error("Nenhum veículo válido foi importado.")

            except json.JSONDecodeError:
                st.error("Erro ao ler o JSON. Verifique se o arquivo é um backup válido.")
            except Exception as e:
                st.error(f"Erro ao importar arquivo: {e}")