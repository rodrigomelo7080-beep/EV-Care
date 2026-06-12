from supabase_client import criar_cliente_supabase_autenticado


def listar_historico_km_online(veiculo_id):
    """
    Lista o histórico de quilometragem online de um veículo.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("historico_km")
            .select("*")
            .eq("veiculo_id", veiculo_id)
            .order("data_registro", desc=True)
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)


def atualizar_km_veiculo_online(user_id, veiculo_id, km_anterior, km_nova):
    """
    Atualiza a KM do veículo online e registra o histórico no Supabase.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        km_anterior = int(km_anterior)
        km_nova = int(km_nova)

        if km_nova < km_anterior:
            return False, "A nova KM não pode ser menor que a KM atual."

        if km_nova == km_anterior:
            return False, "A nova KM é igual à KM atual. Nenhuma alteração foi feita."

        # Atualiza KM atual do veículo
        cliente.table("veiculos").update(
            {
                "km_atual": km_nova
            }
        ).eq(
            "id",
            veiculo_id
        ).execute()

        # Registra histórico
        cliente.table("historico_km").insert(
            {
                "user_id": user_id,
                "veiculo_id": veiculo_id,
                "km_anterior": km_anterior,
                "km_nova": km_nova
            }
        ).execute()

        return True, "Quilometragem online atualizada com sucesso."

    except Exception as erro:
        return False, str(erro)