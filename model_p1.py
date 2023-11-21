from pulp import * 
import json

class Model_p1():

    def extrair_dia(self, hora):
        ''' Retorna o dia de uma hora no formato dXX_hYY '''
        return hora.split('_')[0]

    def extrair_hora(self, dia):
        return (int(dia[1:])-1)*24

    def indice_da_hora(hora):
            return (int(hora[1:3])-1)*24+int(hora[-2:])-1
    
    def gerar_nome_arquivo_saida(self, nome_base_arquivo):
        if not os.path.exists(nome_base_arquivo + ".json"):
            return nome_base_arquivo + ".json"
        
        contador = 1
        while os.path.exists(f"{nome_base_arquivo}_{contador}.json"):
            contador += 1
        return f"{nome_base_arquivo}_{contador}.json"


    def modelo(self, cenario, solver, data, varBombeamentoPolpa):
        # variaveis utilizadas no modelo
        horas_D14 = data['horas_D14']
        produtos_conc = data['produtos_conc']
        horas_Dm3_D14 = ['horas_Dm3_D14'] 
        de_para_produtos_mina_conc = data['de_para_produtos_mina_conc']
        min_estoque_pulmao_concentrador = data['min_estoque_pulmao_concentrador'] 
        max_estoque_pulmao_concentrador = data['max_estoque_pulmao_concentrador'] 
        numero_faixas_producao = data['numero_faixas_producao']
        max_taxa_alimentacao = data['max_taxa_alimentacao']
        parametros_mina = data['parametros_mina']
        taxa_producao_britagem = data['taxa_producao_britagem']
        produtos_britagem = data['produtos_britagem']
        produtos_mina = data['produtos_mina'] 
        faixas_producao_concentrador = data['faixas_producao_concentrador'] 
        estoque_pulmao_inicial_concentrador = data['estoque_pulmao_inicial_concentrador']
        parametros_calculados = data['parametros_calculados']
        fatorGeracaoLama = data['fatorGeracaoLama']
        parametros_mineroduto_ubu = data['parametros_mineroduto_ubu']
        estoque_eb06_d0 = data['estoque_eb06_d0'] 
        dias = data['dias']
        args = data['args']

        BIG_M = 10e6
        modelo = LpProblem("Plano Semanal", LpMaximize)

        # Variável para definir a taxa de produção da britagem, por produto da mina, por hora
        varTaxaBritagem = LpVariable.dicts("Taxa Britagem", (produtos_mina, horas_D14), 0, None, LpContinuous)

        # Variável para definir o estoque pulmão pré-concentrador, por produto da mina, por hora
        varEstoquePulmaoConcentrador = LpVariable.dicts("Estoque Pulmao Concentrador", (produtos_mina, horas_D14), min_estoque_pulmao_concentrador, max_estoque_pulmao_concentrador, LpContinuous)

        # Variável que indica o produto que está sendo entregue pelo concentrador, por hora
        varProdutoConcentrador = LpVariable.dicts("Produto Concentrador", (produtos_mina, produtos_conc, horas_D14),  0, 1, LpInteger)

        # Variável para definir o nível da taxa de alimentação, por produto mina, epor produto do concentrador, por hora
        varNivelTaxaAlim = LpVariable.dicts("Nivel Taxa Alimentacao - C3", (produtos_mina, produtos_conc, horas_D14), 0, numero_faixas_producao, LpInteger)

        # Variável para definir da taxa de alimentação, por produto mina, e por produto do concentrador, por hora
        varTaxaAlimProdMinaConc = LpVariable.dicts("Taxa Alimentacao ProdMinaConc", (produtos_mina, produtos_conc, horas_D14), 0, max_taxa_alimentacao, LpContinuous)

        # Variável para definir da taxa de alimentação, por produto do concentrador, por hora
        varTaxaAlim = LpVariable.dicts("Taxa Alimentacao - C3", (produtos_conc, horas_D14), 0, max_taxa_alimentacao, LpContinuous)

        dados = {}

        # Restrição para garantir que a taxa de britagem se refere ao produto da mina que está sendo entregue

        for produto in produtos_mina:
            dados[produto] = []
            for hora in horas_D14:        
                # print(f'{taxa_producao_britagem[extrair_dia(hora)]}*{produtos_britagem[produto][hora]}')
                dados[produto].append(int(taxa_producao_britagem[self.extrair_dia(hora)]*produtos_britagem[produto][hora]))
                modelo += (            
                    varTaxaBritagem[produto][hora] <= int(taxa_producao_britagem[self.extrair_dia(hora)]*produtos_britagem[produto][hora]),
                    f"rest_TaxaBritagem_{produto}_{hora}"
                )

        # Restrição para tratar o de-para de produtos da mina e do concentrador
        #DA PRA TIRAR
        for produto_mina in produtos_mina:
            for produto_conc in produtos_conc:
                for hora in horas_D14:
                    if de_para_produtos_mina_conc[produto_mina][produto_conc] == 1:
                        modelo += (
                            varProdutoConcentrador[produto_mina][produto_conc][hora] <= 1,
                            f"rest_ProdutoConcentrador_{produto_mina}_{produto_conc}_{hora}"
                        )
                    else:
                        modelo += (
                            varProdutoConcentrador[produto_mina][produto_conc][hora] == 0,
                            f"rest_ProdutoConcentrador_{produto_mina}_{produto_conc}_{hora}"
                        )

        # Restrição para garantir que o concentrador produz um produto por vez
        #DA PRA TIRAR
        for hora in horas_D14:
            modelo += (
                lpSum([varProdutoConcentrador[produto_mina][produto_conc][hora] for produto_mina in produtos_mina for produto_conc in produtos_conc]) <= 1,
                f"rest_UmProdutoConcentrador_{hora}"
            )

        # Restrição para amarrar a taxa de alimentação do concentrador ao único produto produzido por vez
        #DA PRA TIRAR
        for produto_mina in produtos_mina:
            for produto_conc in produtos_conc:
                for hora in horas_D14:
                    modelo += (
                        varTaxaAlimProdMinaConc[produto_mina][produto_conc][hora] <= BIG_M*varProdutoConcentrador[produto_mina][produto_conc][hora],
                        f"rest_amarra_taxaAlimProdMinaConc_varProdConc_{produto_mina}_{produto_conc}_{hora}",
                    )

        # Amarra taxa de alimentação com as faixas de produção do concentrador
        for produto_mina in produtos_mina:
            for produto_conc in produtos_conc:
                for hora in horas_D14:
                    modelo += (
                        varTaxaAlimProdMinaConc[produto_mina][produto_conc][hora] 
                            == faixas_producao_concentrador*varNivelTaxaAlim[produto_mina][produto_conc][hora],
                        f"rest_FaixasProducaoConcentrador_{produto_mina}_{produto_conc}_{hora}",
                    )
                    modelo += (
                        varNivelTaxaAlim[produto_mina][produto_conc][hora] 
                            <= BIG_M*lpSum(varProdutoConcentrador[produto_mina][produto_conc][hora] for produto_mina in produtos_mina),
                        f"rest_TaxaAlimPorProduto_{produto_mina}_{produto_conc}_{hora}",
                    )

        # Define o estoque pulmão do concentrador
        for produto_mina in produtos_mina:
            for i in range(1, len(horas_D14)):
                modelo += (
                    varEstoquePulmaoConcentrador[produto_mina][horas_D14[i]] 
                        == varEstoquePulmaoConcentrador[produto_mina][horas_D14[i-1]]
                            + varTaxaBritagem[produto_mina][horas_D14[i]]
                            - lpSum([varTaxaAlimProdMinaConc[produto_mina][p][horas_D14[i]] for p in produtos_conc]),
                    f"rest_EstoquePulmaoConcentrador_{produto_mina}_{horas_D14[i]}",
                )
            
            # Define o estoque pulmão do concentrador da primeira hora
            modelo += (
                varEstoquePulmaoConcentrador[produto_mina][horas_D14[0]] 
                    == estoque_pulmao_inicial_concentrador[produto_mina]
                        + varTaxaBritagem[produto_mina][horas_D14[0]]
                        - lpSum([varTaxaAlimProdMinaConc[produto_mina][p][horas_D14[0]] for p in produtos_conc]),
                f"rest_EstoquePulmaoConcentrador_{produto_mina}_{horas_D14[0]}",
            )

        # Amarra as variáveis varTaxaAlimProdMinaConc e varTaxaAlim
        for produto_conc in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varTaxaAlim[produto_conc][hora] == lpSum(varTaxaAlimProdMinaConc[produto_mina][produto_conc][hora] for produto_mina in produtos_mina),
                    f"rest_amarra_varTaxaAlim_{produto_conc}_{hora}",
                )

        # '''
        # # Indica a hora de início das manutenções da britagem
        # varInicioManutencoesBritagem = LpVariable.dicts("Início Manutenção Britagem", (range(len(duracao_manutencoes_britagem)), horas_Dm3_D14), 0, 1, LpInteger)

        # # Restrição para garantir que a manutenção da britagem se inicia uma única vez
        # for idx_manut in range(len(duracao_manutencoes_britagem)):
        #     modelo += (
        #         lpSum([varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]] 
        #             for idx_hora in range(0, janela_planejamento*24)]) == 1,
        #         f"rest_define_InicioManutencoesBritagem_{idx_manut}",
        #     )

        # # Restrição que impede que as manutenções ocorram na segunda semana
        # for idx_manut in range(len(duracao_manutencoes_britagem)):
        #     modelo += (
        #         lpSum([varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]] 
        #             for idx_hora in range(janela_planejamento*24, len(horas_D14))]) == 0,
        #         f"rest_evita_InicioManutencoesBritagem_{idx_manut}",
        #     )

        # # Restrições para evitar que manutenções ocorram ao mesmo tempo
        # for idx_hora in range(len(horas_D14)):
        #     for idx_manut in range(len(duracao_manutencoes_britagem)):
        #         modelo += (
        #             varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]] +
        #             lpSum(varInicioManutencoesBritagem[s][horas_D14[j]] 
        #                 for j in range(idx_hora-duracao_manutencoes_britagem[idx_manut]+1,idx_hora)
        #                 for s in range(len(duracao_manutencoes_britagem))
        #                 if s != idx_manut
        #                 )
        #             <= 1,            
        #         f"rest_separa_manutencoesBritagem_{idx_manut}_{idx_hora}",
        #         )

        # # Fixa o horário de início da manutenção do britagem se foi escolhido pelo usuário
        # for idx_manut, inicio in enumerate(inicio_manutencoes_britagem):
        #     if inicio != 'livre':
        #         modelo += (
        #             varInicioManutencoesBritagem[idx_manut][inicio] == 1,
        #             f"rest_fixa_InicioManutencaoBritagem_{idx_manut}",
        #         )

        # # Restrição tratar manutenção, lower bound e valor fixo de taxa de produção da britagem

        # for idx_hora in range(len(horas_D14)):
        #     # se está em manutenção, zera a taxa de produção da britagem
        #     for idx_manut in range(len(duracao_manutencoes_britagem)):
        #         modelo += (
        #             lpSum([varTaxaBritagem[produto][horas_D14[idx_hora]] for produto in produtos_mina])
        #                 <= BIG_M*(1 - lpSum(varInicioManutencoesBritagem[idx_manut][horas_D14[j]] 
        #                                     for j in range(idx_hora - duracao_manutencoes_britagem[idx_manut] + 1, idx_hora))),
        #             f"rest_manutencao_britagem_{idx_manut}_{horas_D14[idx_hora]}",
        #     )
            
        #     # Define lower bound 
        #     # (não parece ser necessário, pois não há limite mínimo da britagem)
        #     # modelo += ( 
        #     #     varTaxaBritagem[horas_D14[idx_hora]] >= 0 # min_taxa_britagem
        #     #                                         - BIG_M*(lpSum(varInicioManutencoesBritagem[idx_manut][horas_D14[j]] 
        #     #                                                     for idx_manut in range(len(duracao_manutencoes_britagem))
        #     #                                                     for j in range(idx_hora - duracao_manutencoes_britagem[idx_manut] + 1, idx_hora))),
        #     #     f"rest_LB_taxa_alim1_{horas_D14[idx_hora]}",
        #     # )
        #     modelo += (
        #         lpSum([varTaxaBritagem[produto][horas_D14[idx_hora]] for produto in produtos_mina])
        #             <= BIG_M*(1 - lpSum(varInicioManutencoesBritagem[idx_manut][horas_D14[j]]
        #                                 for idx_manut in range(len(duracao_manutencoes_britagem)) 
        #                                 for j in range(idx_hora - duracao_manutencoes_britagem[idx_manut] + 1, idx_hora))),
        #         f"rest_UB_taxa_britagem_{horas_D14[idx_hora]}",
        #     )
        # '''
        # '''
        # # Indica a hora de início das manutenções do concentrador
        # varInicioManutencoesConcentrador = LpVariable.dicts("Início Manutenção Concentrador", (range(len(duracao_manutencoes_concentrador)), horas_Dm3_D14), 0, 1, LpInteger)

        # # Restrição para garantir que a manutenção do concentrador se inicia uma única vez
        # for idx_manut in range(len(duracao_manutencoes_concentrador)):
        #     modelo += (
        #         lpSum([varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]] 
        #             for idx_hora in range(0, janela_planejamento*24)]) == 1,
        #         f"rest_define_InicioManutencoesConcentrador_{idx_manut}",
        #     )

        # # Restrição que impede que as manutenções ocorram na segunda semana
        # for idx_manut in range(len(duracao_manutencoes_concentrador)):
        #     modelo += (
        #         lpSum([varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]] 
        #             for idx_hora in range(janela_planejamento*24, len(horas_D14))]) == 0,
        #         f"rest_evita_InicioManutencoesConcentrador_{idx_manut}",
        #     )

        # # Restrições para evitar que manutenções ocorram ao mesmo tempo
        # for idx_hora in range(len(horas_D14)):
        #     for idx_manut in range(len(duracao_manutencoes_concentrador)):
        #         modelo += (
        #             varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]] +
        #             lpSum(varInicioManutencoesConcentrador[s][horas_D14[j]] 
        #                 for j in range(idx_hora-duracao_manutencoes_concentrador[idx_manut]+1,idx_hora)
        #                 for s in range(len(duracao_manutencoes_concentrador))
        #                 if s != idx_manut
        #                 )
        #             <= 1,            
        #         f"rest_separa_manutencoesConcentrador_{idx_manut}_{idx_hora}",
        #         )

        # # Fixa o horário de início da manutenção do concentrador se foi escolhido pelo usuário
        # for idx_manut, inicio in enumerate(inicio_manutencoes_concentrador):
        #     if inicio != 'livre':
        #         modelo += (
        #             varInicioManutencoesConcentrador[idx_manut][inicio] == 1,
        #             f"rest_fixa_InicioManutencaoConcentrador_{idx_manut}",
        #         )

        # # Restrição tratar manutenção, lower bound e valor fixo de taxa de alimentação

        # for idx_hora in range(len(horas_D14)):
        #     # se está em manutenção, zera a taxa de alimentação
        #     for idx_manut in range(len(duracao_manutencoes_concentrador)):
        #         modelo += (
        #             lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
        #                 <= BIG_M*(1 - lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]] 
        #                                     for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
        #             f"rest_manutencao_concentrador_{idx_manut}_{horas_D14[idx_hora]}",
        #     )
            
        #     # Define lower bound
        #     modelo += (
        #         lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc]) 
        #             >= min_taxa_alimentacao - BIG_M*(lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]] 
        #                                                 for idx_manut in range(len(duracao_manutencoes_concentrador))
        #                                                 for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
        #         f"rest_LB_taxa_alim1_{horas_D14[idx_hora]}",
        #     )
        #     modelo += (
        #         lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc]) 
        #             <= BIG_M*(1 - lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
        #                                 for idx_manut in range(len(duracao_manutencoes_concentrador)) 
        #                                 for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
        #         f"rest_LB_taxa_alim2_{horas_D14[idx_hora]}",
        #     )

        #     # se a taxa de alimentacao é fixada pelo modelo ou pelo usuário
        #     if fixar_taxa_alimentacao in ['fixado_pelo_modelo','fixado_pelo_usuario']:
        #         taxa_fixa = taxa_alimentacao_fixa
        #         if fixar_taxa_alimentacao == 'fixado_pelo_modelo':
        #             varTaxaAlimFixa = LpVariable("Taxa Alimentacao - C3 Fixa", 0, max_taxa_alimentacao, LpContinuous)
        #             taxa_fixa = varTaxaAlimFixa
        #         modelo += (
        #             lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
        #                 >= taxa_fixa - BIG_M*(lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
        #                                     for idx_manut in range(len(duracao_manutencoes_concentrador))
        #                                     for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
        #             f"rest_taxa_alim_fixa1_{horas_D14[idx_hora]}",
        #         )
        #         modelo += (
        #             lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
        #                 <= BIG_M*(1 - lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
        #                                     for idx_manut in range(len(duracao_manutencoes_concentrador))
        #                                     for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
        #             f"rest_taxa_alim_fixa2_{horas_D14[idx_hora]}",
        #         )
        #         modelo += (
        #             lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc]) <= taxa_fixa,
        #             f"rest_taxa_alim_fixa3_{horas_D14[idx_hora]}",
        #         )
        # '''
        # Puxada, por dia, é calculada a partir da taxa de alimentação e demais parâmetros
        varPuxada = LpVariable.dicts("Puxada - C3 - Prog", (horas_D14), 0, None, LpContinuous) 
        for hora in horas_D14:
            modelo += (
                varPuxada[hora] == lpSum([varTaxaAlim[produto][hora] for produto in produtos_conc])*parametros_mina['DF - C3'][self.extrair_dia(hora)],
                f"rest_define_Puxada_{hora}",
            )

        # Produção, por produto do concentrador, por dia, é calculada a partir da taxa de alimentação e demais parâmetros
        varProducao = LpVariable.dicts("Producao - C3 - Prog", (produtos_conc, horas_D14), 0, None, LpContinuous) 
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varProducao[produto][hora]
                        == varTaxaAlim[produto][hora] * 
                            (1-parametros_mina['Umidade - C3'][self.extrair_dia(hora)]) * 
                            parametros_calculados['RP (Recuperação Mássica) - C3'][self.extrair_dia(hora)] / 
                            100 * parametros_mina['DF - C3'][self.extrair_dia(hora)] * 
                            (1 - parametros_mina['Dif. de Balanço - C3'][self.extrair_dia(hora)] / 100),
                    f"rest_define_Producao_{produto}_{hora}",
                )

        # Produção Volume, por hora, é calculada a partir produção volume
        varProducaoVolume = LpVariable.dicts("Producao volume/hora - C3 - Prog", (produtos_conc, horas_D14), 0, None, LpContinuous) 
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varProducaoVolume[produto][hora]
                        == varProducao[produto][hora] * (1/parametros_calculados['% Sólidos - EB06'][self.extrair_dia(hora)])
                                                    * (1/parametros_calculados['Densidade Polpa - EB06'][self.extrair_dia(hora)]),
                    f"rest_define_ProducaoVolume_{produto}_{hora}",
                )

        # Geração de Lama, por dia, é calculada a partir da puxada
        varGeracaoLama = LpVariable.dicts("Geracao de lama - C3 - Prog", (horas_D14), 0, None, LpContinuous) 
        for hora in horas_D14:
            modelo += (
                varGeracaoLama[hora] == (varPuxada[hora]*(1-parametros_mina['Umidade - C3'][self.extrair_dia(hora)]))*(1-fatorGeracaoLama),
                f"rest_define_GeracaoLama_{hora}",
            )

        # Rejeito Arenoso, por dia, é calculado a partir da puxada, geração de lama e produção
        varRejeitoArenoso = LpVariable.dicts("Geracao de rejeito arenoso - C3 - Prog", (horas_D14), 0, None, LpContinuous) 
        for hora in horas_D14:
            modelo += (
                varRejeitoArenoso[hora] == ((varPuxada[hora] * (1-parametros_mina['Umidade - C3'][self.extrair_dia(hora)]))) 
                                        - varGeracaoLama[hora] - lpSum(varProducao[produto][hora] for produto in produtos_conc),
                f"rest_define_RejeitoArenoso_{hora}",
            )

        # Indica o estoque EB06, por hora
        varEstoqueEB06 = LpVariable.dicts("Estoque EB06", (produtos_conc, horas_D14), 0, None, LpContinuous)
        #varEstoqueEB04 = LpVariable.dicts("Estoque EB04", (produtos_conc, horas_D14), 0, None, LpContinuous)

        # Indica se há bombeamento de polpa em cada hora
        #varBombeamentoPolpa = LpVariable.dicts("Bombeamento Polpa", (horas_Dm3_D14), 0, 1, LpInteger)

        # Restrição de capacidade do estoque EB06
        for hora in horas_D14:
            modelo += (
                lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc) 
                    <= parametros_mineroduto_ubu['Capacidade EB06'][hora],
                f"rest_capacidade_EstoqueEB06_{hora}",
            )

        # '''
        # # Restrição de capacidade do estoque EB04
        # for hora in horas_D14:
        #     modelo += (
        #         lpSum(varEstoqueEB04[produto][hora] for produto in produtos_conc) 
        #             <= capacidade_eb04,
        #         f"rest_capacidade_EstoqueEB04_{hora}",
        #     )

        # # Define se ha transferencia entre os tanques
        # varEnvioEB04EB06 = LpVariable.dicts("Envio EB04 para EB06", (produtos_conc, horas_D14), 0, 1, LpInteger)
        # varEnvioEB06EB04 = LpVariable.dicts("Envio EB06 para EB04", (produtos_conc, horas_D14), 0, 1, LpInteger)
        # # Define a quantidade da transferência entre os tanques
        # varTaxaEnvioEB04EB06 = LpVariable.dicts("Taxa Envio EB04 para EB06", (produtos_conc, horas_D14), 0, taxa_transferencia_entre_eb, LpContinuous)
        # varTaxaEnvioEB06EB04 = LpVariable.dicts("Taxa Envio EB06 para EB04", (produtos_conc, horas_D14), 0, taxa_transferencia_entre_eb, LpContinuous)
        # '''

        # # Indica se há bombeamento de polpa em cada hora
        # #varBombeamentoPolpa = LpVariable.dicts("Bombeamento Polpa", (produtos_conc, horas_Dm3_D14), 0, 1, LpInteger)
        # '''
        # for produto in produtos_conc:
        #     for hora in horas_D14:
        #         modelo += (
        #             varTaxaEnvioEB06EB04[produto][hora] <= taxa_transferencia_entre_eb*varEnvioEB06EB04[produto][hora],
        #             f"rest_define_TaxaEnvioEB06EB04_{produto}_{hora}",
        #         )
        #         modelo += (
        #             varTaxaEnvioEB04EB06[produto][hora] <= taxa_transferencia_entre_eb*varEnvioEB04EB06[produto][hora],
        #             f"rest_define_TaxaEnvioEB04EB06_{produto}_{hora}",
        #         )
        # '''
        # Define o valor de estoque de EB06, por produto, da segunda hora em diante
        for produto in produtos_conc:
            for i in range(1, len(horas_D14)):
                modelo += (
                    varEstoqueEB06[produto][horas_D14[i]] 
                        == varEstoqueEB06[produto][horas_D14[i-1]] 
                        + varProducaoVolume[produto][horas_D14[i]] 
                        - varBombeamentoPolpa[produto][horas_D14[i]]*parametros_mina['Vazão bombas - M3'][self.extrair_dia(horas_D14[i])],
                    f"rest_define_EstoqueEB06_{produto}_{horas_D14[i]}",
                )
        
        # Define o valor de estoque de EB06, por produto, da primeira hora
        for produto in produtos_conc:
            modelo += (
                varEstoqueEB06[produto][horas_D14[0]]
                    == estoque_eb06_d0[produto] + 
                    varProducaoVolume[produto][horas_D14[0]] - 
                    varBombeamentoPolpa[produto][horas_D14[0]]*parametros_mina['Vazão bombas - M3'][self.extrair_dia(horas_D14[0])],
                f"rest_define_EstoqueEB06_{produto}_{horas_D14[0]}",
            )

        # '''
        # # Define o valor de estoque de EB04, por produto, da segunda hora em diante
        # for produto in produtos_conc:
        #     for i in range(1, len(horas_D14)):
        #         modelo += (
        #             varEstoqueEB04[produto][horas_D14[i]] 
        #                 == varEstoqueEB04[produto][horas_D14[i-1]]
        #                 - varTaxaEnvioEB04EB06[produto][horas_D14[i]] 
        #                 + varTaxaEnvioEB06EB04[produto][horas_D14[i]],
        #                 # + (varEnvioEB06EB04[produto][horas_D14[i]] - varEnvioEB04EB06[produto][horas_D14[i]])*taxa_transferencia_entre_eb,
        #             f"rest_define_EstoqueEB04_{produto}_{horas_D14[i]}",
        #         )

        # # Define o valor de estoque de EB04, por produto, da primeira hora
        # for produto in produtos_conc:
        #     modelo += (
        #         varEstoqueEB04[produto][horas_D14[0]] 
        #             == estoque_eb04_d0[produto] + 
        #                 - varTaxaEnvioEB04EB06[produto][horas_D14[0]] 
        #                 + varTaxaEnvioEB06EB04[produto][horas_D14[0]],
        #                 # (varEnvioEB06EB04[produto][horas_D14[0]] - varEnvioEB04EB06[produto][horas_D14[0]])*taxa_transferencia_entre_eb,
        #         f"rest_define_EstoqueEB04_{produto}_{horas_D14[0]}",
        #     )

        # # Restrição de transferência em unico sentido
        # for hora in horas_D14:
        #     modelo += (
        #         lpSum(varEnvioEB04EB06[produto][hora] + varEnvioEB06EB04[produto][hora] for produto in produtos_conc) <= 1,
        #         f"rest_tranferencia_sentido_unico_{hora}",
        #     )

        # # Restricao de transferencia em enchimento de tanque
        # for hora in horas_D14:
        #     modelo += (
        #         fator_limite_excesso_EB04*parametros_mineroduto_ubu['Capacidade EB06'][hora] 
        #             - lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc)
        #             <= BIG_M * (1 - lpSum(varEnvioEB06EB04[produto][hora] for produto in produtos_conc)),
        #         f"rest_define_tranferencia_por_enchimento_tanque_{hora}",
        #     )
        # '''
        print(f'[OK]\nDefinindo função objetivo...   ', end='')

        for fo in cenario['geral']['funcao_objetivo']:
            if not fo in ['max_brit', 'min_atr_nav', 'max_conc', 'max_usina', 'max_est_polpa', 'max_pf', 'min_est_patio']:
                raise Exception(f"Função objetivo {fo} não implementada!")

        # Definindo a função objetivo
        fo = 0
        #if 'min_atr_nav' in cenario['geral']['funcao_objetivo']:
        #    fo += - (lpSum([varVolumeAtrasadoNavio[navio] for navio in navios_ate_d14]))
        if 'max_conc' in cenario['geral']['funcao_objetivo']:
            fo += lpSum([varTaxaAlim[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
        #if 'max_usina' in cenario['geral']['funcao_objetivo']:
        #    fo += lpSum([varProducaoSemIncorporacao[produto_usina][hora] for produto_usina in produtos_usina for hora in horas_D14])
        #if 'max_est_polpa' in cenario['geral']['funcao_objetivo']:
        #    fo += lpSum([varEstoquePolpaUbu[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
        #if 'min_est_patio' in cenario['geral']['funcao_objetivo']:
        #    fo += - (lpSum([varEstoquePatio[hora] for hora in horas_D14]))
        if 'max_brit' in cenario['geral']['funcao_objetivo']:
            fo += (lpSum([varTaxaBritagem[produto_mina][hora] for produto_mina in produtos_mina for hora in horas_D14]))

        modelo += (fo, "FO",)

        # The problem data is written to an .lp file
        # prob.writeLP("PSemanal.lp")

        print(f'[OK]\nRESOLVENDO o modelo...   ', end='')

        # The problem is solved using PuLP's choice of Solver
        solver.solve(modelo)
        print(varBombeamentoPolpa)
        print('===================================================================')
        resultados = {'variaveis':{}}
        for v in modelo.variables():
            resultados['variaveis'][v.name] = v.varValue

        resultados['parametros']= {'produtos_britagem': produtos_britagem, 'dados': dados}

        # Salva também os índices
        resultados['dias'] = dias
        resultados['horas_D14'] = horas_D14
        # Salvando informações do cenário
        resultados['cenario'] = {
                'nome': cenario['geral']['nome'],
            }

        # Salvando informações do solver
        resultados['solver'] = {
            'nome': solver.name,
            'fo': cenario['geral']['funcao_objetivo'],
            'valor_fo': modelo.objective.value(),
            'status': LpStatus[modelo.status],
            'tempo': modelo.solutionTime,
        }

        # Cria a pasta com os resultados dos experimentos se ainda não existir
        if not os.path.exists(args.pasta_saida):
            os.makedirs(args.pasta_saida)

        # Salvando os dados em arquivo binário usando pickels
        nome_arquivo_saida = self.gerar_nome_arquivo_saida(f"{cenario['geral']['nome']}_resultados_1")
        print(f'[OK]\nGerando arquivo {nome_arquivo_saida}...   ', end='')
        with open(f'{args.pasta_saida}/{nome_arquivo_saida}', "w", encoding="utf8") as f:
            json.dump(resultados, f)

        return modelo.status, resultados