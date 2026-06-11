import streamlit as st
from supabase import create_client


def criar_cliente_supabase():
    """
    Cria o cliente Supabase usando secrets configurados no Streamlit Cloud.
    """
    supabase_url = str(st.secrets.get("SUPABASE_URL", "")).strip().rstrip("/")

    # Corrige automaticamente caso a URL tenha sido copiada como endpoint REST
    if supabase_url.endswith("/rest/v1"):
        supabase_url = supabase_url.replace("/rest/v1", "")
        supabase_key = str(st.secrets.get("SUPABASE_KEY", "")).strip()

    if not supabase_url or not supabase_key:
        return None, "Secrets SUPABASE_URL ou SUPABASE_KEY não encontrados."

    if not supabase_url.startswith("https://"):
        return None, "SUPABASE_URL inválida. Ela deve começar com https://"

    if ".supabase.co" not in supabase_url:
        return None, (
            "SUPABASE_URL parece incorreta. Use a Project URL do Supabase, "
            "no formato https://xxxx.supabase.co"
        )

    if "dashboard" in supabase_url or "project" in supabase_url:
        return None, (
            "SUPABASE_URL incorreta. Não use a URL do painel/dashboard. "
            "Use a Project URL em Project Settings > API."
        )

    try:
        cliente = create_client(supabase_url, supabase_key)
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