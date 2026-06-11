from supabase_client import criar_cliente_supabase_autenticado


def listar_veiculos_usuario():
    """
    Lista os veículos do usuário logado.
    A segurança dos dados é reforçada pelo RLS no Supabase.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("veiculos")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)


def contar_veiculos_usuario():
    """
    Conta quantos veículos o usuário logado possui.
    """
    veiculos, erro = listar_veiculos_usuario()

    if erro:
        return 0, erro

    return len(veiculos), None


def criar_veiculo_online(
    user_id,
    marca,
    modelo,
    km_atual,
    bateria_kwh,
    consumo_km_kwh,
    dados_tecnicos=None,
    veiculo_ativo=False
):
    """
    Cria um veículo no Supabase para o usuário logado.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    dados = {
        "user_id": user_id,
        "marca": marca,
        "modelo": modelo,
        "km_atual": int(km_atual),
        "bateria_kwh": float(bateria_kwh) if bateria_kwh is not None else None,
        "consumo_km_kwh": float(consumo_km_kwh) if consumo_km_kwh is not None else None,
        "dados_tecnicos": dados_tecnicos or {},
        "veiculo_ativo": bool(veiculo_ativo)
    }

    try:
        resposta = (
            cliente
            .table("veiculos")
            .insert(dados)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def atualizar_veiculo_online(
    veiculo_id,
    marca,
    modelo,
    km_atual,
    bateria_kwh,
    consumo_km_kwh,
    dados_tecnicos=None
):
    """
    Atualiza dados básicos de um veículo.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    dados = {
        "marca": marca,
        "modelo": modelo,
        "km_atual": int(km_atual),
        "bateria_kwh": float(bateria_kwh) if bateria_kwh is not None else None,
        "consumo_km_kwh": float(consumo_km_kwh) if consumo_km_kwh is not None else None,
        "dados_tecnicos": dados_tecnicos or {}
    }

    try:
        resposta = (
            cliente
            .table("veiculos")
            .update(dados)
            .eq("id", veiculo_id)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def excluir_veiculo_online(veiculo_id):
    """
    Exclui um veículo do usuário logado.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        resposta = (
            cliente
            .table("veiculos")
            .delete()
            .eq("id", veiculo_id)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def limpar_veiculo_ativo_online():
    """
    Marca todos os veículos do usuário como não ativos.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        resposta = (
            cliente
            .table("veiculos")
            .update({"veiculo_ativo": False})
            .eq("veiculo_ativo", True)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def definir_veiculo_ativo_online(veiculo_id):
    """
    Define um veículo como ativo.
    Primeiro limpa o veículo ativo anterior.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    ok_limpeza, erro_limpeza = limpar_veiculo_ativo_online()

    if not ok_limpeza:
        return False, erro_limpeza

    try:
        resposta = (
            cliente
            .table("veiculos")
            .update({"veiculo_ativo": True})
            .eq("id", veiculo_id)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def obter_veiculo_ativo_online():
    """
    Busca o veículo ativo do usuário logado.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return None, erro

    try:
        resposta = (
            cliente
            .table("veiculos")
            .select("*")
            .eq("veiculo_ativo", True)
            .limit(1)
            .execute()
        )

        dados = resposta.data or []

        if not dados:
            return None, None

        return dados[0], None

    except Exception as erro:
        return None, str(erro)