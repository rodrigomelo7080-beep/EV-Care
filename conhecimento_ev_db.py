import streamlit as st
from supabase import create_client


def criar_cliente_conhecimento_ev():
    """
    Cria cliente Supabase para leitura pública dos conteúdos educativos.
    """
    try:
        supabase_url = (
            st.secrets.get("SUPABASE_URL")
            or st.secrets.get("supabase_url")
        )

        supabase_key = (
            st.secrets.get("SUPABASE_ANON_KEY")
            or st.secrets.get("SUPABASE_KEY")
            or st.secrets.get("supabase_key")
        )

        if not supabase_url or not supabase_key:
            return None, "Secrets do Supabase não encontradas."

        return create_client(supabase_url, supabase_key), None

    except Exception as erro:
        return None, str(erro)


def listar_conteudos_conhecimento_ev():
    """
    Lista conteúdos ativos da aba Conhecimento EV.
    """
    cliente, erro = criar_cliente_conhecimento_ev()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("conhecimento_ev")
            .select("*")
            .eq("ativo", True)
            .order("ordem_categoria")
            .order("ordem")
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)