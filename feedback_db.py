import smtplib
import streamlit as st
from email.message import EmailMessage
from supabase_client import criar_cliente_supabase_autenticado


def enviar_email_feedback(
    email_origem,
    nome,
    pagina,
    tipo,
    mensagem,
    interesse_plus=False,
    nota=None
):
    """
    Envia uma cópia do feedback para o e-mail configurado nas Secrets.
    """
    try:
        smtp_host = st.secrets.get("SMTP_HOST")
        smtp_port = int(st.secrets.get("SMTP_PORT", 587))
        smtp_user = st.secrets.get("SMTP_USER")
        smtp_password = st.secrets.get("SMTP_PASSWORD")
        feedback_destino = st.secrets.get("FEEDBACK_DESTINO")

        if not all([smtp_host, smtp_user, smtp_password, feedback_destino]):
            return False, "Configurações de e-mail incompletas nas Secrets."

        assunto = f"Novo feedback EV Care - {tipo}"

        corpo = f"""
Novo feedback recebido no EV Care.

Nome: {nome}
E-mail: {email_origem}
Página relacionada: {pagina}
Tipo: {tipo}
Nota: {nota}
Interesse Plus: {'Sim' if interesse_plus else 'Não'}

Mensagem:
{mensagem}
"""

        email = EmailMessage()
        email["Subject"] = assunto
        email["From"] = smtp_user
        email["To"] = feedback_destino
        email.set_content(corpo)

        with smtplib.SMTP(smtp_host, smtp_port) as servidor:
            servidor.starttls()
            servidor.login(smtp_user, smtp_password)
            servidor.send_message(email)

        return True, None

    except Exception as erro:
        return False, str(erro)


def registrar_feedback_online(
    user_id,
    email,
    nome,
    pagina,
    tipo,
    mensagem,
    interesse_plus=False,
    nota=None
):
    """
    Registra feedback no Supabase e tenta enviar cópia por e-mail.

    Mesmo que o e-mail falhe, o feedback continua salvo no banco.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        email_enviado, erro_email = enviar_email_feedback(
            email_origem=email,
            nome=nome,
            pagina=pagina,
            tipo=tipo,
            mensagem=mensagem,
            interesse_plus=interesse_plus,
            nota=nota
        )

        dados = {
            "user_id": user_id,
            "email": email,
            "nome": nome,
            "pagina": pagina,
            "tipo": tipo,
            "mensagem": mensagem,
            "interesse_plus": bool(interesse_plus),
            "nota": nota,
            "status": "novo",
            "email_enviado": bool(email_enviado),
            "erro_email": erro_email
        }

        resposta = (
            cliente
            .table("feedbacks")
            .insert(dados)
            .execute()
        )

        if email_enviado:
            return True, "Feedback enviado com sucesso. Obrigado por ajudar a melhorar o EV Care!"

        return True, (
            "Feedback salvo com sucesso. Porém, a notificação por e-mail não foi enviada. "
            "O comentário ficou registrado no sistema."
        )

    except Exception as erro:
        return False, str(erro)


def listar_meus_feedbacks():
    """
    Lista feedbacks enviados pelo usuário logado.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("feedbacks")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)