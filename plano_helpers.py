import streamlit as st


# =============================================================================
# CONSTANTES DOS PLANOS
# =============================================================================

PLANO_FREE = "free"
PLANO_PLUS = "plus"

STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"


# =============================================================================
# RECURSOS PLUS
# =============================================================================

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


# =============================================================================
# LIMITES E PERMISSÕES POR PLANO
# =============================================================================

LIMITES_PLANO = {
    PLANO_FREE: {
        "limite_veiculos": 1,
        "veiculos_ilimitados": False,
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
        "veiculos_ilimitados": True,
        "relatorios_mensais": True,
        "exportacao_pdf": True,
        "exportacao_excel": True,
        "alertas_inteligentes": True,
        "graficos_avancados": True,
        "historico_avancado": True,
        "sincronizacao_dispositivos": True,
    },
}


# =============================================================================
# FUNÇÕES DE PLANO
# =============================================================================

def normalizar_plano(plano):
    """
    Normaliza o nome do plano para evitar erros de maiúsculas, espaços ou valores vazios.
    """
    if not plano:
        return PLANO_FREE

    plano_normalizado = str(plano).strip().lower()

    if plano_normalizado == PLANO_PLUS:
        return PLANO_PLUS

    return PLANO_FREE


def obter_plano_usuario():
    """
    Retorna o plano atual salvo na sessão.
    O padrão é free.
    """
    plano = st.session_state.get("auth_plano", PLANO_FREE)
    return normalizar_plano(plano)


def obter_status_assinatura():
    """
    Retorna o status atual da assinatura salvo na sessão.
    """
    status = st.session_state.get("auth_status_assinatura", STATUS_INACTIVE)

    if not status:
        return STATUS_INACTIVE

    return str(status).strip().lower()


def usuario_eh_free():
    """
    Retorna True se o usuário estiver no plano Free.
    """
    return obter_plano_usuario() == PLANO_FREE


def usuario_eh_plus():
    """
    Retorna True se o usuário estiver no plano Plus.
    """
    return obter_plano_usuario() == PLANO_PLUS


def usuario_plus_ativo():
    """
    Retorna True se o usuário estiver no plano Plus com assinatura ativa.
    """
    return (
        obter_plano_usuario() == PLANO_PLUS
        and obter_status_assinatura() == STATUS_ACTIVE
    )


def obter_nome_plano_formatado():
    """
    Retorna o nome comercial do plano atual.
    """
    if usuario_eh_plus():
        return "EV Care Plus"

    return "EV Care Free"


def obter_limite_veiculos():
    """
    Retorna o limite de veículos permitido para o plano atual.
    None significa ilimitado.

    O plano Plus só libera veículos ilimitados quando a assinatura está ativa.
    """
    if usuario_plus_ativo():
        return LIMITES_PLANO[PLANO_PLUS].get("limite_veiculos")

    return LIMITES_PLANO[PLANO_FREE].get("limite_veiculos", 1)


def pode_criar_veiculo(quantidade_atual):
    """
    Verifica se o usuário pode criar mais um veículo com base no plano atual.
    """
    limite = obter_limite_veiculos()

    if limite is None:
        return True, None

    try:
        quantidade_atual = int(quantidade_atual)
    except Exception:
        quantidade_atual = 0

    if quantidade_atual < limite:
        return True, None

    return False, (
        "O plano Free permite cadastrar 1 veículo. "
        "Veículos adicionais estarão disponíveis no EV Care Plus."
    )


def recurso_disponivel(nome_recurso):
    """
    Verifica se um recurso está disponível para o plano atual.

    Recursos Plus só ficam disponíveis se:
    - plano = plus
    - status_assinatura = active
    """
    if not usuario_plus_ativo():
        return False

    regras = LIMITES_PLANO.get(PLANO_PLUS, {})

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
    plano_formatado = obter_nome_plano_formatado()
    status = obter_status_assinatura()
    limite = obter_limite_veiculos()

    if usuario_eh_plus():
        st.success(f"Plano atual: {plano_formatado}")
    else:
        st.info(f"Plano atual: {plano_formatado}")

    st.write(f"Status da assinatura: {status}")

    if limite is None:
        st.write("Limite de veículos: ilimitado")
    else:
        st.write(f"Limite de veículos: {limite}")


def obter_recursos_plus():
    """
    Retorna o dicionário de recursos Plus planejados.
    """
    return RECURSOS_PLUS


def listar_recursos_bloqueados_para_usuario():
    """
    Retorna lista de recursos Plus que não estão disponíveis para o plano atual.
    """
    bloqueados = []

    for chave_recurso, nome_recurso in RECURSOS_PLUS.items():
        if not recurso_disponivel(chave_recurso):
            bloqueados.append(
                {
                    "codigo": chave_recurso,
                    "nome": nome_recurso,
                    "mensagem": mensagem_recurso_plus(chave_recurso)
                }
            )

    return bloqueados