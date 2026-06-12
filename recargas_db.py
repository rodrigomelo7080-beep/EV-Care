from datetime import datetime, timezone
from supabase_client import criar_cliente_supabase_autenticado


def _float_seguro(valor, padrao=0.0):
    """
    Converte valores numéricos vindos do Supabase para float com segurança.
    """
    try:
        if valor is None:
            return padrao
        return float(valor)
    except Exception:
        return padrao


def _int_seguro(valor, padrao=0):
    """
    Converte valores numéricos vindos do Supabase para int com segurança.
    """
    try:
        if valor is None:
            return padrao
        return int(valor)
    except Exception:
        return padrao


def listar_recargas_online(veiculo_id):
    """
    Lista as recargas online de um veículo.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("recargas")
            .select("*")
            .eq("veiculo_id", veiculo_id)
            .order("data_recarga", desc=True)
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)


def listar_recargas_online_ordem_crescente(veiculo_id):
    """
    Lista as recargas online em ordem crescente.
    Útil para cálculos de consumo e custo real.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("recargas")
            .select("*")
            .eq("veiculo_id", veiculo_id)
            .order("data_recarga", desc=False)
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)


def registrar_recarga_online(
    user_id,
    veiculo_id,
    km_atual,
    bateria_inicial,
    bateria_final,
    energia_kwh,
    preco_kwh,
    local,
    tipo,
    observacao=None
):
    """
    Registra uma nova recarga online no Supabase.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        energia_kwh = _float_seguro(energia_kwh)
        preco_kwh = _float_seguro(preco_kwh)
        custo_total = energia_kwh * preco_kwh

        dados = {
            "user_id": user_id,
            "veiculo_id": veiculo_id,
            "km_atual": _int_seguro(km_atual),
            "bateria_inicial": _float_seguro(bateria_inicial),
            "bateria_final": _float_seguro(bateria_final),
            "energia_kwh": energia_kwh,
            "preco_kwh": preco_kwh,
            "custo_total": custo_total,
            "local": local or "",
            "tipo": tipo or "Outro",
            "observacao": observacao or ""
        }

        resposta = (
            cliente
            .table("recargas")
            .insert(dados)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def editar_recarga_online(
    recarga_id,
    bateria_inicial,
    bateria_final,
    energia_kwh,
    preco_kwh,
    local,
    tipo,
    observacao=None
):
    """
    Edita uma recarga online existente.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        energia_kwh = _float_seguro(energia_kwh)
        preco_kwh = _float_seguro(preco_kwh)
        custo_total = energia_kwh * preco_kwh

        dados = {
            "bateria_inicial": _float_seguro(bateria_inicial),
            "bateria_final": _float_seguro(bateria_final),
            "energia_kwh": energia_kwh,
            "preco_kwh": preco_kwh,
            "custo_total": custo_total,
            "local": local or "",
            "tipo": tipo or "Outro",
            "observacao": observacao or "",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        resposta = (
            cliente
            .table("recargas")
            .update(dados)
            .eq("id", recarga_id)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def excluir_recarga_online(recarga_id):
    """
    Exclui uma recarga online.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        resposta = (
            cliente
            .table("recargas")
            .delete()
            .eq("id", recarga_id)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def obter_resumo_recargas_online(veiculo_id, km_atual_veiculo=None):
    """
    Calcula resumo das recargas online de um veículo.

    Retorna estrutura parecida com o resumo local usado pelo app.
    """
    recargas, erro = listar_recargas_online_ordem_crescente(veiculo_id)

    if erro:
        return None, erro

    total_recargas = len(recargas)

    energia_total = sum(
        _float_seguro(r.get("energia_kwh"))
        for r in recargas
    )

    custo_total = sum(
        _float_seguro(r.get("custo_total"))
        for r in recargas
    )

    custo_medio_recarga = (
        custo_total / total_recargas
        if total_recargas > 0
        else 0
    )

    preco_medio_kwh = (
        custo_total / energia_total
        if energia_total > 0
        else 0
    )

    custo_real_km = None
    consumo_real_km_kwh = None
    km_rodados = 0

    if recargas and km_atual_veiculo is not None:
        primeira_km = _int_seguro(recargas[0].get("km_atual"))
        km_atual_veiculo = _int_seguro(km_atual_veiculo)

        if km_atual_veiculo > primeira_km:
            km_rodados = km_atual_veiculo - primeira_km

            if km_rodados > 0:
                custo_real_km = custo_total / km_rodados

            if energia_total > 0:
                consumo_real_km_kwh = km_rodados / energia_total

    resumo = {
        "total_recargas": total_recargas,
        "energia_total": energia_total,
        "custo_total": custo_total,
        "custo_medio_recarga": custo_medio_recarga,
        "preco_medio_kwh": preco_medio_kwh,
        "custo_real_km": custo_real_km,
        "consumo_real_km_kwh": consumo_real_km_kwh,
        "km_rodados": km_rodados
    }

    return resumo, None