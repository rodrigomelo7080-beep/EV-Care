from datetime import datetime, timezone

from supabase_client import criar_cliente_supabase_autenticado


VERSAO_TERMOS_ATUAL = "2026-06-17"
VERSAO_PRIVACIDADE_ATUAL = "2026-06-17"


def registrar_aceite_termos(user_id):
    """
    Registra o aceite dos Termos de Uso e da Política de Privacidade
    no profile do usuário.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        dados = {
            "aceitou_termos": True,
            "data_aceite_termos": datetime.now(timezone.utc).isoformat(),
            "versao_termos": VERSAO_TERMOS_ATUAL,
            "versao_privacidade": VERSAO_PRIVACIDADE_ATUAL,
        }

        resposta = (
            cliente
            .table("profiles")
            .update(dados)
            .eq("id", user_id)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)