cat > plano_helpers.py <<'PY'
import streamlit as st


PLANO_FREE = "free"
PLANO_PLUS = "plus"


RECURSOS_PLUS = {
    "veiculos_ilimitados": "Veículos ilimitados",
    "relatorios_mensais": "Relatórios mensais",
    "exportacao_pdf": "Exportação em PDF",
    "exportacao_excel": "Exportação em Excel",
    "alertas_inteligentes": "Alertas inteligentes",
    "graficos_avancados": "Gráficos avançados",
    "historico_avancado": "Histórico avançado",
    "sincronizacao_dispositivos": "Sincronização entre dispositivos",
}


LIMITES_PLANO = {
    PLANO_FREE: {
        "limite_veiculos": 1,
        "relatorios_mensais": False,
        "exportacao_pdf": False,
        "exportacao_excel": False,
        "alertas_inteligentes": False,
        "graficos_avancados": False,
        "historico_avancado": False,
        "sincronizacao_dispositivos": False,
    },
    PLANO_PLUS: {
        "limite_veiculos": None,
        "relatorios_mensais": True,
        "exportacao_pdf": True,
        "exportacao_excel": True,
        "alertas_inteligentes": True,
        "graficos_avancados": True,
        "historico_avancado": True,
        "sincronizacao_dispositivos": True,
    },
}


def obter_plano_usuario():
    """
    Retorna o plano atual salvo na sessão.
    O padrão é free.
    """
    return st.session_state.get("auth_plano", PLANO_FREE) or PLANO_FREE


def usuario_eh_plus():
    """
    Retorna True se o usuário estiver no plano Plus.
    """
    return obter_plano_usuario() == PLANO_PLUS


def obter_limite_veiculos():
    """
    Retorna o limite de veículos permitido para o plano atual.
    None significa ilimitado.
    """
    plano = obter_plano_usuario()
    regras = LIMITES_PLANO.get(plano, LIMITES_PLANO[PLANO_FREE])

    return regras.get("limite_veiculos", 1)


def pode_criar_veiculo(quantidade_atual):
    """
    Verifica se o usuário pode criar mais um veículo com base no plano atual.
    """
    limite = obter_limite_veiculos()

    if limite is None:
        return True, None

    if quantidade_atual < limite:
        return True, None

    return False, (
        "O plano Free permite cadastrar 1 veículo. "
        "Veículos adicionais estarão disponíveis no EV Care Plus."
    )


def recurso_disponivel(nome_recurso):
    """
    Verifica se um recurso está disponível para o plano atual.
    """
    plano = obter_plano_usuario()
    regras = LIMITES_PLANO.get(plano, LIMITES_PLANO[PLANO_FREE])

    return bool(regras.get(nome_recurso, False))


def mensagem_recurso_plus(nome_recurso):
    """
    Retorna mensagem padronizada para recursos Plus.
    """
    nome_amigavel = RECURSOS_PLUS.get(nome_recurso, "Este recurso")

    return (
        f"{nome_amigavel} faz parte do EV Care Plus. "
        "Esse recurso será liberado em uma próxima fase."
    )


def exibir_bloqueio_plus(nome_recurso):
    """
    Mostra aviso visual de recurso Plus.
    """
    st.warning(mensagem_recurso_plus(nome_recurso))


def exibir_resumo_plano():
    """
    Exibe um resumo simples do plano atual.
    """
    plano = obter_plano_usuario()

    if plano == PLANO_PLUS:
        st.success("Plano atual: EV Care Plus")
    else:
        st.info("Plano atual: EV Care Free")

    limite = obter_limite_veiculos()

    if limite is None:
        st.write("Limite de veículos: ilimitado")
    else:
        st.write(f"Limite de veículos: {limite}")
PY