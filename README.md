# ⚡ EV Care

O **EV Care** é um aplicativo em desenvolvimento histórico de uso e manutenções periódicas de forma simples e visual.O **EV Care** é um aplicativo em desenvolvimento para gestão de veículos elétricos.

## 🚧 Status do projeto

Este projeto está em fase **Beta funcional**.

A versão atual já possui os principais módulos operacionais, mas ainda está em evolução. No momento, os dados são armazenados em arquivos JSON locais. Futuramente, o projeto deve evoluir para login de usuários e banco de dados online.

## 🎯 Objetivo

O objetivo do EV Care é ajudar proprietários de veículos elétricos a responder perguntas como:

- Quanto estou gastando com recargas?
- Qual é meu custo real por km?
- Qual é meu consumo real em km/kWh?
- Quando devo fazer a próxima manutenção?
- Minha viagem é possível com a autonomia atual?
- Meu carro elétrico está sendo mais econômico que um carro a gasolina?

## ✅ Funcionalidades atuais

### 🚗 Garagem

- Cadastro de veículos pelo catálogo
- Cadastro manual de veículos
- Seleção de veículo ativo
- Edição de veículo
- Exclusão de veículo com confirmação
- Salvamento do último veículo ativo

### 🔋 Recargas

- Registro de recargas
- Histórico de recargas
- Edição de recargas
- Exclusão de recargas
- Cálculo de gasto total
- Cálculo de preço médio do kWh
- Cálculo de custo real aproximado por km
- Cálculo de consumo real aproximado em km/kWh

### 🛣️ Quilometragem

- Atualização de KM atual
- Histórico de alterações de quilometragem
- Uso da KM para cálculos reais de consumo, custo e manutenção

### 🛠️ Manutenções

- Plano expandido de manutenção para veículos elétricos
- Registro de manutenções realizadas
- Serviços personalizados
- Edição de serviços de manutenção
- Remoção de serviços do plano
- Status de manutenção:
  - Em dia
  - Próximo
  - Vencido
- Cálculo da próxima manutenção com base na KM real em que o serviço foi registrado

### 📊 Dashboard

- Resumo do veículo ativo
- Autonomia estimada
- Saúde estimada da bateria
- Última recarga
- Gasto total em recargas
- Custo real por km
- Consumo real aproximado
- Alertas de manutenção
- Próxima manutenção relevante

### 🧭 Viagens

- Simulação de viagem
- Estimativa de energia necessária
- Estimativa de custo da viagem
- Verificação de autonomia com margem de segurança

### 💰 Custos e Economia

- Custo estimado por km do veículo elétrico
- Comparação com carro a gasolina
- Economia real aproximada com base em recargas
- Simulador de economia por distância

### 📜 Histórico

- Histórico de manutenções
- Histórico de quilometragem
- Histórico de recargas

### ⚙️ Configurações

- Diagnóstico do sistema
- Salvamento manual
- Backup dos dados
- Importação de backup JSON

## 🧰 Tecnologias usadas

- Python
- Streamlit
- JSON para armazenamento local
- GitHub Codespaces para desenvolvimento online
- GitHub para versionamento

## ▶️ Como executar o projeto

Instale as dependências:

```bash
python -m pip install -r requirements.txt

