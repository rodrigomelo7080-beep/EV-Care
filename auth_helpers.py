import streamlit as st
from supabase_client import criar_cliente_supabase


def inicializar_estado_auth():
    """
    Inicializa variáveis de autenticação no session_state.
    """

    if "auth_logado" not in st.session_state:
        st.session_state.auth_logado = False

    if "auth_user_id" not in st.session_state:
        st.session_state.auth_user_id = None

    if "auth_email" not in st.session_state:
        st.session_state.auth_email = None

    if "auth_nome" not in st.session_state:
        st.session_state.auth_nome = None

    if "auth_plano" not in st.session_state:
        st.session_state.auth_plano = "free"

    if "auth_access_token" not in st.session_state:
        st.session_state.auth_access_token = None

    if "auth_refresh_token" not in st.session_state:
        st.session_state.auth_refresh_token = None


def salvar_usuario_na_sessao(user, session=None, nome=None):
    """
    Salva dados básicos do usuário autenticado no session_state.
    """

    st.session_state.auth_logado = True
    st.session_state.auth_user_id = user.id
    st.session_state.auth_email = user.email
    st.session_state.auth_nome = nome or user.email
    st.session_state.auth_plano = "free"

    if session:
        st.session_state.auth_access_token = getattr(session, "access_token", None)
        st.session_state.auth_refresh_token = getattr(session, "refresh_token", None)


def sair_usuario():
    """
    Remove dados de autenticação da sessão local do Streamlit.
    """

    st.session_state.auth_logado = False
    st.session_state.auth_user_id = None
    st.session_state.auth_email = None
    st.session_state.auth_nome = None
    st.session_state.auth_plano = "free"
    st.session_state.auth_access_token = None
    st.session_state.auth_refresh_token = None


def criar_ou_atualizar_profile(cliente, user, nome=None):
    """
    Cria ou atualiza o registro do usuário na tabela profiles.
    """

    dados_profile = {
        "id": user.id,
        "email": user.email,
        "nome": nome or user.email,
        "plano": "free",
        "status_assinatura": "inactive"
    }

    try:
        cliente.table("profiles").upsert(dados_profile).execute()
        return True, None
    except Exception as erro:
        return False, str(erro)


def criar_conta(email, senha, nome=None):
    """
    Cria uma conta no Supabase Auth.
    """

    cliente, erro = criar_cliente_supabase()

    if erro:
        return False, erro

    try:
        resposta = cliente.auth.sign_up(
            {
                "email": email,
                "password": senha
            }
        )

        user = getattr(resposta, "user", None)
        session = getattr(resposta, "session", None)

        if user and session:
            criar_ou_atualizar_profile(cliente, user, nome)
            salvar_usuario_na_sessao(user, session, nome)
            return True, "Conta criada e login realizado com sucesso."

        if user and not session:
            return True, "Conta criada. Verifique seu e-mail para confirmar o cadastro antes de entrar."

        return False, "Não foi possível criar a conta."

    except Exception as erro:
        return False, str(erro)


def entrar_usuario(email, senha):
    """
    Realiza login com e-mail e senha.
    """

    cliente, erro = criar_cliente_supabase()

    if erro:
        return False, erro

    try:
        resposta = cliente.auth.sign_in_with_password(
            {
                "email": email,
                "password": senha
            }
        )

        user = getattr(resposta, "user", None)
        session = getattr(resposta, "session", None)

        if not user:
            return False, "Login não realizado. Verifique e-mail e senha."

        criar_ou_atualizar_profile(cliente, user)
        salvar_usuario_na_sessao(user, session)

        return True, "Login realizado com sucesso."

    except Exception as erro:
        return False, str(erro)
