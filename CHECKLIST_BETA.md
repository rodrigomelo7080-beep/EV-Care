# ✅ Checklist de Testes Beta — EV Care

Este checklist foi criado para orientar os testes da versão Beta do EV Care.

O objetivo é validar se as principais funcionalidades estão funcionando corretamente e identificar pontos de melhoria antes de uma versão mais ampla.

---

## 1. Acesso e Conta

- [ ] Acessar o link público do EV Care
- [ ] Criar uma nova conta
- [ ] Fazer login com uma conta existente
- [ ] Sair da conta
- [ ] Entrar novamente
- [ ] Confirmar que os dados da conta anterior não aparecem em outra conta

Observações:

```text
Escreva aqui qualquer problema encontrado no login, logout ou troca de conta.

## 2. Minha Garagem  ##

 Cadastrar um veículo
 Confirmar que o veículo aparece na lista
 Definir o veículo como ativo
 Editar dados do veículo
 Confirmar que o veículo ativo aparece corretamente nas outras páginas
 Testar limite de 1 veículo no plano Free
 Testar veículos adicionais em conta Plus, se aplicável

## 3. Quilometragem ##

 Abrir a página Quilometragem
 Confirmar que o veículo ativo aparece
 Atualizar a quilometragem
 Confirmar que a nova KM aparece corretamente
 Confirmar que o histórico de KM foi registrado
 Testar exportação CSV de quilometragem em conta Plus
 Confirmar que conta Free vê bloqueio de recurso Plus

 4. Recargas

 Registrar uma nova recarga
 Confirmar que a recarga aparece no histórico
 Editar uma recarga
 Excluir uma recarga
 Conferir o resumo de recargas
 Verificar energia total carregada
 Verificar gasto total
 Verificar preço médio do kWh
 Testar exportação CSV de recargas em conta Plus
 Confirmar que conta Free vê bloqueio de recurso Plus

 5. Manutenções

 Abrir a página Manutenções
 Confirmar que o painel de manutenção aparece
 Verificar serviços vencidos, próximos e em dia
 Registrar uma manutenção realizada
 Confirmar que o status da manutenção atualiza corretamente
 Adicionar serviço manual
 Editar serviço manual
 Remover serviço manual
 Conferir histórico de manutenções
 Testar exportação CSV de manutenções em conta Plus
 Confirmar que conta Free vê bloqueio de recurso Plus

 6. Dashboard

 Abrir o Dashboard sem login e verificar onboarding
 Abrir o Dashboard com login e sem veículo
 Abrir o Dashboard com veículo cadastrado
 Confirmar KM atual
 Confirmar autonomia estimada
 Confirmar saúde estimada da bateria
 Confirmar resumo de recargas
 Confirmar alertas de manutenção
 Confirmar que manutenções realizadas atualizam os alertas
 Testar relatório PDF em conta Plus
 Confirmar que conta Free vê bloqueio do PDF
 Testar relatório mensal em conta Plus

 7. Custos e Economia

 Abrir a página Custos e Economia
 Confirmar que os dados do veículo aparecem
 Alterar preço da gasolina
 Alterar consumo médio de carro a gasolina
 Conferir custo por km estimado
 Conferir gasto total online
 Conferir custo real por km quando houver dados suficientes
 Conferir economia aproximada

 8. Histórico

 Conferir histórico de quilometragem
 Conferir histórico de recargas
 Conferir histórico de manutenções
 Confirmar que os dados pertencem somente à conta logada

 9. Planos Free e Plus
Plano Free

 Confirmar limite de 1 veículo
 Confirmar bloqueio de exportações CSV
 Confirmar bloqueio do relatório PDF
 Confirmar bloqueio do relatório mensal

Plano Plus

 Confirmar veículos adicionais
 Confirmar exportação CSV de recargas
 Confirmar exportação CSV de quilometragem
 Confirmar exportação CSV de manutenções
 Confirmar relatório PDF
 Confirmar relatório mensal

 10. Feedback

 Abrir a página Feedback
 Enviar um feedback de teste
 Confirmar mensagem de sucesso
 Confirmar que o feedback aparece em Meus feedbacks
 Confirmar que o feedback foi salvo no sistema
 Confirmar que a notificação por e-mail foi recebida pelo responsável

 11. Teste de Troca de Conta
Use duas contas diferentes para este teste.
Conta A

 Entrar na Conta A
 Cadastrar ou confirmar veículo da Conta A
 Registrar recarga, KM ou manutenção
 Sair da Conta A

Conta B

 Entrar na Conta B
 Confirmar que os dados da Conta A não aparecem
 Cadastrar ou confirmar veículo da Conta B
 Sair da Conta B

Voltar para Conta A

 Entrar novamente na Conta A
 Confirmar que os dados da Conta A continuam corretos

 14. Interesse no EV Care Plus

 Eu usaria apenas o plano Free
 Eu teria interesse no plano Plus
 Eu pagaria por relatórios e exportações
 Eu pagaria por alertas inteligentes
 Eu indicaria o EV Care para outros usuários de veículos elétricos

 Aviso
Não envie senhas, documentos, dados bancários ou informações sensíveis durante os testes.
O EV Care está em Beta e pode passar por mudanças de interface, funcionalidades e regras de plano.