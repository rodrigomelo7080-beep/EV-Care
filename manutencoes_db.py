from datetime import datetime, timezone
from supabase_client import criar_cliente_supabase_autenticado
from ev_care_base import MANUTENCOES_EV_DETALHADAS


def _int_seguro(valor, padrao=0):
    try:
        if valor is None:
            return padrao
        return int(valor)
    except Exception:
        return padrao


def listar_servicos_manutencao_online(veiculo_id, apenas_ativos=True):
    """
    Lista os serviços de manutenção online de um veículo.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        query = (
            cliente
            .table("servicos_manutencao")
            .select("*")
            .eq("veiculo_id", veiculo_id)
        )

        if apenas_ativos:
            query = query.eq("ativo", True)

        resposta = (
            query
            .order("created_at", desc=False)
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)


def criar_servico_manutencao_online(
    user_id,
    veiculo_id,
    nome,
    categoria,
    intervalo_km,
    intervalo_meses,
    criticidade,
    descricao,
    ultima_km=0
):
    """
    Cria um serviço de manutenção online.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        dados = {
            "user_id": user_id,
            "veiculo_id": veiculo_id,
            "nome": nome,
            "categoria": categoria,
            "intervalo_km": _int_seguro(intervalo_km, 10000),
            "intervalo_meses": _int_seguro(intervalo_meses, 0),
            "criticidade": criticidade or "Média",
            "descricao": descricao or "",
            "ativo": True,
            "ultima_km": _int_seguro(ultima_km, 0),
            "ultima_data": None
        }

        resposta = (
            cliente
            .table("servicos_manutencao")
            .insert(dados)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def criar_plano_padrao_manutencao_online(user_id, veiculo_id, km_atual=0):
    """
    Cria o plano padrão de manutenção EV no Supabase para um veículo.

    Só deve ser chamado quando o veículo ainda não tiver serviços cadastrados.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        servicos_existentes, erro_lista = listar_servicos_manutencao_online(
            veiculo_id,
            apenas_ativos=False
        )

        if erro_lista:
            return False, erro_lista

        if servicos_existentes:
            return True, "Plano de manutenção online já existe."

        dados_para_inserir = []

        for nome, dados in MANUTENCOES_EV_DETALHADAS.items():
            dados_para_inserir.append(
                {
                    "user_id": user_id,
                    "veiculo_id": veiculo_id,
                    "nome": nome,
                    "categoria": dados.get("categoria", "Geral"),
                    "intervalo_km": _int_seguro(dados.get("intervalo_km"), 10000),
                    "intervalo_meses": _int_seguro(dados.get("intervalo_meses"), 0),
                    "criticidade": dados.get("criticidade", "Média"),
                    "descricao": dados.get("descricao", ""),
                    "ativo": True,
                    "ultima_km": 0,
                    "ultima_data": None
                }
            )

        if not dados_para_inserir:
            return False, "Nenhum serviço padrão encontrado para criar."

        resposta = (
            cliente
            .table("servicos_manutencao")
            .insert(dados_para_inserir)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def editar_servico_manutencao_online(
    servico_id,
    nome,
    categoria,
    intervalo_km,
    intervalo_meses,
    criticidade,
    descricao
):
    """
    Edita um serviço de manutenção online.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        dados = {
            "nome": nome,
            "categoria": categoria,
            "intervalo_km": _int_seguro(intervalo_km, 10000),
            "intervalo_meses": _int_seguro(intervalo_meses, 0),
            "criticidade": criticidade or "Média",
            "descricao": descricao or "",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        resposta = (
            cliente
            .table("servicos_manutencao")
            .update(dados)
            .eq("id", servico_id)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def desativar_servico_manutencao_online(servico_id):
    """
    Desativa um serviço de manutenção online sem apagar histórico.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        resposta = (
            cliente
            .table("servicos_manutencao")
            .update(
                {
                    "ativo": False,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            )
            .eq("id", servico_id)
            .execute()
        )

        return True, resposta.data

    except Exception as erro:
        return False, str(erro)


def registrar_manutencao_online(
    user_id,
    veiculo_id,
    servico_id,
    nome_servico,
    km_realizada,
    observacao=None
):
    """
    Registra uma manutenção realizada e atualiza ultima_km / ultima_data do serviço.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return False, erro

    try:
        km_realizada = _int_seguro(km_realizada, 0)

        dados_manutencao = {
            "user_id": user_id,
            "veiculo_id": veiculo_id,
            "servico_id": servico_id,
            "nome_servico": nome_servico,
            "km_realizada": km_realizada,
            "observacao": observacao or ""
        }

        resposta_manutencao = (
            cliente
            .table("manutencoes")
            .insert(dados_manutencao)
            .execute()
        )

        agora = datetime.now(timezone.utc).isoformat()

        cliente.table("servicos_manutencao").update(
            {
                "ultima_km": km_realizada,
                "ultima_data": agora,
                "updated_at": agora
            }
        ).eq(
            "id",
            servico_id
        ).execute()

        return True, resposta_manutencao.data

    except Exception as erro:
        return False, str(erro)


def listar_manutencoes_online(veiculo_id):
    """
    Lista manutenções realizadas online de um veículo.
    """
    cliente, erro = criar_cliente_supabase_autenticado()

    if erro:
        return [], erro

    try:
        resposta = (
            cliente
            .table("manutencoes")
            .select("*")
            .eq("veiculo_id", veiculo_id)
            .order("data_realizada", desc=True)
            .execute()
        )

        return resposta.data or [], None

    except Exception as erro:
        return [], str(erro)


def calcular_status_servico_manutencao_online(servico, km_atual):
    """
    Calcula status de um serviço online com base em ultima_km + intervalo_km.

    Status:
    - Vencido
    - Próximo
    - Em dia
    """
    intervalo_km = _int_seguro(servico.get("intervalo_km"), 10000)
    ultima_km = _int_seguro(servico.get("ultima_km"), 0)
    km_atual = _int_seguro(km_atual, 0)

    proxima_km = ultima_km + intervalo_km
    km_restante = proxima_km - km_atual

    vencido_por_km = km_restante <= 0

    limite_proximo_km = max(int(intervalo_km * 0.2), 100)
    proximo_por_km = 0 < km_restante <= limite_proximo_km

    if vencido_por_km:
        status = "Vencido"
    elif proximo_por_km:
        status = "Próximo"
    else:
        status = "Em dia"

    return {
        "status": status,
        "categoria": servico.get("categoria", "Geral"),
        "criticidade": servico.get("criticidade", "Média"),
        "descricao": servico.get("descricao", ""),
        "intervalo_km": intervalo_km,
        "intervalo_meses": _int_seguro(servico.get("intervalo_meses"), 0),
        "ultima_km": ultima_km,
        "proxima_km": proxima_km,
        "km_restante": km_restante,
        "limite_proximo_km": limite_proximo_km
    }


def obter_resumo_manutencoes_online(veiculo_id, km_atual):
    """
    Retorna lista de serviços com status calculado e contadores.
    """
    servicos, erro = listar_servicos_manutencao_online(veiculo_id)

    if erro:
        return None, erro

    itens_status = []

    for servico in servicos:
        status = calcular_status_servico_manutencao_online(
            servico,
            km_atual
        )
        itens_status.append((servico, status))

    vencidos = [
        item for item in itens_status
        if item[1]["status"] == "Vencido"
    ]

    proximos = [
        item for item in itens_status
        if item[1]["status"] == "Próximo"
    ]

    em_dia = [
        item for item in itens_status
        if item[1]["status"] == "Em dia"
    ]

    ordem_status = {
        "Vencido": 0,
        "Próximo": 1,
        "Em dia": 2
    }

    itens_status.sort(
        key=lambda item: (
            ordem_status.get(item[1]["status"], 3),
            item[1]["km_restante"]
        )
    )

    resumo = {
        "servicos": servicos,
        "itens_status": itens_status,
        "vencidos": vencidos,
        "proximos": proximos,
        "em_dia": em_dia,
        "total_servicos": len(servicos)
    }

    return resumo, None
