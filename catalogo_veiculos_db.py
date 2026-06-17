from supabase_client import criar_cliente_supabase_autenticado


def listar_marcas_catalogo():
    """
    Lista marcas ativas do catálogo de veículos elétricos.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("catalogo_veiculos_ev")
            .select("marca")
            .eq("ativo", True)
            .order("marca")
            .execute()
        )

        dados = resposta.data or []
        marcas = sorted({item.get("marca") for item in dados if item.get("marca")})

        return marcas, None

    except Exception as erro:
        return [], str(erro)


def listar_modelos_catalogo(marca):
    """
    Lista modelos ativos do catálogo para uma marca.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("catalogo_veiculos_ev")
            .select("*")
            .eq("ativo", True)
            .eq("marca", marca)
            .order("modelo")
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)


def buscar_veiculo_catalogo(catalogo_id):
    """
    Busca um veículo específico do catálogo.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return None, erro

    try:
        resposta = (
            cliente
            .table("catalogo_veiculos_ev")
            .select("*")
            .eq("id", catalogo_id)
            .limit(1)
            .execute()
        )

        dados = resposta.data or []

        if not dados:
            return None, None

        return dados[0], None

    except Exception as erro:
        return None, str(erro)