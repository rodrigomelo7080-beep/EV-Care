import streamlit as st
from supabase import create_client


def obter_config_supabase():
    """
    Lê e valida as configurações do Supabase a partir dos secrets do Streamlit.
    """

    supabase_url = str(st.secrets.get("SUPABASE_URL", "")).strip().rstrip("/")
    supabase_key = str(st.secrets.get("SUPABASE_KEY", "")).strip()

    # Corrige automaticamente caso a URL tenha sido copiada como endpoint REST
    if supabase_url.endswith("/rest/v1"):
        supabase_url = supabase_url.replace("/rest/v1", "")

    if not supabase_url or not supabase_key:
        return None, None, "Secrets SUPABASE_URL ou SUPABASE_KEY não encontrados."

    if not supabase_url.startswith("https://"):
        return None, None, "SUPABASE_URL inválida. Ela deve começar com https://"

    if ".supabase.co" not in supabase_url:
        return None, None, (
            "SUPABASE_URL parece incorreta. Use a Project URL do Supabase, "
            "no formato https://xxxx.supabase.co"
        )

    if "dashboard" in supabase_url or "project" in supabase_url:
        return None, None, (
            "SUPABASE_URL incorreta. Não use a URL do painel/dashboard. "
            "Use a Project URL em Project Settings > API."
        )

    return supabase_url, supabase_key, None


def criar_cliente_supabase():
    """
    Cria o cliente Supabase público usando secrets configurados no Streamlit Cloud.
    Este cliente serve para login, criação de conta e testes básicos.
    """

    supabase_url, supabase_key, erro = obter_config_supabase()

    if erro:
        return None, erro

    try:
        cliente = create_client(supabase_url, supabase_key)
        return cliente, None
    except Exception as erro:
        return None, str(erro)


def criar_cliente_supabase_autenticado():
    """
    Cria um cliente Supabase com a sessão do usuário logado.

    Esse cliente será usado para acessar tabelas protegidas por RLS,
    como veiculos, recargas, manutenções e historico_km.
    """

    cliente, erro = criar_cliente_supabase()

    if erro:
        return None, erro

    access_token = st.session_state.get("auth_access_token")
    refresh_token = st.session_state.get("auth_refresh_token")

    if not access_token or not refresh_token:
        return None, "Usuário não autenticado ou sessão Supabase ausente."

    try:
        cliente.auth.set_session(access_token, refresh_token)
        return cliente, None
    except Exception as erro:
        return None, str(erro)


def testar_conexao_supabase():
    """
    Testa se o cliente Supabase pode ser criado.
    Nesta etapa, não consulta tabelas ainda.
    """

    cliente, erro = criar_cliente_supabase()

    if erro:
        return {
            "ok": False,
            "mensagem": erro
        }

    if cliente is None:
        return {
            "ok": False,
            "mensagem": "Cliente Supabase não foi criado."
        }

    return {
        "ok": True,
        "mensagem": "Cliente Supabase criado com sucesso."
    }


def testar_cliente_autenticado():
    """
    Testa se existe uma sessão autenticada disponível para acessar dados protegidos.
    """

    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return {
            "ok": False,
            "mensagem": erro
        }

    return {
        "ok": True,
        "mensagem": "Cliente Supabase autenticado criado com sucesso."
    }