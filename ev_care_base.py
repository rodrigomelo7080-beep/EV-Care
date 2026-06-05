# -*- coding: utf-8 -*-

import os
import json
import csv
from datetime import datetime

# =============================================================================
# CONFIGURAÇÕES DE INTERFACE
# =============================================================================
class Cores:
    VERMELHO = ''
    VERDE = ''
    AMARELO = ''
    AZUL = ''
    CIANO = ''
    MAGENTA = ''
    RESET = ''
    NEGRITO = ''
    FUNDO_AZUL = ''
    TEXTO_PRETO = ''

# =============================================================================
# CATÁLOGO DE VEÍCULOS
# Consumo tratado como km/kWh
# =============================================================================
DADOS_VEICULOS = {
    "BYD": {
        "DOLPHIN MINI (38kWh)": {"Bateria": "38.0 kWh", "Potencia": "75 cv", "Torque": "135 Nm", "Consumo": 8.0, "Revisao": {"Checkup Geral": 20000, "Filtro de Ar": 20000, "Fluido de Freio": 40000}, "FatorDegradacao": 35000},
        "DOLPHIN EV": {"Bateria": "44.9 kWh", "Potencia": "95 cv", "Torque": "180 Nm", "Consumo": 6.8, "Revisao": {"Revisão Geral": 20000, "Filtro de Cabine": 20000, "Fluido de Freio": 40000}, "FatorDegradacao": 35000},
        "DOLPHIN PLUS": {"Bateria": "60.5 kWh", "Potencia": "204 cv", "Torque": "310 Nm", "Consumo": 6.2, "Revisao": {"Revisão Geral": 20000, "Filtro de Cabine": 20000, "Fluido de Freio": 40000}, "FatorDegradacao": 35000},
        "SEAL": {"Bateria": "82.6 kWh", "Potencia": "531 cv", "Torque": "670 Nm", "Consumo": 5.5, "Revisao": {"Óleo do Redutor": 150000, "Revisão Geral": 20000, "Líquido Arrefecimento": 100000}, "FatorDegradacao": 40000},
        "YUAN PLUS": {"Bateria": "60.5 kWh", "Potencia": "204 cv", "Torque": "310 Nm", "Consumo": 6.1, "Revisao": {"Revisão Geral": 20000, "Filtro de Cabine": 20000, "Fluido de Freio": 40000}, "FatorDegradacao": 35000},
        "TAN EV": {"Bateria": "86.4 kWh", "Potencia": "517 cv", "Torque": "680 Nm", "Consumo": 4.8, "Revisao": {"Revisão Geral": 20000, "Pastilhas de Freio": 40000, "Líquido Arrefecimento": 100000}, "FatorDegradacao": 40000},
        "HAN EV": {"Bateria": "76.9 kWh", "Potencia": "494 cv", "Torque": "680 Nm", "Consumo": 5.0, "Revisao": {"Revisão Geral": 20000, "Checkup de Bateria": 40000}, "FatorDegradacao": 38000}
    },
    "GWM": {
        "ORA 03 SKIN": {"Bateria": "48.0 kWh", "Potencia": "171 cv", "Torque": "250 Nm", "Consumo": 6.5, "Revisao": {"Rodízio de Pneus": 10000, "Revisão Periódica": 15000, "Filtro de Ar": 30000}, "FatorDegradacao": 35000},
        "ORA 03 GT": {"Bateria": "63.0 kWh", "Potencia": "171 cv", "Torque": "250 Nm", "Consumo": 6.3, "Revisao": {"Rodízio de Pneus": 10000, "Revisão Periódica": 15000, "Fluido de Freio": 30000}, "FatorDegradacao": 35000}
    },
    "VOLVO": {
        "EX30": {"Bateria": "69.0 kWh", "Potencia": "272 cv", "Torque": "343 Nm", "Consumo": 5.3, "Revisao": {"Inspeção Geral": 30000, "Filtro de Cabine": 30000, "Limpadores": 15000}, "FatorDegradacao": 38000},
        "XC40 RECHARGE": {"Bateria": "78.0 kWh", "Potencia": "408 cv", "Torque": "660 Nm", "Consumo": 4.6, "Revisao": {"Filtro de Ar": 30000, "Fluido de Freio": 60000, "Revisão de Sistemas": 30000}, "FatorDegradacao": 40000},
        "C40 RECHARGE": {"Bateria": "78.0 kWh", "Potencia": "408 cv", "Torque": "660 Nm", "Consumo": 4.7, "Revisao": {"Filtro de Ar": 30000, "Checkup de Sistemas": 30000, "Fluido de Freio": 60000}, "FatorDegradacao": 40000}
    },
    "RENAULT": {
        "KWID E-TECH": {"Bateria": "26.8 kWh", "Potencia": "65 cv", "Torque": "113 Nm", "Consumo": 7.6, "Revisao": {"Revisão Anual": 10000, "Filtro de Ar": 20000, "Bateria 12V": 40000}, "FatorDegradacao": 30000},
        "MEGANE E-TECH": {"Bateria": "60.0 kWh", "Potencia": "220 cv", "Torque": "300 Nm", "Consumo": 6.0, "Revisao": {"Revisão Geral": 20000, "Filtro de Ar": 20000, "Líquido de Freio": 40000}, "FatorDegradacao": 35000}
    },
    "BMW": {
        "i3": {"Bateria": "42.2 kWh", "Potencia": "170 cv", "Torque": "250 Nm", "Consumo": 6.4, "Revisao": {"Microfiltro": 20000, "Fluido de Freio": 40000}, "FatorDegradacao": 35000},
        "iX1": {"Bateria": "66.5 kWh", "Potencia": "313 cv", "Torque": "494 Nm", "Consumo": 5.4, "Revisao": {"Checkup Geral": 25000}, "FatorDegradacao": 40000},
        "iX3": {"Bateria": "80.0 kWh", "Potencia": "286 cv", "Torque": "400 Nm", "Consumo": 5.5, "Revisao": {"Serviço Standard": 25000}, "FatorDegradacao": 40000},
        "i4": {"Bateria": "83.9 kWh", "Potencia": "340 cv", "Torque": "430 Nm", "Consumo": 5.2, "Revisao": {"Inspeção BMW": 20000}, "FatorDegradacao": 38000}
    },
    "NISSAN": {
        "LEAF": {"Bateria": "40.0 kWh", "Potencia": "150 cv", "Torque": "320 Nm", "Consumo": 6.2, "Revisao": {"Inspeção de Bateria": 10000, "Filtro de Ar": 15000, "Fluido de Freio": 30000}, "FatorDegradacao": 32000}
    },
    "CHEVROLET": {
        "BOLT EV": {"Bateria": "66.0 kWh", "Potencia": "203 cv", "Torque": "360 Nm", "Consumo": 5.9, "Revisao": {"Filtro de Cabine": 36000, "Fluido de Freio": 72000}, "FatorDegradacao": 38000},
        "BOLT EUV": {"Bateria": "66.0 kWh", "Potencia": "203 cv", "Torque": "360 Nm", "Consumo": 5.7, "Revisao": {"Filtro de Cabine": 36000, "Fluido de Freio": 72000}, "FatorDegradacao": 38000}
    },
    "AUDI": {
        "E-TRON": {"Bateria": "95.0 kWh", "Potencia": "408 cv", "Torque": "664 Nm", "Consumo": 4.2, "Revisao": {"Serviço Inspeção": 30000, "Fluido Freio": 60000}, "FatorDegradacao": 42000}
    },
    "TESLA": {
        "MODEL 3": {"Bateria": "75.0 kWh", "Potencia": "450 cv", "Torque": "639 Nm", "Consumo": 6.5, "Revisao": {"Filtro Cabine": 32000, "Fluido Freio": 64000}, "FatorDegradacao": 45000}
    }
}

# =============================================================================
# PLANO GERAL DE MANUTENÇÃO PARA VEÍCULOS ELÉTRICOS
# Intervalos genéricos baseados em práticas comuns de manutenção EV.
# O app permite edição manual por veículo.
# =============================================================================

MANUTENCOES_EV_DETALHADAS = {
    "Rodízio de Pneus": {
        "categoria": "Pneus e Rodagem",
        "intervalo_km": 10000,
        "intervalo_meses": 12,
        "criticidade": "Alta",
        "descricao": "Ajuda a manter desgaste uniforme, autonomia e segurança."
    },
    "Inspeção de Pneus e Calibragem": {
        "categoria": "Pneus e Rodagem",
        "intervalo_km": 5000,
        "intervalo_meses": 1,
        "criticidade": "Alta",
        "descricao": "Verificar pressão, desgaste irregular, bolhas, cortes e profundidade dos sulcos."
    },
    "Alinhamento e Balanceamento": {
        "categoria": "Pneus e Rodagem",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Média",
        "descricao": "Recomendado quando houver desgaste irregular, vibração ou direção puxando."
    },
    "Filtro de Cabine": {
        "categoria": "Conforto e Ar-condicionado",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Média",
        "descricao": "Mantém qualidade do ar interno e eficiência do sistema de climatização."
    },
    "Palhetas do Limpador": {
        "categoria": "Visibilidade e Segurança",
        "intervalo_km": 12000,
        "intervalo_meses": 12,
        "criticidade": "Média",
        "descricao": "Substituir se houver ruído, falhas de limpeza ou ressecamento."
    },
    "Fluido de Freio": {
        "categoria": "Freios",
        "intervalo_km": 40000,
        "intervalo_meses": 24,
        "criticidade": "Alta",
        "descricao": "Fluido higroscópico; deve ser verificado/substituído conforme contaminação e prazo."
    },
    "Inspeção de Pastilhas, Discos e Pinças": {
        "categoria": "Freios",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Alta",
        "descricao": "Regeneração reduz desgaste, mas o sistema físico ainda precisa inspeção."
    },
    "Limpeza e Lubrificação das Pinças de Freio": {
        "categoria": "Freios",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Média",
        "descricao": "Importante em regiões úmidas, litorâneas ou com corrosão."
    },
    "Revisão Geral EV": {
        "categoria": "Inspeção Geral",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Alta",
        "descricao": "Inspeção geral de segurança, suspensão, direção, luzes, fluidos e sistemas EV."
    },
    "Checkup do Sistema de Alta Tensão": {
        "categoria": "Sistema Elétrico EV",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Alta",
        "descricao": "Inspeção visual e diagnóstica de bateria HV, cabos, conectores e alertas."
    },
    "Inspeção da Porta de Recarga e Vedação": {
        "categoria": "Sistema de Recarga",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Média",
        "descricao": "Verificar conector, tampa, vedação, sujeira, oxidação e encaixe do plugue."
    },
    "Inspeção da Bateria 12V": {
        "categoria": "Sistema Elétrico EV",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Alta",
        "descricao": "A bateria auxiliar alimenta módulos, acessórios e sistemas de controle."
    },
    "Inspeção do Sistema de Arrefecimento EV": {
        "categoria": "Arrefecimento e Térmica",
        "intervalo_km": 40000,
        "intervalo_meses": 24,
        "criticidade": "Alta",
        "descricao": "Verificar nível, vazamentos e condição do fluido térmico da bateria/inversor/motor."
    },
    "Substituição do Líquido de Arrefecimento EV": {
        "categoria": "Arrefecimento e Térmica",
        "intervalo_km": 150000,
        "intervalo_meses": 60,
        "criticidade": "Alta",
        "descricao": "Intervalo varia muito por fabricante; confirmar no manual do veículo."
    },
    "Inspeção do Óleo do Redutor / Unidade de Tração": {
        "categoria": "Powertrain EV",
        "intervalo_km": 60000,
        "intervalo_meses": 36,
        "criticidade": "Média",
        "descricao": "Alguns EVs possuem óleo do redutor/eixo elétrico com inspeção ou troca programada."
    },
    "Atualizações de Software e Diagnóstico": {
        "categoria": "Software e Diagnóstico",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Média",
        "descricao": "Verificar alertas, campanhas, recalls, atualização de módulos e falhas registradas."
    },
    "Inspeção de Suspensão e Direção": {
        "categoria": "Chassi e Segurança",
        "intervalo_km": 20000,
        "intervalo_meses": 12,
        "criticidade": "Alta",
        "descricao": "Verificar buchas, pivôs, terminais, amortecedores, ruídos e folgas."
    },
    "Fluido do Lavador do Para-brisa": {
        "categoria": "Visibilidade e Segurança",
        "intervalo_km": 5000,
        "intervalo_meses": 1,
        "criticidade": "Baixa",
        "descricao": "Completar reservatório e verificar funcionamento dos esguichos."
    }
}

REVISAO_PADRAO_GENERICA = {
    item: dados["intervalo_km"]
    for item, dados in MANUTENCOES_EV_DETALHADAS.items()
}
FATOR_DEGRADACAO_PADRAO = 35000
FACTOR_DEGRADACAO_PADRAO = FATOR_DEGRADACAO_PADRAO

# =============================================================================
# PERSISTÊNCIA DE DADOS
# Salvamento seguro para OnlineGDB: arquivos JSON na raiz.
# =============================================================================
def limpar_nome_usuario(usuario):
    usuario = str(usuario).strip()
    if not usuario:
        usuario = "default"
    caracteres_invalidos = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
    for c in caracteres_invalidos:
        usuario = usuario.replace(c, "_")
    return usuario

def get_arquivo_usuario(usuario="default"):
    usuario = limpar_nome_usuario(usuario)
    return f"{usuario}_garagem.json"

def get_arquivo_config_usuario(usuario="default"):
    usuario = limpar_nome_usuario(usuario)
    return f"{usuario}_config.json"

def salvar_dados(garagem, usuario="default"):
    try:
        arquivo = get_arquivo_usuario(usuario)
        dados_formatados = [veiculo.to_dict() for veiculo in garagem]
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados_formatados, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar dados: {e}")
        return False

def carregar_dados(usuario="default"):
    arquivo = get_arquivo_usuario(usuario)
    if not os.path.exists(arquivo):
        return []
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
        if not conteudo:
            return []
        dados_brutos = json.loads(conteudo)
        if not isinstance(dados_brutos, list):
            print("Arquivo de garagem inválido. Iniciando garagem vazia.")
            return []
        garagem = []
        for v in dados_brutos:
            try:
                garagem.append(VeiculoEV(**v))
            except Exception as erro_veiculo:
                print(f"Um veículo não pôde ser carregado: {erro_veiculo}")
        return garagem
    except json.JSONDecodeError:
        print("Arquivo JSON corrompido. Iniciando garagem vazia.")
        return []
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return []

def salvar_veiculo_ativo(usuario, garagem, veiculo_ativo):
    try:
        if not veiculo_ativo or not garagem:
            return False
        indice = garagem.index(veiculo_ativo)
        config = {
            "indice_veiculo_ativo": indice,
            "marca": veiculo_ativo.marca,
            "modelo": veiculo_ativo.modelo,
            "km_atual": veiculo_ativo.km_atual,
            "data_salvamento": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        arquivo = get_arquivo_config_usuario(usuario)
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar veículo ativo: {e}")
        return False

def carregar_veiculo_ativo(usuario, garagem):
    try:
        if not garagem:
            return None
        arquivo = get_arquivo_config_usuario(usuario)
        if not os.path.exists(arquivo):
            return None
        with open(arquivo, "r", encoding="utf-8") as f:
            config = json.load(f)
        indice = config.get("indice_veiculo_ativo")
        if indice is not None:
            try:
                indice = int(indice)
                if 0 <= indice < len(garagem):
                    return garagem[indice]
            except:
                pass
        marca = config.get("marca")
        modelo = config.get("modelo")
        if marca and modelo:
            for veiculo in garagem:
                if veiculo.marca == marca and veiculo.modelo == modelo:
                    return veiculo
        return None
    except Exception as e:
        print(f"Erro ao carregar veículo ativo: {e}")
        return None

# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================
class VeiculoEV:
    def __init__(self, marca, modelo, km_atual, info_tecnica, ultima_revisao=None, historico=None, historico_km=None, historico_recargas=None):
        self.marca = str(marca).upper()
        self.modelo = str(modelo).upper()
        self.km_atual = int(km_atual)
        self.info = info_tecnica
        self.plano = info_tecnica.get("Revisao", REVISAO_PADRAO_GENERICA)
        self.fator_degradacao = info_tecnica.get("FatorDegradacao", FATOR_DEGRADACAO_PADRAO)
        self.ultima_revisao = ultima_revisao if ultima_revisao else {item: 0 for item in self.plano}
        self.historico = historico if historico else []
        self.historico_km = historico_km if historico_km else []
        self.historico_recargas = historico_recargas if historico_recargas else []

    def calcular_saude_bateria(self):
        degradacao = self.km_atual / self.fator_degradacao
        saude = 100 - degradacao
        return max(saude, 65.0)

    def calcular_autonomia(self):
        try:
            capacidade = float(str(self.info["Bateria"]).split()[0])
            consumo = float(self.info.get("Consumo", 6.0))
            if consumo <= 0:
                return 0
            return capacidade * consumo
        except:
            return 0

    def calcular_custo_por_km(self, preco_kwh=0.65):
        try:
            consumo = float(self.info.get("Consumo", 6.0))
            if consumo <= 0:
                return 0
            return preco_kwh / consumo
        except:
            return 0

    def calcular_tempo_recarga(self, potencia_carregador, bateria_atual_percentual=20):
        try:
            capacidade_total = float(str(self.info["Bateria"]).split()[0])
            bateria_atual_kwh = capacidade_total * (bateria_atual_percentual / 100)
            energia_necessaria = capacidade_total - bateria_atual_kwh
            eficiencia = 0.9 if potencia_carregador > 22 else 0.95
            tempo_horas = (energia_necessaria / potencia_carregador) / eficiencia
            return tempo_horas
        except:
            return 0

    def pode_fazer_viagem(self, distancia_km, margem_seguranca=10):
        autonomia = self.calcular_autonomia()
        autonomia_com_margem = autonomia * (1 - margem_seguranca / 100)
        return autonomia_com_margem >= distancia_km

    def estimar_vida_util_bateria(self, limite_minimo=65.0):
        saude_atual = self.calcular_saude_bateria()
        if saude_atual <= limite_minimo:
            return 0
        km_restantes = (saude_atual - limite_minimo) * self.fator_degradacao
        return km_restantes

    def exibir_resumo_bateria(self):
        saude = self.calcular_saude_bateria()
        autonomia = self.calcular_autonomia()
        blocos_cheios = int((saude / 100) * 20)
        barra = "█" * blocos_cheios + "░" * (20 - blocos_cheios)
        print(f"Saúde estimada da bateria: {saude:.2f}%")
        print(f"Autonomia estimada: {autonomia:.0f} km")
        print(f"[{barra}]")

    def atualizar_km(self, nova_km):
        try:
            nk = int(nova_km)
            if nk < 0:
                print("KM não pode ser negativa.")
                return False
            if nk < self.km_atual:
                print(f"KM deve ser maior que a atual ({self.km_atual} km).")
                return False
            self.historico_km.append({"km_anterior": self.km_atual, "km_nova": nk, "data": datetime.now().strftime("%d/%m/%Y %H:%M")})
            self.km_atual = nk
            return True
        except ValueError:
            print("Digite um número válido.")
            return False

    def registrar_servico(self, item):
        """
        Registra uma manutenção como realizada exatamente na KM atual do veículo.

        Regra:
        - A última revisão do item passa a ser a KM atual.
        - A próxima manutenção será:
          KM atual + intervalo do serviço.
        """
        if item in self.plano:
            self.ultima_revisao[item] = int(self.km_atual)

            data = datetime.now().strftime("%d/%m/%Y %H:%M")

            self.historico.append(
                f"[{data}] {item} aos {self.km_atual} km"
            )

            return True

        return False


    def verificar_revisoes_pendentes(self):
        pendentes = []
        for item, intervalo in self.plano.items():
            proxima = self.ultima_revisao.get(item, 0) + intervalo
            if self.km_atual >= proxima:
                pendentes.append(item)
        return pendentes

    def get_manutencoes_por_periodo(self, data_inicio, data_fim):
        manutencoes = []
        for registro in self.historico:
            try:
                data_registro = datetime.strptime(registro.split("] ")[0][1:], "%d/%m/%Y %H:%M")
                if data_inicio <= data_registro <= data_fim:
                    manutencoes.append(registro)
            except:
                continue
        return manutencoes

    def registrar_recarga(self, bateria_inicial, bateria_final, energia_kwh, preco_kwh, local, tipo):
        try:
            bateria_inicial = float(bateria_inicial)
            bateria_final = float(bateria_final)
            energia_kwh = float(energia_kwh)
            preco_kwh = float(preco_kwh)
            if bateria_inicial < 0 or bateria_inicial > 100:
                print("Bateria inicial deve estar entre 0 e 100%.")
                return False
            if bateria_final < 0 or bateria_final > 100:
                print("Bateria final deve estar entre 0 e 100%.")
                return False
            if bateria_final <= bateria_inicial:
                print("Bateria final deve ser maior que a bateria inicial.")
                return False
            if energia_kwh <= 0:
                print("Energia carregada deve ser maior que zero.")
                return False
            if preco_kwh < 0:
                print("Preço do kWh não pode ser negativo.")
                return False
            custo_total = energia_kwh * preco_kwh
            recarga = {
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "km_atual": self.km_atual,
                "bateria_inicial": bateria_inicial,
                "bateria_final": bateria_final,
                "energia_kwh": energia_kwh,
                "preco_kwh": preco_kwh,
                "custo_total": custo_total,
                "local": local if local else "Não informado",
                "tipo": tipo if tipo else "Não informado"
            }
            self.historico_recargas.append(recarga)
            return True
        except:
            print("Erro ao registrar recarga. Verifique os dados informados.")
            return False

    def obter_resumo_recargas(self):
        total_recargas = len(self.historico_recargas)
        if total_recargas == 0:
            return {"total_recargas": 0, "energia_total": 0, "custo_total": 0, "custo_medio_recarga": 0, "preco_medio_kwh": 0, "km_rodados": 0, "custo_real_km": None, "consumo_real_km_kwh": None}
        energia_total = 0
        custo_total = 0
        for r in self.historico_recargas:
            energia_total += float(r.get("energia_kwh", 0))
            custo_total += float(r.get("custo_total", 0))
        custo_medio_recarga = custo_total / total_recargas if total_recargas > 0 else 0
        preco_medio_kwh = custo_total / energia_total if energia_total > 0 else 0
        try:
            primeira_recarga = self.historico_recargas[0]
            km_primeira_recarga = int(float(primeira_recarga.get("km_atual", self.km_atual)))
            km_rodados = self.km_atual - km_primeira_recarga
        except:
            km_rodados = 0
        if km_rodados > 0 and custo_total > 0 and energia_total > 0:
            custo_real_km = custo_total / km_rodados
            consumo_real_km_kwh = km_rodados / energia_total
        else:
            custo_real_km = None
            consumo_real_km_kwh = None
        return {"total_recargas": total_recargas, "energia_total": energia_total, "custo_total": custo_total, "custo_medio_recarga": custo_medio_recarga, "preco_medio_kwh": preco_medio_kwh, "km_rodados": km_rodados, "custo_real_km": custo_real_km, "consumo_real_km_kwh": consumo_real_km_kwh}

    def obter_ultima_recarga(self):
        if not self.historico_recargas:
            return None
        return self.historico_recargas[-1]

    def excluir_recarga(self, indice):
        try:
            if indice < 0 or indice >= len(self.historico_recargas):
                print("Índice de recarga inválido.")
                return False
            self.historico_recargas.pop(indice)
            return True
        except Exception as e:
            print(f"Erro ao excluir recarga: {e}")
            return False

    def editar_recarga(self, indice, bateria_inicial, bateria_final, energia_kwh, preco_kwh, local, tipo):
        try:
            if indice < 0 or indice >= len(self.historico_recargas):
                print("Índice de recarga inválido.")
                return False
            bateria_inicial = float(bateria_inicial)
            bateria_final = float(bateria_final)
            energia_kwh = float(energia_kwh)
            preco_kwh = float(preco_kwh)
            if bateria_inicial < 0 or bateria_inicial > 100:
                print("Bateria inicial deve estar entre 0 e 100%.")
                return False
            if bateria_final < 0 or bateria_final > 100:
                print("Bateria final deve estar entre 0 e 100%.")
                return False
            if bateria_final <= bateria_inicial:
                print("Bateria final deve ser maior que a bateria inicial.")
                return False
            if energia_kwh <= 0:
                print("Energia carregada deve ser maior que zero.")
                return False
            if preco_kwh < 0:
                print("Preço do kWh não pode ser negativo.")
                return False
            custo_total = energia_kwh * preco_kwh
            recarga_antiga = self.historico_recargas[indice]
            self.historico_recargas[indice] = {
                "data": recarga_antiga.get("data", datetime.now().strftime("%d/%m/%Y %H:%M")),
                "data_edicao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "km_atual": recarga_antiga.get("km_atual", self.km_atual),
                "bateria_inicial": bateria_inicial,
                "bateria_final": bateria_final,
                "energia_kwh": energia_kwh,
                "preco_kwh": preco_kwh,
                "custo_total": custo_total,
                "local": local if local else "Não informado",
                "tipo": tipo if tipo else "Não informado"
            }
            return True
        except Exception as e:
            print(f"Erro ao editar recarga: {e}")
            return False

    def calcular_custo_real_por_km_recargas(self):
        try:
            resumo = self.obter_resumo_recargas()
            if resumo["custo_real_km"] is None:
                return None
            return {"km_rodados": resumo["km_rodados"], "custo_total": resumo["custo_total"], "energia_total": resumo["energia_total"], "custo_por_km": resumo["custo_real_km"], "consumo_medio_km_kwh": resumo["consumo_real_km_kwh"]}
        except:
            return None

    def exportar_historico_csv(self, filename="historico.csv"):
        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Data", "Serviço", "KM"])
                for registro in self.historico:
                    data, servico_km = registro.split("] ")
                    data = data[1:]
                    servico, km = servico_km.split(" aos ")
                    writer.writerow([data, servico, km.replace(" km", "")])
            print(f"Histórico exportado para {filename}.")
            return True
        except Exception as e:
            print(f"Erro ao exportar histórico: {e}")
            return False

    def to_dict(self):
        return {"marca": self.marca, "modelo": self.modelo, "km_atual": self.km_atual, "info_tecnica": self.info, "ultima_revisao": self.ultima_revisao, "historico": self.historico, "historico_km": self.historico_km, "historico_recargas": self.historico_recargas}

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================
def buscar_preco_kwh(estado="SP"):
    precos = {"SP": 0.65, "RJ": 0.70, "MG": 0.55, "RS": 0.60, "PR": 0.58, "SC": 0.62, "BA": 0.75, "PE": 0.68, "CE": 0.63, "DF": 0.50}
    return precos.get(estado.upper(), 0.60)

def filtrar_veiculos(garagem, marca=None, autonomia_min=None):
    filtrados = garagem
    if marca:
        filtrados = [v for v in filtrados if v.marca.upper() == marca.upper()]
    if autonomia_min:
        filtrados = [v for v in filtrados if v.calcular_autonomia() >= autonomia_min]
    return filtrados

def exportar_garagem_json(garagem, filename="garagem_exportada.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump([v.to_dict() for v in garagem], f, indent=4, ensure_ascii=False)
        print(f"Garagem exportada para {filename}.")
    except Exception as e:
        print(f"Erro ao exportar garagem: {e}")

def importar_garagem_json(filename="garagem_importada.json"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if not isinstance(dados, list):
            print("Arquivo inválido.")
            return []
        return [VeiculoEV(**v) for v in dados]
    except Exception as e:
        print(f"Erro ao importar garagem: {e}")
        return []

# =============================================================================
# INTERFACE
# =============================================================================
def limpar_tela():
    print("\n" * 5)

def pausar():
    input("\nPressione Enter para continuar...")

def imprimir_cabecalho(texto):
    limpar_tela()
    print("=" * 70)
    print(texto.center(70))
    print("=" * 70)
    print()

def input_validado(prompt, tipo=int, min_val=None, max_val=None, max_tentativas=3):
    tentativas = 0
    while tentativas < max_tentativas:
        try:
            valor = input(prompt)
            if tipo == int:
                valor = int(valor)
            elif tipo == float:
                valor = float(valor.replace(",", "."))
            if min_val is not None and valor < min_val:
                print(f"Valor deve ser >= {min_val}")
                tentativas += 1
                continue
            if max_val is not None and valor > max_val:
                print(f"Valor deve ser <= {max_val}")
                tentativas += 1
                continue
            return valor
        except ValueError:
            print("Entrada inválida. Tente novamente.")
            tentativas += 1
    print("Número máximo de tentativas excedido.")
    return None

def selecionar_usuario():
    usuarios = []
    try:
        for nome_arquivo in os.listdir("."):
            if nome_arquivo.endswith("_garagem.json"):
                nome_usuario = nome_arquivo.replace("_garagem.json", "")
                usuarios.append(nome_usuario)
    except Exception:
        usuarios = []
    if not usuarios:
        return "default"
    imprimir_cabecalho("SELECIONAR USUÁRIO")
    for i, u in enumerate(usuarios, 1):
        print(f"{i}. {u}")
    print("0. Novo usuário")
    op = input("\nEscolha: ")
    if op == "0":
        novo_usuario = input("Digite o nome do novo usuário: ").strip()
        if novo_usuario:
            return limpar_nome_usuario(novo_usuario)
        return "default"
    try:
        indice = int(op) - 1
        if 0 <= indice < len(usuarios):
            return usuarios[indice]
        return "default"
    except:
        return "default"

# =============================================================================
# CADASTRO DE VEÍCULO
# =============================================================================
def menu_cadastro_novo(garagem, usuario="default"):
    imprimir_cabecalho("ADICIONAR VEÍCULO")
    print("1. Selecionar do catálogo")
    print("2. Cadastro manual")
    print("0. Cancelar")
    op = input("\nEscolha: ")
    if op == "0":
        return None
    if op == "1":
        marcas = sorted(list(DADOS_VEICULOS.keys()))
        imprimir_cabecalho("CATÁLOGO - MARCAS")
        for i, marca in enumerate(marcas, 1):
            print(f"{i}. {marca}")
        m_sel = input_validado("\nID da marca: ", min_val=1, max_val=len(marcas))
        if m_sel is None:
            return None
        marca_nome = marcas[m_sel - 1]
        modelos = sorted(list(DADOS_VEICULOS[marca_nome].keys()))
        imprimir_cabecalho(f"CATÁLOGO - {marca_nome}")
        for i, modelo in enumerate(modelos, 1):
            print(f"{i}. {modelo}")
        mo_sel = input_validado("\nID do modelo: ", min_val=1, max_val=len(modelos))
        if mo_sel is None:
            return None
        modelo_nome = modelos[mo_sel - 1]
        km = input_validado(f"KM atual do {modelo_nome}: ", min_val=0)
        if km is None:
            return None
        novo = VeiculoEV(marca_nome, modelo_nome, km, DADOS_VEICULOS[marca_nome][modelo_nome])
        garagem.append(novo)
        salvar_dados(garagem, usuario)
        print("Veículo cadastrado com sucesso.")
        pausar()
        return novo
    elif op == "2":
        imprimir_cabecalho("CADASTRO MANUAL")
        montadora = input("Nome da montadora: ").strip().upper()
        if not montadora:
            print("Marca não pode ser vazia.")
            pausar()
            return None
        carro_nome = input("Nome do modelo: ").strip().upper()
        if not carro_nome:
            print("Modelo não pode ser vazio.")
            pausar()
            return None
        quilometragem = input_validado("KM atual: ", min_val=0)
        if quilometragem is None:
            return None
        bateria_kwh = input_validado("Capacidade da bateria em kWh. Ex: 60.5: ", tipo=float, min_val=0.1)
        if bateria_kwh is None:
            print("Cadastro cancelado: bateria inválida.")
            pausar()
            return None
        consumo_medio = input_validado("Consumo médio em km/kWh. Ex: 6.0: ", tipo=float, min_val=0.1)
        if consumo_medio is None:
            print("Cadastro cancelado: consumo inválido.")
            pausar()
            return None
        info_custom = {"Bateria": f"{bateria_kwh} kWh", "Potencia": "Não informada", "Torque": "Não informado", "Consumo": consumo_medio, "Revisao": REVISAO_PADRAO_GENERICA, "FatorDegradacao": FATOR_DEGRADACAO_PADRAO}
        novo = VeiculoEV(montadora, carro_nome, quilometragem, info_custom)
        garagem.append(novo)
        salvar_dados(garagem, usuario)
        print("Veículo manual cadastrado com sucesso.")
        pausar()
        return novo
    return None

# =============================================================================
# TELAS PRINCIPAIS
# =============================================================================
def mostrar_dashboard(veiculo_ativo, usuario):
    imprimir_cabecalho("DASHBOARD")
    print(f"Usuário: {usuario}")
    if not veiculo_ativo:
        print("\nNenhum veículo ativo selecionado.")
        print("Acesse 'Minha Garagem' ou cadastre um veículo.")
        pausar()
        return
    print(f"\nVeículo ativo: {veiculo_ativo.marca} {veiculo_ativo.modelo}")
    print(f"Quilometragem atual: {veiculo_ativo.km_atual} km")
    print()
    veiculo_ativo.exibir_resumo_bateria()
    pendentes = veiculo_ativo.verificar_revisoes_pendentes()
    if pendentes:
        print("\nAlertas de manutenção:")
        for p in pendentes:
            print(f"- {p} está pendente.")
    else:
        print("\nManutenção: nenhuma pendência no momento.")
    ultima_recarga = veiculo_ativo.obter_ultima_recarga()
    print("\nÚltima recarga:")
    if ultima_recarga:
        print(f"Data: {ultima_recarga.get('data', 'Não informada')}")
        print(f"Local: {ultima_recarga.get('local', 'Não informado')}")
        print(f"Tipo: {ultima_recarga.get('tipo', 'Não informado')}")
        print(f"KM na recarga: {ultima_recarga.get('km_atual', 0)} km")
        print(f"Bateria: {ultima_recarga.get('bateria_inicial', 0):.1f}% -> {ultima_recarga.get('bateria_final', 0):.1f}%")
        print(f"Energia: {ultima_recarga.get('energia_kwh', 0):.2f} kWh")
        print(f"Custo: R$ {ultima_recarga.get('custo_total', 0):.2f}")
    else:
        print("Nenhuma recarga registrada ainda.")
    resumo = veiculo_ativo.obter_resumo_recargas()
    print("\nResumo de recargas:")
    print(f"Total de recargas: {resumo['total_recargas']}")
    print(f"Energia total carregada: {resumo['energia_total']:.2f} kWh")
    print(f"Gasto total em recargas: R$ {resumo['custo_total']:.2f}")
    print(f"Preço médio registrado do kWh: R$ {resumo['preco_medio_kwh']:.2f}")
    print("\nCustos por km:")
    estado = input("Estado para custo estimado. Ex: CE, SP, RJ. Enter para CE: ").strip().upper() or "CE"
    preco_kwh = buscar_preco_kwh(estado)
    custo_estimado_km = veiculo_ativo.calcular_custo_por_km(preco_kwh)
    print(f"\nCusto estimado por km usando tabela de {estado}: R$ {custo_estimado_km:.4f}")
    print(f"Preço estimado do kWh em {estado}: R$ {preco_kwh:.2f}")
    print(f"Consumo teórico do veículo: {veiculo_ativo.info.get('Consumo', 6.0)} km/kWh")
    if resumo["custo_real_km"] is not None:
        print("\nCusto real aproximado com base nas recargas:")
        print(f"KM considerados desde a primeira recarga: {resumo['km_rodados']} km")
        print(f"Gasto considerado: R$ {resumo['custo_total']:.2f}")
        print(f"Energia considerada: {resumo['energia_total']:.2f} kWh")
        print(f"Custo real aproximado por km: R$ {resumo['custo_real_km']:.4f}")
        print(f"Consumo real aproximado: {resumo['consumo_real_km_kwh']:.2f} km/kWh")
    else:
        print("\nCusto real por km ainda não disponível.")
        print("Para calcular corretamente: registre uma recarga, use o veículo e atualize a quilometragem.")
    pausar()

def menu_minha_garagem(garagem):
    imprimir_cabecalho("MINHA GARAGEM")
    if not garagem:
        print("Garagem vazia.")
        pausar()
        return None
    for i, v in enumerate(garagem, 1):
        print(f"{i}. {v.marca} {v.modelo} - {v.km_atual} km")
    idx = input_validado("\nEscolha o veículo ativo: ", min_val=1, max_val=len(garagem))
    if idx is None:
        return None
    return garagem[idx - 1]

def atualizar_quilometragem(veiculo_ativo, garagem, usuario):
    imprimir_cabecalho("ATUALIZAR QUILOMETRAGEM")
    if not veiculo_ativo:
        print("Nenhum veículo ativo selecionado.")
        pausar()
        return
    print(f"Veículo: {veiculo_ativo.marca} {veiculo_ativo.modelo}")
    print(f"KM atual: {veiculo_ativo.km_atual}")
    nova_km = input("\nNova KM: ")
    if veiculo_ativo.atualizar_km(nova_km):
        salvar_dados(garagem, usuario)
        print("Quilometragem atualizada com sucesso.")
    pausar()

def menu_manutencoes(veiculo_ativo, garagem, usuario):
    while True:
        imprimir_cabecalho("MANUTENÇÕES")
        if not veiculo_ativo:
            print("Nenhum veículo ativo selecionado.")
            pausar()
            return
        print(f"Veículo: {veiculo_ativo.marca} {veiculo_ativo.modelo}")
        print("\n1. Ver próximas manutenções")
        print("2. Registrar manutenção")
        print("3. Histórico de manutenções")
        print("0. Voltar")
        op = input("\nEscolha: ")
        if op == "0":
            return
        elif op == "1":
            imprimir_cabecalho("PRÓXIMAS MANUTENÇÕES")
            for item, intervalo in veiculo_ativo.plano.items():
                ultima = veiculo_ativo.ultima_revisao.get(item, 0)
                proxima = ultima + intervalo
                resta = proxima - veiculo_ativo.km_atual
                if resta > 0:
                    print(f"{item}: faltam {resta} km")
                else:
                    print(f"{item}: vencida há {abs(resta)} km")
            pausar()
        elif op == "2":
            imprimir_cabecalho("REGISTRAR MANUTENÇÃO")
            itens = list(veiculo_ativo.plano.keys())
            for i, item in enumerate(itens, 1):
                print(f"{i}. {item}")
            esc = input_validado("\nID do serviço: ", min_val=1, max_val=len(itens))
            if esc is not None:
                if veiculo_ativo.registrar_servico(itens[esc - 1]):
                    salvar_dados(garagem, usuario)
                    print("Serviço registrado com sucesso.")
            pausar()
        elif op == "3":
            imprimir_cabecalho("HISTÓRICO DE MANUTENÇÕES")
            if not veiculo_ativo.historico:
                print("Sem registros.")
            else:
                for h in veiculo_ativo.historico:
                    print(f"- {h}")
            pausar()

def escolher_tipo_recarga():
    print("\nTipo de recarga:")
    print("1. Residencial")
    print("2. Pública lenta")
    print("3. Pública rápida")
    print("4. Gratuita")
    print("5. Outro")
    tipo_op = input("Escolha: ")
    if tipo_op == "1":
        return "Residencial"
    elif tipo_op == "2":
        return "Pública lenta"
    elif tipo_op == "3":
        return "Pública rápida"
    elif tipo_op == "4":
        return "Gratuita"
    return "Outro"

def mostrar_lista_recargas_resumida(veiculo_ativo):
    for i, r in enumerate(veiculo_ativo.historico_recargas, 1):
        data = r.get("data", "Não informada")
        local = r.get("local", "Não informado")
        energia = float(r.get("energia_kwh", 0))
        custo = float(r.get("custo_total", 0))
        print(f"{i}. {data} | {local} | {energia:.2f} kWh | R$ {custo:.2f}")

def menu_recargas(veiculo_ativo, garagem, usuario):
    while True:
        imprimir_cabecalho("RECARGAS")
        if not veiculo_ativo:
            print("Nenhum veículo ativo selecionado.")
            pausar()
            return
        print(f"Veículo: {veiculo_ativo.marca} {veiculo_ativo.modelo}")
        print("\n1. Registrar recarga")
        print("2. Histórico de recargas")
        print("3. Resumo de recargas")
        print("4. Excluir recarga")
        print("5. Editar recarga")
        print("0. Voltar")
        op = input("\nEscolha: ")
        if op == "0":
            return
        elif op == "1":
            imprimir_cabecalho("REGISTRAR RECARGA")
            print(f"Veículo: {veiculo_ativo.marca} {veiculo_ativo.modelo}")
            print(f"KM atual registrada: {veiculo_ativo.km_atual} km")
            bateria_inicial = input_validado("Bateria inicial (%): ", tipo=float, min_val=0, max_val=100)
            if bateria_inicial is None:
                pausar(); continue
            bateria_final = input_validado("Bateria final (%): ", tipo=float, min_val=0, max_val=100)
            if bateria_final is None:
                pausar(); continue
            energia_kwh = input_validado("Energia carregada em kWh: ", tipo=float, min_val=0.01)
            if energia_kwh is None:
                pausar(); continue
            preco_kwh = input_validado("Preço do kWh em R$: ", tipo=float, min_val=0)
            if preco_kwh is None:
                pausar(); continue
            local = input("Local da recarga. Ex: Casa, Shopping, Posto: ").strip()
            tipo = escolher_tipo_recarga()
            if veiculo_ativo.registrar_recarga(bateria_inicial, bateria_final, energia_kwh, preco_kwh, local, tipo):
                salvar_dados(garagem, usuario)
                custo_total = energia_kwh * preco_kwh
                print("\nRecarga registrada com sucesso.")
                print(f"Custo total da recarga: R$ {custo_total:.2f}")
            pausar()
        elif op == "2":
            imprimir_cabecalho("HISTÓRICO DE RECARGAS")
            if not veiculo_ativo.historico_recargas:
                print("Sem recargas registradas.")
            else:
                for i, r in enumerate(veiculo_ativo.historico_recargas, 1):
                    print(f"\nRecarga {i}")
                    print(f"Data: {r.get('data', 'Não informada')}")
                    if r.get("data_edicao"):
                        print(f"Editada em: {r.get('data_edicao')}")
                    print(f"KM: {r.get('km_atual', 0)} km")
                    print(f"Bateria: {r.get('bateria_inicial', 0):.1f}% -> {r.get('bateria_final', 0):.1f}%")
                    print(f"Energia: {r.get('energia_kwh', 0):.2f} kWh")
                    print(f"Preço kWh: R$ {r.get('preco_kwh', 0):.2f}")
                    print(f"Custo total: R$ {r.get('custo_total', 0):.2f}")
                    print(f"Local: {r.get('local', 'Não informado')}")
                    print(f"Tipo: {r.get('tipo', 'Não informado')}")
            pausar()
        elif op == "3":
            imprimir_cabecalho("RESUMO DE RECARGAS")
            resumo = veiculo_ativo.obter_resumo_recargas()
            print(f"Total de recargas: {resumo['total_recargas']}")
            print(f"Energia total carregada: {resumo['energia_total']:.2f} kWh")
            print(f"Gasto total: R$ {resumo['custo_total']:.2f}")
            print(f"Custo médio por recarga: R$ {resumo['custo_medio_recarga']:.2f}")
            print(f"Preço médio do kWh registrado: R$ {resumo['preco_medio_kwh']:.2f}")
            if resumo["custo_real_km"] is not None:
                print("\nUso real aproximado:")
                print(f"KM rodados desde a primeira recarga: {resumo['km_rodados']} km")
                print(f"Custo real aproximado por km: R$ {resumo['custo_real_km']:.4f}")
                print(f"Consumo real aproximado: {resumo['consumo_real_km_kwh']:.2f} km/kWh")
            else:
                print("\nAinda não há dados suficientes para calcular custo real por km.")
                print("Registre uma recarga e depois atualize a quilometragem após usar o veículo.")
            pausar()
        elif op == "4":
            imprimir_cabecalho("EXCLUIR RECARGA")
            if not veiculo_ativo.historico_recargas:
                print("Não há recargas para excluir.")
                pausar(); continue
            print("Recargas registradas:")
            mostrar_lista_recargas_resumida(veiculo_ativo)
            escolha = input_validado("\nDigite o número da recarga que deseja excluir: ", min_val=1, max_val=len(veiculo_ativo.historico_recargas))
            if escolha is None:
                pausar(); continue
            indice = escolha - 1
            recarga = veiculo_ativo.historico_recargas[indice]
            print("\nRecarga selecionada:")
            print(f"Data: {recarga.get('data', 'Não informada')}")
            print(f"KM: {recarga.get('km_atual', 0)} km")
            print(f"Local: {recarga.get('local', 'Não informado')}")
            print(f"Tipo: {recarga.get('tipo', 'Não informado')}")
            print(f"Bateria: {recarga.get('bateria_inicial', 0):.1f}% -> {recarga.get('bateria_final', 0):.1f}%")
            print(f"Energia: {recarga.get('energia_kwh', 0):.2f} kWh")
            print(f"Custo total: R$ {recarga.get('custo_total', 0):.2f}")
            confirmar = input("\nTem certeza que deseja excluir esta recarga? (s/n): ").strip().lower()
            if confirmar == "s":
                if veiculo_ativo.excluir_recarga(indice):
                    salvar_dados(garagem, usuario)
                    print("Recarga excluída com sucesso.")
                else:
                    print("Não foi possível excluir a recarga.")
            else:
                print("Exclusão cancelada.")
            pausar()
        elif op == "5":
            imprimir_cabecalho("EDITAR RECARGA")
            if not veiculo_ativo.historico_recargas:
                print("Não há recargas para editar.")
                pausar(); continue
            print("Recargas registradas:")
            mostrar_lista_recargas_resumida(veiculo_ativo)
            escolha = input_validado("\nDigite o número da recarga que deseja editar: ", min_val=1, max_val=len(veiculo_ativo.historico_recargas))
            if escolha is None:
                pausar(); continue
            indice = escolha - 1
            recarga = veiculo_ativo.historico_recargas[indice]
            print("\nRecarga atual:")
            print(f"Data: {recarga.get('data', 'Não informada')}")
            print(f"KM: {recarga.get('km_atual', 0)} km")
            print(f"Bateria inicial: {recarga.get('bateria_inicial', 0):.1f}%")
            print(f"Bateria final: {recarga.get('bateria_final', 0):.1f}%")
            print(f"Energia: {recarga.get('energia_kwh', 0):.2f} kWh")
            print(f"Preço kWh: R$ {recarga.get('preco_kwh', 0):.2f}")
            print(f"Custo total: R$ {recarga.get('custo_total', 0):.2f}")
            print(f"Local: {recarga.get('local', 'Não informado')}")
            print(f"Tipo: {recarga.get('tipo', 'Não informado')}")
            print("\nDigite os novos dados da recarga. Nesta versão, é necessário preencher todos os campos novamente.")
            nova_bateria_inicial = input_validado("Nova bateria inicial (%): ", tipo=float, min_val=0, max_val=100)
            if nova_bateria_inicial is None:
                pausar(); continue
            nova_bateria_final = input_validado("Nova bateria final (%): ", tipo=float, min_val=0, max_val=100)
            if nova_bateria_final is None:
                pausar(); continue
            nova_energia_kwh = input_validado("Nova energia carregada em kWh: ", tipo=float, min_val=0.01)
            if nova_energia_kwh is None:
                pausar(); continue
            novo_preco_kwh = input_validado("Novo preço do kWh em R$: ", tipo=float, min_val=0)
            if novo_preco_kwh is None:
                pausar(); continue
            novo_local = input("Novo local da recarga: ").strip()
            novo_tipo = escolher_tipo_recarga()
            novo_custo_total = nova_energia_kwh * novo_preco_kwh
            print("\nResumo da alteração:")
            print(f"Bateria: {nova_bateria_inicial:.1f}% -> {nova_bateria_final:.1f}%")
            print(f"Energia: {nova_energia_kwh:.2f} kWh")
            print(f"Preço kWh: R$ {novo_preco_kwh:.2f}")
            print(f"Custo total recalculado: R$ {novo_custo_total:.2f}")
            print(f"Local: {novo_local if novo_local else 'Não informado'}")
            print(f"Tipo: {novo_tipo}")
            confirmar = input("\nConfirmar edição desta recarga? (s/n): ").strip().lower()
            if confirmar == "s":
                if veiculo_ativo.editar_recarga(indice, nova_bateria_inicial, nova_bateria_final, nova_energia_kwh, novo_preco_kwh, novo_local, novo_tipo):
                    salvar_dados(garagem, usuario)
                    print("Recarga editada com sucesso.")
                else:
                    print("Não foi possível editar a recarga.")
            else:
                print("Edição cancelada.")
            pausar()
        else:
            print("Opção inválida.")
            pausar()

def planejar_viagem(veiculo_ativo):
    imprimir_cabecalho("PLANEJAR VIAGEM")
    if not veiculo_ativo:
        print("Nenhum veículo ativo selecionado.")
        pausar()
        return
    distancia = input_validado("Distância da viagem em km: ", tipo=float, min_val=0)
    if distancia is None:
        return
    margem = input_validado("Margem de segurança em %. Use 10 se tiver dúvida: ", tipo=float, min_val=0, max_val=99)
    if margem is None:
        margem = 10
    estado = input("Estado para preço do kWh. Ex: CE, SP, RJ. Enter para CE: ").strip().upper() or "CE"
    autonomia = veiculo_ativo.calcular_autonomia()
    autonomia_com_margem = autonomia * (1 - margem / 100)
    preco_kwh = buscar_preco_kwh(estado)
    consumo = float(veiculo_ativo.info.get("Consumo", 6.0))
    if consumo <= 0:
        print("Consumo inválido para cálculo.")
        pausar()
        return
    energia_necessaria = distancia / consumo
    custo = energia_necessaria * preco_kwh
    pode = autonomia_com_margem >= distancia
    print("\nResultado da viagem:")
    print(f"Veículo: {veiculo_ativo.marca} {veiculo_ativo.modelo}")
    print(f"Distância: {distancia:.1f} km")
    print(f"Autonomia estimada: {autonomia:.0f} km")
    print(f"Autonomia com margem de {margem:.0f}%: {autonomia_com_margem:.0f} km")
    print(f"Energia estimada necessária: {energia_necessaria:.2f} kWh")
    print(f"Preço do kWh em {estado}: R$ {preco_kwh:.2f}")
    print(f"Custo estimado da viagem: R$ {custo:.2f}")
    if pode:
        print("\nStatus: viagem possível sem recarga, considerando a margem informada.")
    else:
        print("\nStatus: viagem não recomendada sem recarga.")
    pausar()

def custos_e_economia(veiculo_ativo):
    imprimir_cabecalho("CUSTOS E ECONOMIA")
    if not veiculo_ativo:
        print("Nenhum veículo ativo selecionado.")
        pausar()
        return
    estado = input("Estado. Ex: CE, SP, RJ. Enter para CE: ").strip().upper() or "CE"
    preco_kwh = buscar_preco_kwh(estado)
    gasolina = input_validado("Preço da gasolina em R$: ", tipo=float, min_val=0)
    if gasolina is None:
        return
    consumo_ev = float(veiculo_ativo.info.get("Consumo", 6.0))
    if consumo_ev <= 0:
        print("Consumo inválido.")
        pausar()
        return
    custo_ev_km_estimado = preco_kwh / consumo_ev
    custo_gasolina_km = gasolina / 10.5
    resumo = veiculo_ativo.obter_resumo_recargas()
    print(f"\nPreço do kWh estimado em {estado}: R$ {preco_kwh:.2f}")
    print(f"Consumo teórico do elétrico: {consumo_ev:.2f} km/kWh")
    print(f"Custo estimado por km do elétrico: R$ {custo_ev_km_estimado:.4f}")
    print(f"Custo por km estimado de carro a gasolina: R$ {custo_gasolina_km:.4f}")
    economia_estimativa_total = (custo_gasolina_km - custo_ev_km_estimado) * veiculo_ativo.km_atual
    print("\nEstimativa teórica:")
    if economia_estimativa_total >= 0:
        print(f"Economia estimada usando tabela de energia: R$ {economia_estimativa_total:.2f}")
    else:
        print("Nesse cenário teórico, o elétrico não gerou economia.")
        print(f"Diferença estimada: R$ {abs(economia_estimativa_total):.2f}")
    print("\nCom base nas recargas registradas:")
    print(f"Total de recargas: {resumo['total_recargas']}")
    print(f"Gasto total em recargas: R$ {resumo['custo_total']:.2f}")
    print(f"Energia total carregada: {resumo['energia_total']:.2f} kWh")
    print(f"Preço médio do kWh registrado: R$ {resumo['preco_medio_kwh']:.2f}")
    if resumo["custo_real_km"] is not None:
        economia_real_aproximada = (custo_gasolina_km - resumo["custo_real_km"]) * resumo["km_rodados"]
        print("\nUso real aproximado:")
        print(f"KM considerados: {resumo['km_rodados']} km")
        print(f"Custo real aproximado por km do elétrico: R$ {resumo['custo_real_km']:.4f}")
        print(f"Consumo real aproximado: {resumo['consumo_real_km_kwh']:.2f} km/kWh")
        if economia_real_aproximada >= 0:
            print(f"Economia real aproximada no período: R$ {economia_real_aproximada:.2f}")
        else:
            print("No período registrado, o elétrico não gerou economia aproximada.")
            print(f"Diferença aproximada: R$ {abs(economia_real_aproximada):.2f}")
    else:
        print("\nAinda não há dados suficientes para economia real.")
        print("Registre uma recarga, use o veículo e depois atualize a quilometragem.")
    pausar()

def menu_historico(veiculo_ativo):
    while True:
        imprimir_cabecalho("HISTÓRICO")
        if not veiculo_ativo:
            print("Nenhum veículo ativo selecionado.")
            pausar()
            return
        print("1. Histórico de manutenções")
        print("2. Histórico de quilometragem")
        print("3. Histórico de recargas")
        print("0. Voltar")
        op = input("\nEscolha: ")
        if op == "0":
            return
        elif op == "1":
            imprimir_cabecalho("HISTÓRICO DE MANUTENÇÕES")
            if not veiculo_ativo.historico:
                print("Sem registros.")
            else:
                for h in veiculo_ativo.historico:
                    print(f"- {h}")
            pausar()
        elif op == "2":
            imprimir_cabecalho("HISTÓRICO DE QUILOMETRAGEM")
            if not veiculo_ativo.historico_km:
                print("Sem registros.")
            else:
                for registro in veiculo_ativo.historico_km:
                    print(f"- {registro['data']}: {registro['km_anterior']} km -> {registro['km_nova']} km")
            pausar()
        elif op == "3":
            imprimir_cabecalho("HISTÓRICO DE RECARGAS")
            if not veiculo_ativo.historico_recargas:
                print("Sem recargas registradas.")
            else:
                for i, r in enumerate(veiculo_ativo.historico_recargas, 1):
                    print(f"\nRecarga {i}")
                    print(f"Data: {r.get('data', 'Não informada')}")
                    if r.get("data_edicao"):
                        print(f"Editada em: {r.get('data_edicao')}")
                    print(f"KM: {r.get('km_atual', 0)} km")
                    print(f"Bateria: {r.get('bateria_inicial', 0):.1f}% -> {r.get('bateria_final', 0):.1f}%")
                    print(f"Energia: {r.get('energia_kwh', 0):.2f} kWh")
                    print(f"Custo: R$ {r.get('custo_total', 0):.2f}")
                    print(f"Local: {r.get('local', 'Não informado')}")
                    print(f"Tipo: {r.get('tipo', 'Não informado')}")
            pausar()

def ficha_tecnica(veiculo_ativo):
    imprimir_cabecalho("FICHA TÉCNICA")
    if not veiculo_ativo:
        print("Nenhum veículo ativo selecionado.")
        pausar()
        return
    print(f"Veículo: {veiculo_ativo.marca} {veiculo_ativo.modelo}")
    print(f"KM atual: {veiculo_ativo.km_atual} km")
    print("\nDados técnicos:")
    for k, v in veiculo_ativo.info.items():
        if k != "Revisao":
            print(f"{k}: {v}")
    print(f"\nAutonomia estimada: {veiculo_ativo.calcular_autonomia():.0f} km")
    print(f"Saúde estimada da bateria: {veiculo_ativo.calcular_saude_bateria():.2f}%")
    print(f"Vida útil restante estimada da bateria: {veiculo_ativo.estimar_vida_util_bateria():.0f} km")
    pausar()

def diagnostico_sistema(usuario, garagem, veiculo_ativo):
    imprimir_cabecalho("DIAGNÓSTICO DO SISTEMA")
    arquivo_garagem = get_arquivo_usuario(usuario)
    arquivo_config = get_arquivo_config_usuario(usuario)
    print("Informações gerais:")
    print(f"Usuário atual: {usuario}")
    print(f"Arquivo da garagem: {arquivo_garagem}")
    print(f"Arquivo de configuração: {arquivo_config}")
    print(f"Arquivo da garagem existe: {'Sim' if os.path.exists(arquivo_garagem) else 'Não'}")
    print(f"Arquivo de configuração existe: {'Sim' if os.path.exists(arquivo_config) else 'Não'}")
    print(f"Quantidade de veículos na garagem: {len(garagem)}")
    if veiculo_ativo:
        print("\nVeículo ativo:")
        print(f"Marca/modelo: {veiculo_ativo.marca} {veiculo_ativo.modelo}")
        print(f"KM atual: {veiculo_ativo.km_atual} km")
        print(f"Autonomia estimada: {veiculo_ativo.calcular_autonomia():.0f} km")
        print(f"Saúde estimada da bateria: {veiculo_ativo.calcular_saude_bateria():.2f}%")
        print(f"Manutenções registradas: {len(veiculo_ativo.historico)}")
        print(f"Alterações de KM registradas: {len(veiculo_ativo.historico_km)}")
        print(f"Recargas registradas: {len(veiculo_ativo.historico_recargas)}")
        pendentes = veiculo_ativo.verificar_revisoes_pendentes()
        print(f"Manutenções pendentes: {len(pendentes)}")
        if pendentes:
            for p in pendentes:
                print(f"- {p}")
        resumo = veiculo_ativo.obter_resumo_recargas()
        print("\nResumo técnico de recargas do veículo ativo:")
        print(f"Energia total registrada: {resumo['energia_total']:.2f} kWh")
        print(f"Custo total registrado: R$ {resumo['custo_total']:.2f}")
        if resumo['custo_real_km'] is not None:
            print(f"Custo real aproximado por km: R$ {resumo['custo_real_km']:.4f}")
            print(f"Consumo real aproximado: {resumo['consumo_real_km_kwh']:.2f} km/kWh")
        else:
            print("Custo real/consumo real: dados ainda insuficientes")
    else:
        print("\nVeículo ativo: nenhum selecionado")
    print("\nResumo da garagem:")
    if not garagem:
        print("Nenhum veículo cadastrado.")
    else:
        for i, v in enumerate(garagem, 1):
            print(f"{i}. {v.marca} {v.modelo} | {v.km_atual} km | {len(v.historico_recargas)} recargas | {len(v.historico)} manutenções")
    pausar()

def menu_ferramentas_backup(garagem, veiculo_ativo, usuario):
    while True:
        imprimir_cabecalho("FERRAMENTAS E BACKUP")
        print("1. Calcular tempo de recarga")
        print("2. Filtrar veículos")
        print("3. Exportar histórico de manutenção para CSV")
        print("4. Relatório de manutenção por período")
        print("5. Exportar garagem completa JSON")
        print("6. Importar garagem completa JSON")
        print("7. Diagnóstico do sistema")
        print("0. Voltar")
        op = input("\nEscolha: ")
        if op == "0":
            return
        elif op == "1":
            imprimir_cabecalho("TEMPO DE RECARGA")
            if not veiculo_ativo:
                print("Nenhum veículo ativo selecionado.")
                pausar(); continue
            potencia = input_validado("Potência do carregador em kW: ", tipo=float, min_val=0.1)
            bateria_atual = input_validado("Bateria atual em %: ", tipo=float, min_val=0, max_val=100)
            if potencia is not None and bateria_atual is not None:
                tempo = veiculo_ativo.calcular_tempo_recarga(potencia, bateria_atual)
                print(f"\nTempo estimado: {tempo:.2f} horas ({tempo * 60:.0f} minutos)")
            pausar()
        elif op == "2":
            imprimir_cabecalho("FILTRAR VEÍCULOS")
            marca = input("Marca ou Enter para todas: ").strip()
            autonomia_min = input_validado("Autonomia mínima em km ou 0 para ignorar: ", tipo=float, min_val=0)
            if autonomia_min is None:
                autonomia_min = 0
            filtrados = filtrar_veiculos(garagem, marca, autonomia_min)
            if not filtrados:
                print("Nenhum veículo encontrado.")
            else:
                for i, v in enumerate(filtrados, 1):
                    print(f"{i}. {v.marca} {v.modelo} - Autonomia: {v.calcular_autonomia():.0f} km")
            pausar()
        elif op == "3":
            imprimir_cabecalho("EXPORTAR HISTÓRICO CSV")
            if not veiculo_ativo:
                print("Nenhum veículo ativo selecionado.")
                pausar(); continue
            filename = input("Nome do arquivo. Ex: historico.csv: ").strip() or "historico.csv"
            veiculo_ativo.exportar_historico_csv(filename)
            pausar()
        elif op == "4":
            imprimir_cabecalho("RELATÓRIO POR PERÍODO")
            if not veiculo_ativo:
                print("Nenhum veículo ativo selecionado.")
                pausar(); continue
            data_inicio_str = input("Data inicial DD/MM/AAAA: ").strip() or "01/01/2020"
            data_fim_str = input("Data final DD/MM/AAAA: ").strip() or datetime.now().strftime("%d/%m/%Y")
            try:
                data_inicio = datetime.strptime(data_inicio_str, "%d/%m/%Y")
                data_fim = datetime.strptime(data_fim_str, "%d/%m/%Y").replace(hour=23, minute=59, second=59)
                manutencoes = veiculo_ativo.get_manutencoes_por_periodo(data_inicio, data_fim)
                if not manutencoes:
                    print("Nenhuma manutenção encontrada no período.")
                else:
                    for m in manutencoes:
                        print(f"- {m}")
            except:
                print("Formato de data inválido.")
            pausar()
        elif op == "5":
            imprimir_cabecalho("EXPORTAR GARAGEM JSON")
            filename = input("Nome do arquivo. Ex: garagem_exportada.json: ").strip() or "garagem_exportada.json"
            exportar_garagem_json(garagem, filename)
            pausar()
        elif op == "6":
            imprimir_cabecalho("IMPORTAR GARAGEM JSON")
            filename = input("Nome do arquivo. Ex: garagem_exportada.json: ").strip() or "garagem_exportada.json"
            nova_garagem = importar_garagem_json(filename)
            if nova_garagem:
                garagem.extend(nova_garagem)
                salvar_dados(garagem, usuario)
                print("Garagem importada com sucesso.")
            pausar()
        elif op == "7":
            diagnostico_sistema(usuario, garagem, veiculo_ativo)
        else:
            print("Opção inválida.")
            pausar()

# =============================================================================
# LOOP PRINCIPAL
# =============================================================================
def main():
    usuario = selecionar_usuario()
    minha_garagem = carregar_dados(usuario)
    veiculo_ativo = carregar_veiculo_ativo(usuario, minha_garagem)
    while True:
        imprimir_cabecalho("EV CARE - PAINEL PRINCIPAL")
        print(f"Usuário: {usuario}")
        if veiculo_ativo:
            print(f"Veículo ativo: {veiculo_ativo.marca} {veiculo_ativo.modelo}")
            print(f"KM atual: {veiculo_ativo.km_atual} km")
        else:
            print("Veículo ativo: nenhum selecionado")
        print("\n--- MENU PRINCIPAL ---")
        print("1. Dashboard")
        print("2. Minha Garagem / Trocar veículo")
        print("3. Adicionar veículo")
        print("4. Atualizar quilometragem")
        print("5. Manutenções")
        print("6. Recargas")
        print("7. Planejar viagem")
        print("8. Custos e economia")
        print("9. Histórico")
        print("10. Ficha técnica")
        print("11. Ferramentas e backup")
        print("0. Sair")
        opcao = input("\nEscolha: ")
        if opcao == "0":
            confirmar = input("Tem certeza que deseja sair? (s/n): ").lower()
            if confirmar == "s":
                salvar_dados(minha_garagem, usuario)
                if veiculo_ativo:
                    salvar_veiculo_ativo(usuario, minha_garagem, veiculo_ativo)
                print("Dados salvos. Encerrando...")
                break
        elif opcao == "1":
            mostrar_dashboard(veiculo_ativo, usuario)
        elif opcao == "2":
            selecionado = menu_minha_garagem(minha_garagem)
            if selecionado:
                veiculo_ativo = selecionado
                salvar_veiculo_ativo(usuario, minha_garagem, veiculo_ativo)
        elif opcao == "3":
            novo = menu_cadastro_novo(minha_garagem, usuario)
            if novo:
                veiculo_ativo = novo
                salvar_veiculo_ativo(usuario, minha_garagem, veiculo_ativo)
        elif opcao == "4":
            atualizar_quilometragem(veiculo_ativo, minha_garagem, usuario)
        elif opcao == "5":
            menu_manutencoes(veiculo_ativo, minha_garagem, usuario)
        elif opcao == "6":
            menu_recargas(veiculo_ativo, minha_garagem, usuario)
        elif opcao == "7":
            planejar_viagem(veiculo_ativo)
        elif opcao == "8":
            custos_e_economia(veiculo_ativo)
        elif opcao == "9":
            menu_historico(veiculo_ativo)
        elif opcao == "10":
            ficha_tecnica(veiculo_ativo)
        elif opcao == "11":
            menu_ferramentas_backup(minha_garagem, veiculo_ativo, usuario)
        else:
            print("Opção inválida.")
            pausar()

if __name__ == "__main__":
    main()
