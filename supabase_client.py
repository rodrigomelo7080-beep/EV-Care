import streamlit as st
from supabase import create_client


def criar_cliente_supabase():
    """
    Cria o cliente Supabase usando secrets configurados no Streamlit Cloud.
    """
    supabase_url = st.secrets.get("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        return None, "Secrets SUPABASE_URL ou SUPABASE_KEY não encontrados."

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