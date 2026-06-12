from ev_care_base import (
    VeiculoEV,
    REVISAO_PADRAO_GENERICA,
    MANUTENCOES_EV_DETALHADAS,
    FATOR_DEGRADACAO_PADRAO
)


def converter_veiculo_online_para_veiculo_ev(registro_online):
    """
    Converte um registro da tabela veiculos do Supabase em um objeto VeiculoEV.

    Essa função permite que o veículo salvo no Supabase seja usado pelas
    páginas antigas do app, que ainda dependem da classe VeiculoEV.
    """

    if not registro_online:
        return None

    marca = str(
        registro_online.get("marca") or "Marca não informada"
    ).strip()

    modelo = str(
        registro_online.get("modelo") or "Modelo não informado"
    ).strip()

    try:
        km_atual = int(registro_online.get("km_atual") or 0)
    except Exception:
        km_atual = 0

    try:
        bateria_kwh = float(registro_online.get("bateria_kwh") or 0)
    except Exception:
        bateria_kwh = 0.0

    try:
        consumo_km_kwh = float(registro_online.get("consumo_km_kwh") or 6.0)
    except Exception:
        consumo_km_kwh = 6.0

    dados_tecnicos = registro_online.get("dados_tecnicos") or {}

    if not isinstance(dados_tecnicos, dict):
        dados_tecnicos = {}

    info = dict(dados_tecnicos)

    if bateria_kwh > 0:
        info["Bateria"] = f"{bateria_kwh} kWh"
    else:
        info["Bateria"] = info.get("Bateria", "Não informada")

    info["Consumo"] = consumo_km_kwh
    info.setdefault("Potencia", "Não informada")
    info.setdefault("Torque", "Não informado")
    info.setdefault("Revisao", dict(REVISAO_PADRAO_GENERICA))
    info.setdefault("ManutencaoDetalhada", dict(MANUTENCOES_EV_DETALHADAS))
    info.setdefault("FatorDegradacao", FATOR_DEGRADACAO_PADRAO)

    # IMPORTANTE:
    # A classe VeiculoEV do seu projeto usa argumentos posicionais:
    # VeiculoEV(marca, modelo, km_atual, info)
    # Não use marca=, modelo=, km_atual=, info= aqui.
    veiculo = VeiculoEV(
        marca,
        modelo,
        km_atual,
        info
    )

    # Metadados online úteis para as próximas etapas da migração
    veiculo.id_online = registro_online.get("id")
    veiculo.user_id_online = registro_online.get("user_id")
    veiculo.origem_dados = "supabase"
    veiculo.veiculo_ativo_online = bool(
        registro_online.get("veiculo_ativo", False)
    )

    return veiculo


def converter_veiculo_online(registro_online):
    """
    Nome curto usado pelo app.py.

    Mantém compatibilidade com:
    from veiculo_online_adapter import converter_veiculo_online
    """
    return converter_veiculo_online_para_veiculo_ev(registro_online)