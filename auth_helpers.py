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

    if "auth_status_assinatura" not in st.session_state:
        st.session_state.auth_status_assinatura = "inactive"

    if "auth_access_token" not in st.session_state:
        st.session_state.auth_access_token = None

    if "auth_refresh_token" not in st.session_state:
        st.session_state.auth_refresh_token = None


def limpar_estado_dados_usuario():
    """
    Limpa dados carregados de usuário/veículo da sessão atual.
    Evita que uma conta veja dados carregados de outra conta.
    """
    chaves_para_limpar = [
        "veiculo_ativo",
        "veiculo_ativo_origem",
        "erro_veiculo_online_ativo",
        "garagem",
        "usuario_atual"
    ]

    for chave in chaves_para_limpar:
        if chave in st.session_state:
            del st.session_state[chave]


def salvar_usuario_na_sessao(
    user,
    session=None,
    nome=None,
    plano="free",
    status_assinatura="inactive"
):
    """
    Salva dados básicos do usuário autenticado no session_state.
    """
    limpar_estado_dados_usuario()

    st.session_state.auth_logado = True
    st.session_state.auth_user_id = user.id
    st.session_state.auth_email = user.email
    st.session_state.auth_nome = nome or user.email
    st.session_state.auth_plano = plano or "free"
    st.session_state.auth_status_assinatura = status_assinatura or "inactive"

    if session:
        st.session_state.auth_access_token = getattr(session, "access_token", None)
        st.session_state.auth_refresh_token = getattr(session, "refresh_token", None)


def sair_usuario():
    """
    Remove dados de autenticação da sessão local do Streamlit.
    """
    limpar_estado_dados_usuario()

    st.session_state.auth_logado = False
    st.session_state.auth_user_id = None
    st.session_state.auth_email = None
    st.session_state.auth_nome = None
    st.session_state.auth_plano = "free"
    st.session_state.auth_status_assinatura = "inactive"
    st.session_state.auth_access_token = None
    st.session_state.auth_refresh_token = None


def buscar_profile_usuario(cliente, user_id):
    """
    Busca o profile do usuário no Supabase.
    """
    try:
        resposta = (
            cliente
            .table("profiles")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        dados = resposta.data or []

        if not dados:
            return None, None

        return dados[0], None

    except Exception as erro:
        return None, str(erro)


def criar_ou_atualizar_profile(cliente, user, nome=None):
    """
    Cria o registro do usuário na tabela profiles se ainda não existir.
    Não sobrescreve plano/status caso o usuário já exista.
    """
    try:
        profile_existente, erro_busca = buscar_profile_usuario(cliente, user.id)

        if erro_busca:
            return False, erro_busca

        if profile_existente:
            dados_atualizacao = {
                "email": user.email,
                "nome": profile_existente.get("nome") or nome or user.email
            }

            (
                cliente
                .table("profiles")
                .update(dados_atualizacao)
                .eq("id", user.id)
                .execute()
            )

            return True, None

        dados_profile = {
            "id": user.id,
            "email": user.email,
            "nome": nome or user.email,
            "plano": "free",
            "status_assinatura": "inactive"
        }

        (
            cliente
            .table("profiles")
            .insert(dados_profile)
            .execute()
        )

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
            ok_profile, erro_profile = criar_ou_atualizar_profile(
                cliente,
                user,
                nome
            )

            if not ok_profile:
                return False, erro_profile

            profile, erro_busca = buscar_profile_usuario(cliente, user.id)

            plano = "free"
            status_assinatura = "inactive"
            nome_profile = nome or user.email

            if profile:
                plano = profile.get("plano", "free")
                status_assinatura = profile.get("status_assinatura", "inactive")
                nome_profile = profile.get("nome") or nome or user.email

            salvar_usuario_na_sessao(
                user,
                session,
                nome_profile,
                plano,
                status_assinatura
            )

            return True, "Conta criada e login realizado com sucesso."

        if user and not session:
            return True, (
                "Conta criada. Verifique seu e-mail para confirmar o cadastro "
                "antes de entrar."
            )

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

        ok_profile, erro_profile = criar_ou_atualizar_profile(cliente, user)

        if not ok_profile:
            return False, erro_profile

        profile, erro_busca = buscar_profile_usuario(cliente, user.id)

        plano = "free"
        status_assinatura = "inactive"
        nome = user.email

        if profile:
            plano = profile.get("plano", "free")
            status_assinatura = profile.get("status_assinatura", "inactive")
            nome = profile.get("nome") or user.email

        salvar_usuario_na_sessao(
            user,
            session,
            nome,
            plano,
            status_assinatura
        )

        return True, "Login realizado com sucesso."

    except Exception as erro:
        return False, str(erro)