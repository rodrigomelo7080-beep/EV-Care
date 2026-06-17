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


def listar_modelos_por_marca_catalogo(marca):
    """
    Lista modelos únicos ativos de uma marca no catálogo.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("catalogo_veiculos_ev")
            .select("modelo")
            .eq("ativo", True)
            .eq("marca", marca)
            .order("modelo")
            .execute()
        )

        dados = resposta.data or []
        modelos = sorted({item.get("modelo") for item in dados if item.get("modelo")})

        return modelos, None

    except Exception as erro:
        return [], str(erro)


def listar_versoes_catalogo(marca, modelo):
    """
    Lista versões ativas de um modelo específico no catálogo.
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
            .eq("modelo", modelo)
            .order("ano_modelo", desc=True)
            .order("versao")
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)


def listar_modelos_catalogo(marca):
    """
    Mantido por compatibilidade.
    Lista todas as linhas ativas do catálogo para uma marca.
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
    Busca uma versão específica do catálogo.
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