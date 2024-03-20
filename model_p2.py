from pulp import *
import math

class Model_p2():

    def extrair_dia(self, hora):
        ''' Retorna o dia de uma hora no formato dXX_hYY '''
        return hora.split('_')[0]

    def extrair_hora(self, dia):
        return (int(dia[1:])-1)*24

    def indice_da_hora(self, hora):
            return (int(hora[1:3])-1)*24+int(hora[-2:])-1

    def gerar_nome_arquivo_saida(self, nome_base_arquivo):
        if not os.path.exists(nome_base_arquivo + ".json"):
            return nome_base_arquivo + ".json"

        contador = 1
        while os.path.exists(f"{nome_base_arquivo}_{contador}.json"):
            contador += 1
        return f"{nome_base_arquivo}_{contador}.json"

    def modelo(self, cenario, solver, data, varBombeamentoPolpaPPO):

        # variaveis utilizadas pelo modelo
        horas_D14 = data['horas_D14']
        produtos_conc = data['produtos_conc']
        parametros_calculados = data['parametros_calculados']
        dias = data['dias']
        max_producao_sem_incorporacao = data['max_producao_sem_incorporacao']
        args = data['args']
        produtos_usina = data['produtos_usina']
        de_para_produtos_conc_usina = data['de_para_produtos_conc_usina']
        parametros_ubu = data['parametros_ubu']
        min_estoque_polpa_ubu = data['min_estoque_polpa_ubu']
        max_estoque_polpa_ubu = data['max_estoque_polpa_ubu']
        max_taxa_envio_patio = data['max_taxa_envio_patio']
        max_taxa_retorno_patio_usina = data['max_taxa_retorno_patio_usina']
        min_estoque_patio_usina = data['min_estoque_patio_usina']
        max_estoque_patio_usina = data['max_estoque_patio_usina']
        estoque_polpa_ubu = data['estoque_polpa_ubu']
        estoque_inicial_patio_usina = data['estoque_inicial_patio_usina']
        fator_limite_excesso_patio = data['fator_limite_excesso_patio']
        vazao_bombas = data['vazao_bombas']


        BIG_M = 10e6
        modelo = LpProblem("Plano Semanal", LpMaximize)

        varTaxaBritagem = LpVariable.dicts("Britagem_Taxa_Producao", (produtos_mina, horas_D14), 0, None, LpContinuous)

        # Variável para definir o estoque pulmão pré-concentrador, por produto da mina, por hora
        varEstoquePulmaoConcentrador = LpVariable.dicts("Concentrador_Estoque_Pulmao", (produtos_mina, horas_D14),
                                                        parametros['capacidades']['pilha_pulmao']['min'], parametros['capacidades']['pilha_pulmao']['max'],
                                                        LpContinuous)

        # Variável que indica o produto que está sendo entregue pelo concentrador, por hora
        varProdutoConcentrador = LpVariable.dicts("Concentrador_ConversaoProduto", (produtos_mina, produtos_conc, horas_D14),  0, 1, LpInteger)

        # Variável que indica o início da campanha de um produto no concentrador, por hora
        # varInicioCampanhaConcentrador = LpVariable.dicts("Concentrador_InicioCampanha", (produtos_conc, horas_D14),  0, 1, LpInteger)

        # Variável que indica o final da campanha de um produto no concentrador, por hora
        varFimCampanhaConcentrador = LpVariable.dicts("Concentrador_FimCampanha", (produtos_conc, horas_D14),  0, 1, LpInteger)

        # Variável para definir da taxa de alimentação, por produto mina, e por produto do concentrador, por hora
        varTaxaAlimProdMinaConc = LpVariable.dicts("Concentrador_Taxa_Alimentacao_ConversaoProdutos", (produtos_mina, produtos_conc, horas_D14),
                                                0, parametros['capacidades']['Taxa_C3']['max'],
                                                LpContinuous)

        # Variável para definir da taxa de alimentação, por produto do concentrador, por hora
        varTaxaAlim = LpVariable.dicts("Concentrador_Taxa_Alimentacao", (produtos_conc, horas_D14),
                                        0, parametros['capacidades']['Taxa_C3']['max'],
                                        LpContinuous)

        # Variável para definir da taxa de alimentação acumulada, por produto do concentrador, por hora
        varTaxaAlimAcumulada = LpVariable.dicts("Concentrador_Taxa_Alimentacao_Acumulada",
                                                (produtos_conc, horas_D14),
                                                0, None,
                                                LpContinuous)

        # Variável para definir da janela de taxa de alimentação acumulada, por produto do concentrador, por hora
        varJanelaAlimAcumulada = LpVariable.dicts("Concentrador_Janela_Alimentacao_Acumulada",
                                                  (produtos_conc, horas_D14),
                                                  0, None,
                                                  LpInteger)

        dados = {}
        # Restrição para garantir que a taxa de britagem se refere ao produto da mina que está sendo entregue
        for produto in produtos_mina:
            dados[produto] = []
            for hora in horas_D14:
                # print(f'{parametros['calculados']['Taxa_Prod_Brit3'][extrair_dia(hora)]}*{produtos_britagem[produto][hora]}')
                dados[produto].append(int(parametros['calculados']['Taxa_Prod_Brit3'][extrair_dia(hora)]*produtos_britagem[produto][hora]))
                modelo += (
                    varTaxaBritagem[produto][hora] <= int(parametros['calculados']['Taxa_Prod_Brit3'][extrair_dia(hora)]*produtos_britagem[produto][hora]),
                    f"rest_TaxaBritagem_{produto}_{hora}"
                )

        # Restrição para tratar o de-para de produtos da mina e do concentrador
        for produto in produtos_mina:
            for produto_conc in produtos_conc:
                for hora in horas_D14:
                    if de_para_produtos_mina_conc[produto][produto_conc] == 1:
                        modelo += (
                            varProdutoConcentrador[produto][produto_conc][hora] <= 1,
                            f"rest_ProdutoConcentrador_{produto}_{produto_conc}_{hora}"
                        )
                    else:
                        modelo += (
                            varProdutoConcentrador[produto][produto_conc][hora] == 0,
                            f"rest_ProdutoConcentrador_{produto}_{produto_conc}_{hora}"
                        )

        # Restrição para garantir que o concentrador produz um produto por vez
        for hora in horas_D14:
            modelo += (
                lpSum([varProdutoConcentrador[produto_mina][produto_conc][hora] for produto_mina in produtos_mina for produto_conc in produtos_conc]) <= 1,
                f"rest_UmProdutoConcentrador_{hora}"
            )

        # # Restrição para garantir que a variável binária que indica o produto no concentrador é zero
        # # se não tem alimentação no concentrador
        # for hora in horas_D14:
        #     for produto_conc in produtos_conc:
        #         modelo += (
        #             lpSum([varProdutoConcentrador[produto_mina][produto_conc][hora] for produto_mina in produtos_mina]) <=
        #                 varTaxaAlim[produto_conc][hora],
        #             f"rest_SemTaxaSemProdutoConcentrador_{produto_conc}_{hora}"
        #         )

        # Restrições para definir os valores das variáveis de início e fim das campanhas de
        # produtos no concentrador

        def produto_concentrador_anterior(produto_conc, idx_hora):
            if idx_hora > 0:
                return lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora-1]] for produto_mina in produtos_mina])
            elif parametros['limites_campanhas'][produto_conc]['acum'] > 0:
                return 1
            else:
                return 0

        for produto_conc in produtos_conc:
            for idx_hora in range(1, len(horas_D14)):

                modelo += (
                    varFimCampanhaConcentrador[produto_conc][horas_D14[idx_hora-1]] >=
                        produto_concentrador_anterior(produto_conc, idx_hora) -
                        lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]),
                    f"rest_1_FimCampanhaConcentrador_{produto_conc}_{horas_D14[idx_hora-1]}"
                )
                modelo += (
                    varFimCampanhaConcentrador[produto_conc][horas_D14[idx_hora-1]] <=
                        2 -
                        lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]) -
                        produto_concentrador_anterior(produto_conc, idx_hora),
                    f"rest_2_FimCampanhaConcentrador_{produto_conc}_{horas_D14[idx_hora-1]}"
                )
                modelo += (
                    varFimCampanhaConcentrador[produto_conc][horas_D14[idx_hora-1]] <=
                        BIG_M*produto_concentrador_anterior(produto_conc, idx_hora),
                    f"rest_3_FimCampanhaConcentrador_{produto_conc}_{horas_D14[idx_hora-1]}"
                )

            modelo += (
                varFimCampanhaConcentrador[produto_conc][horas_D14[-1]] == 0,
                f"rest_3_FimCampanhaConcentrador_{produto_conc}_{horas_D14[-1]}"
            )

        # Restrições para calcular a taxa de alimentação acumulada no concentrador, por produto, por hora

        def massa_concentrador_anterior(produto_conc, idx_hora):
            if idx_hora > 0:
                return varTaxaAlimAcumulada[produto_conc][horas_D14[idx_hora-1]]
            else:
                return parametros['limites_campanhas'][produto_conc]['acum']

        for produto_conc in produtos_conc:

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][horas_D14[idx_hora]] <=
                        massa_concentrador_anterior(produto_conc, idx_hora)
                        + varTaxaAlim[produto_conc][horas_D14[idx_hora]]
                        + (1 - lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]))*BIG_M,
                    f"rest_1a_taxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][horas_D14[idx_hora]] >=
                        massa_concentrador_anterior(produto_conc, idx_hora)
                        + varTaxaAlim[produto_conc][horas_D14[idx_hora]]
                        - (1 - lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]))*BIG_M,
                    f"rest_1b_taxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][horas_D14[idx_hora]] <=
                    lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina])*BIG_M,
                    f"rest_1c_taxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

        for produto_conc in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][hora] >=
                        parametros['limites_campanhas'][produto_conc]['min'] -
                        (1 - varFimCampanhaConcentrador[produto_conc][hora])*BIG_M,
                        f"rest_limiteMinCampanhaConcentrador_{produto_conc}_{hora}",
                )
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][hora] <=
                        parametros['limites_campanhas'][produto_conc]['max'],
                        f"rest_limiteMaxCampanhaConcentrador_{produto_conc}_{hora}",
                )

        # Restrições para calcular a janela da taxa de alimentação acumulada no concentrador, por produto, por hora

        def janela_concentrador_anterior(produto_conc, idx_hora):
            if idx_hora > 0:
                return varJanelaAlimAcumulada[produto_conc][horas_D14[idx_hora-1]]
            else:
                return parametros['janelas_campanhas'][produto_conc]['acum']

        for produto_conc in produtos_conc:

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaAlimAcumulada[produto_conc][horas_D14[idx_hora]] <=
                        janela_concentrador_anterior(produto_conc, idx_hora)
                        + 1
                        + (1 - lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]))*BIG_M,
                    f"rest_1a_janelaTaxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaAlimAcumulada[produto_conc][horas_D14[idx_hora]] >=
                        janela_concentrador_anterior(produto_conc, idx_hora)
                        + 1
                        - (1 - lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]))*BIG_M,
                    f"rest_1b_janelaTaxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaAlimAcumulada[produto_conc][horas_D14[idx_hora]] <=
                    lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina])*BIG_M,
                    f"rest_1c_janelaTaxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

        # Restrições para garantir que as campanhas de produto no concentrador respeitam os
        # limites mínimos e máximos de massa

        for produto_conc in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varJanelaAlimAcumulada[produto_conc][hora] >=
                        parametros['janelas_campanhas'][produto_conc]['min'] -
                        (1 - varFimCampanhaConcentrador[produto_conc][hora])*BIG_M,
                        f"rest_limiteMinJanelaCampanhaConcentrador_{produto_conc}_{hora}",
                )
                modelo += (
                    varJanelaAlimAcumulada[produto_conc][hora] <=
                        parametros['janelas_campanhas'][produto_conc]['max'],
                        f"rest_limiteMaxJanelaCampanhaConcentrador_{produto_conc}_{hora}",
                )

        # Restrição para amarrar a taxa de alimentação do concentrador ao único produto produzido por vez
        for produto in produtos_mina:
            for produto_conc in produtos_conc:
                for hora in horas_D14:
                    modelo += (
                        varTaxaAlimProdMinaConc[produto][produto_conc][hora] <= BIG_M*varProdutoConcentrador[produto][produto_conc][hora],
                        f"rest_amarra_taxaAlimProdMinaConc_varProdConc_{produto}_{produto_conc}_{hora}",
                    )

        # Define o estoque pulmão do concentrador
        for produto in produtos_mina:
            for i in range(1, len(horas_D14)):
                modelo += (
                    varEstoquePulmaoConcentrador[produto][horas_D14[i]]
                        == varEstoquePulmaoConcentrador[produto][horas_D14[i-1]]
                            + varTaxaBritagem[produto][horas_D14[i]]
                            - lpSum([varTaxaAlimProdMinaConc[produto][p][horas_D14[i]] for p in produtos_conc]),
                    f"rest_EstoquePulmaoConcentrador_{produto}_{horas_D14[i]}",
                )

            # Define o estoque pulmão do concentrador da primeira hora
            modelo += (
                varEstoquePulmaoConcentrador[produto][horas_D14[0]]
                    == parametros['estoque_inicial']['pilha_pulmao'][produto]
                        + varTaxaBritagem[produto][horas_D14[0]]
                        - lpSum([varTaxaAlimProdMinaConc[produto][p][horas_D14[0]] for p in produtos_conc]),
                f"rest_EstoquePulmaoConcentrador_{produto}_{horas_D14[0]}",
            )

        # Amarra as variáveis varTaxaAlimProdMinaConc e varTaxaAlim
        for produto_conc in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varTaxaAlim[produto_conc][hora] == lpSum(varTaxaAlimProdMinaConc[produto_mina][produto_conc][hora] for produto_mina in produtos_mina),
                    f"rest_amarra_varTaxaAlim_{produto_conc}_{hora}",
                )

        # Puxada (em TMS) é calculada a partir da taxa de alimentação e demais parâmetros
        varPuxada = LpVariable.dicts("Concentrador_Puxada", (horas_D14), 0, None, LpContinuous)
        for hora in horas_D14:
            modelo += (
                varPuxada[hora] == lpSum([varTaxaAlim[produto][hora] for produto in produtos_conc]) *
                                parametros['gerais']['DF_C3'][extrair_dia(hora)] *
                                parametros['gerais']['UF_C3'][extrair_dia(hora)] *
                                (1-parametros['gerais']['Umidade'][extrair_dia(hora)]),
                f"rest_define_Puxada_{hora}",
            )

        # Produção, por produto do concentrador é calculada a partir da taxa de alimentação e demais parâmetros
        varProducao = LpVariable.dicts("Concentrador_Producao", (produtos_conc, horas_D14), 0, None, LpContinuous)
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varProducao[produto][hora]
                        == varTaxaAlim[produto][hora] *
                            (1-parametros['gerais']['Umidade'][extrair_dia(hora)]) *
                            (parametros['calculados']['RP (Recuperação Mássica) - C3'][hora][produto] / 100) *
                            parametros['gerais']['DF_C3'][extrair_dia(hora)] *
                            (1 - parametros['gerais']['Dif Balanço'][extrair_dia(hora)]),
                    f"rest_define_Producao_{produto}_{hora}",
                )

        # Produção Volume, por hora, é calculada a partir produção volume
        varProducaoVolume = LpVariable.dicts("Concentrador_Volume", (produtos_conc, horas_D14), 0, None, LpContinuous)
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varProducaoVolume[produto][hora]
                        == varProducao[produto][hora] * (1/parametros['config']['perc_solidos'])
                                                    * (1/parametros['config']['densidade']),
                    f"rest_define_ProducaoVolume_{produto}_{hora}",
                )

        # Geração de Lama, por dia, é calculada a partir da puxada
        varGeracaoLama = LpVariable.dicts("Concentrador_Lama", (horas_D14), 0, None, LpContinuous)
        for hora in horas_D14:
            modelo += (
                varGeracaoLama[hora] == varPuxada[hora]*(1-parametros['config']['fator_geracao_lama']),
                f"rest_define_GeracaoLama_{hora}",
            )

        # Rejeito Arenoso, por dia, é calculado a partir da puxada, geração de lama e produção
        varRejeitoArenoso = LpVariable.dicts("Concentrador_Rejeito_Arenoso", (horas_D14), 0, None, LpContinuous)
        for hora in horas_D14:
            modelo += (
                varRejeitoArenoso[hora] == varPuxada[hora] - varGeracaoLama[hora] - lpSum(varProducao[produto][hora] for produto in produtos_conc),
                f"rest_define_RejeitoArenoso_{hora}",
            )


        # Indica o estoque EB06, por hora
        varEstoqueEB06 = LpVariable.dicts("EB06_Estoque", (produtos_conc, horas_D14), 0, None, LpContinuous)

        # Restrição de capacidade do estoque EB06
        for hora in horas_D14:
            modelo += (
                lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc)
                    <= parametros['capacidades']['EB6']['max'],
                f"rest_capacidade_EstoqueEB06_{hora}",
            )


        # Define o valor de estoque de EB06, por produto, da segunda hora em diante
        for produto in produtos_conc:
            for i in range(1, len(horas_D14)):
                modelo += (
                    varEstoqueEB06[produto][horas_D14[i]]
                        == varEstoqueEB06[produto][horas_D14[i-1]]
                        + varProducaoVolume[produto][horas_D14[i]]
                        - varBombeamentoPolpaEB06[produto][horas_D14[i]]*parametros['gerais']['Vazao_EB6'][extrair_dia(horas_D14[i])],
                    f"rest_define_EstoqueEB06_{produto}_{horas_D14[i]}",
                )

        # Define o valor de estoque de EB06, por produto, da primeira hora
        for produto in produtos_conc:
            modelo += (
                varEstoqueEB06[produto][horas_D14[0]]
                    == parametros['estoque_inicial']['EB6'][produto] +
                    varProducaoVolume[produto][horas_D14[0]] -
                    varBombeamentoPolpaEB06[produto][horas_D14[0]]*parametros['gerais']['Vazao_EB6'][extrair_dia(horas_D14[0])]
                f"rest_define_EstoqueEB06_{produto}_{horas_D14[0]}",
            )

        # Restricao de transferencia em enchimento de tanque
        for hora in horas_D14:
            modelo += (
                parametros['config']['limite_perc_transferencia_entre_eb6_eb4']*parametros['capacidades']['EB6']['max']
                    - lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc)
                    <= BIG_M * (1 - lpSum(varEnvioEB06EB04[produto][hora] for produto in produtos_conc)),
                f"rest_define_tranferencia_por_enchimento_tanque_{hora}",
            )

        logger.info('[OK]')

        logger.info('Definindo variáveis e restrições do Mineroduto')

        # Indica o quanto foi bombeado de polpa do EB07, por produto do concentrador, em cada hora
        varBombeadoEB07 = LpVariable.dicts("Mineroduto_Bombeado_Polpa_EB07", (produtos_conc, horas_Dm3_D14), 0, None, LpContinuous)

        # Carrega os dados de D-3
        for hora in horas_Dm3:
            for produto in produtos_conc:
                if produto == parametros['bombEB06_dm3']['Bombeamento Polpa -D3'][hora]:
                    modelo += (
                        varBombeamentoPolpaEB06[produto][hora] == 1,
                        f"rest_define_Bombeamento_inicial_{produto}_{hora}",
                    )
                else:
                    modelo += (
                        varBombeamentoPolpaEB06[produto][hora] == 0,
                        f"rest_define_Bombeamento_inicial_{produto}_{hora}",
                    )

        # Carrega os dados de D-3
        for hora in horas_Dm3:
            for produto in produtos_conc:
                if produto == parametros['bombEB07_dm3']['Bombeamento Polpa -D3'][hora]:
                    modelo += (
                        varBombeadoEB07[produto][hora] == parametros['bombEB07_dm3']['bombeado'][hora],
                        f"rest_define_Bombeado_inicial_{produto}_{hora}",
                    )
                else:
                    modelo += (
                        varBombeadoEB07[produto][hora] == 0,
                        f"rest_define_Bombeado_inicial_{produto}_{hora}",
                    )

        # Restrição para garantir que apenas um produto é bombeado por vez
        for hora in horas_D14:
            modelo += (
                lpSum(varBombeamentoPolpaEB06[produto][hora] for produto in produtos_conc) <= 1,
                f"rest_bombeamento_unico_produto_{hora}",
            )

        def bombeamento_hora_anterior(produto, idx_hora):
            if idx_hora == 0:
                return varBombeamentoPolpaEB06[produto][horas_Dm3[-1]]
            else:
                return varBombeamentoPolpaEB06[produto][horas_D14[idx_hora-1]]

        # Define o bombeamento de polpa para as horas de d01 a d14, respeitando as janelas mínimas de polpa e de água respectivamente
        for produto in produtos_conc:
            for i, hora in enumerate(horas_D14[0:-parametros['config']['janela_min_bombeamento_polpa']+1]):
                modelo += (
                    varBombeamentoPolpaEB06[produto][horas_D14[i]] +
                        lpSum([varBombeamentoPolpaEB06[produto][horas_D14[j]] for j in range(i+1, i+parametros['config']['janela_min_bombeamento_polpa'])]) >=
                            parametros['config']['janela_min_bombeamento_polpa']
                            - parametros['config']['janela_min_bombeamento_polpa']*(1 - varBombeamentoPolpaEB06[produto][horas_D14[i]] + bombeamento_hora_anterior(produto, i)),
                    f"rest_janela_bombeamento_polpa_{produto}_{hora}",
            )

        # Para a primeira hora é necessário considerar o bombeamento de polpa que já pode ter acontecido no dia anterior ao do planejamento
        if parametros['calculados']['Bombeamento Acumulado Polpa final semana anterior'] > 0:
            tamanho_primeira_janela = parametros['config']['bombeamento_restante_janela_anterior_polpa']
            produto_polpa_semana_anterior = parametros['bombEB06_dm3']['Bombeamento Polpa -D3'][horas_Dm3[-1]]
            modelo += (
                lpSum([varBombeamentoPolpaEB06[produto_polpa_semana_anterior][horas_D14[j]] for j in range(0, tamanho_primeira_janela)]) >= tamanho_primeira_janela,
                f"rest_primeira_janela_bombeamento_polpa_{produto_polpa_semana_anterior}_{horas_D14[0]}",
            )

        # Para a primeira hora é necessário considerar o bombeamento de água que já pode ter acontecido no dia anterior ao do planejamento

        for produto in produtos_conc:
            if parametros['calculados']['Bombeamento Acumulado Agua final semana anterior'] > 0:
                tamanho_primeira_janela = parametros['config']['bombeamento_restante_janela_anterior_agua']
                modelo += (
                    lpSum([varBombeamentoPolpaEB06[produto][horas_D14[j]] for j in range(0, tamanho_primeira_janela)]) == 0,
                    f"rest_primeira_janela_bombeamento_polpa_{produto}_{horas_D14[0]}",
                )

        if parametros['config']['config_janela_final']:
            # Trata os últimos horários (tempo menor que a janela mínima de bombeamento de polpa) para que os bombeamentos de polpa,
            # se houverem sejam consecutivos até o final
            for produto in produtos_conc:
                # subject to Prod{i in 2..H-1}: #maximo de 1s
                #     sum{t in i..H-1}X[t] >= H - i - (1 - X[i])*M - X[i-1]*M;
                for i in range(len(horas_D14)-parametros['config']['janela_min_bombeamento_polpa']+1, len(horas_D14)):
                    modelo += (
                        lpSum(varBombeamentoPolpaEB06[produto][horas_D14[j]] for j in range(i,len(horas_D14)))
                            >= len(horas_D14) - i
                               - (1 - varBombeamentoPolpaEB06[produto][horas_D14[i]]) * BIG_M_MINERODUTO
                               - (varBombeamentoPolpaEB06[produto][horas_D14[i-1]] * BIG_M_MINERODUTO),
                        f"rest_janela_bombeamento_polpa_{produto}_{horas_D14[i]}",
                    )

        #for produto in produtos_conc:
        for i, hora in enumerate(horas_D14[0:-parametros['config']['janela_min_bombeamento_agua']+1]):
            modelo += (
                lpSum(varBombeamentoPolpaEB06[produto][horas_D14[i]] for produto in produtos_conc)+
                lpSum([varBombeamentoPolpaEB06[produto][horas_D14[j]]
                        for produto in produtos_conc for j in range(i+1, i+parametros['config']['janela_min_bombeamento_agua'])]) <=
                    BIG_M_MINERODUTO*(1 + lpSum(varBombeamentoPolpaEB06[produto][horas_D14[i]] for produto in produtos_conc)
                            - lpSum(bombeamento_hora_anterior(produto, i) for produto in produtos_conc)),
                f"rest_janela_bombeamento_agua_{produto}_{hora}",
            )

        # Define a quantidade bombeada de polpa por hora
        for produto in produtos_conc:
            for idx_hora in range(len(horas_Dm3), len(horas_Dm3_D14)):
                # modelo += (
                #     varBombeadoEB07[produto][horas_Dm3_D14[idx_hora]] ==
                #         varBombeamentoPolpaEB06[produto][horas_Dm3_D14[idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo']]] *
                #         parametros['gerais']['Vazao_EB7'][extrair_dia(horas_Dm3_D14[idx_hora])],
                #     f"rest_definie_bombeado_{produto}_{horas_Dm3_D14[idx_hora]}",
                # )

                if (idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo'] < len(horas_Dm3)):
                    vazaoEB06 = parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo']]]
                else:
                    vazaoEB06 = parametros['gerais']['Vazao_EB6'][extrair_dia(horas_Dm3_D14[idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo']])]
                modelo += (
                    varBombeadoEB07[produto][horas_Dm3_D14[idx_hora]] ==
                        varBombeamentoPolpaEB06[produto][horas_Dm3_D14[idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo']]] *
                        vazaoEB06,
                    f"rest_definie_bombeado_{produto}_{horas_Dm3_D14[idx_hora]}",
                )

        # Define a conservação de fluxo em matipo
        varEstoque_eb07 = LpVariable.dicts("EB07_Estoque", (produtos_conc, horas_D14), 0, None, LpContinuous)

        # Variável que indica o produto que está armazenado no EB07 (ele armazena um único produto por vez)
        varProdutoEB07 = LpVariable.dicts("EB07_Produto", (produtos_conc, horas_D14),  0, 1, LpInteger)

        # Define que o estoque EB07 tem apenas um produto por vez
        for hora in horas_D14:
            modelo += (
                lpSum(varProdutoEB07[produto][hora] for produto in produtos_conc) <= 1,
                f"rest_define_produto_eb07_{hora}",
            )

        for produto in produtos_conc:
            for i in range(len(horas_Dm3)+1, len(horas_Dm3_D14)):
                if (i-parametros['config']['tempo_mineroduto_Germano_Matipo'] < len(horas_Dm3)):
                    vazaoEB06 = parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[i-parametros['config']['tempo_mineroduto_Germano_Matipo']]]
                else:
                    vazaoEB06 = parametros['gerais']['Vazao_EB6'][extrair_dia(horas_Dm3_D14[i-parametros['config']['tempo_mineroduto_Germano_Matipo']])]
                modelo += (
                    varEstoque_eb07[produto][horas_Dm3_D14[i]] == varEstoque_eb07[produto][horas_Dm3_D14[i-1]] +
                        varBombeamentoPolpaEB06[produto][horas_Dm3_D14[i-parametros['config']['tempo_mineroduto_Germano_Matipo']]]*
                        #(vazaoEB06 - parametros['gerais']['Vazao_EB7'][extrair_dia(horas_Dm3_D14[i])]),
                        (vazaoEB06 - vazaoEB06),
                    f"rest_define_estoque_eb07_{produto}_{i}",
                )

            modelo += (
                varEstoque_eb07[produto][horas_D14[0]] == parametros['estoque_inicial']['EB7'][produto] +
                    varBombeamentoPolpaEB06[produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]]*
                    # (parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]] -
                    # parametros['gerais']['Vazao_EB7'][extrair_dia(horas_D14[0])]),
                    (parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]] -
                     parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]]),
                f"rest_define_estoque_eb07_hora0_{produto}_{hora}",
            )

        # Limita as quantidades de produtos no tanque eb07
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varEstoque_eb07[produto][hora] <= varProdutoEB07[produto][hora]*parametros['capacidades']['EB7']['max'],
                    f"rest_limita_max_estoque_eb07_{produto}_{hora}",
                )
                modelo += (
                    varEstoque_eb07[produto][hora] >= varProdutoEB07[produto][hora]*parametros['capacidades']['EB7']['min'],
                    f"rest_limita_min_estoque_eb07_{produto}_{hora}",
                )

        # Restrições para fixar as janelas de bombeamento

        # param H:= 24;    # horas
        # param d := 14;   # dias
        # param dmax := 6; # parametros['config']['janela_max_bombeamento_polpa']
        # param M := 100;  # infinito

        # var TB, integer, >=0; # parametros['config']['config_valor_janela_bombeamento_polpa'] ou livre
        # var Xac{t in 1..H}, integer, >=0; # Bombeamento acumulado
        # var X{t in 1..H}, binary; # Bombeamento (já temos)
        # var Xf{t in 1..H}, integer, >=0; # Bombeamento tamanho (último bombeamento)

        # Contabiliza o bombeamento acumulado de polpa - Xac
        varBombeamentoPolpaAcumulado = LpVariable.dicts("Mineroduto_Bombeamento_Polpa_Acumulado", (horas_D14), 0, len(horas_D14), LpInteger)

        # Indica o bombeamento final de polpa
        varBombeamentoPolpaFinal = LpVariable.dicts("Mineroduto_Bombeamento_Polpa_Final", (horas_D14), 0, len(horas_D14), LpInteger)

        # Restrições de SEQUENCIAMENTO FÁBRICA - CLIENTE para Bombeamento de Polpa

        def bombeamento_acumulado_polpa_hora_anterior(idx_hora):
            if idx_hora == 0:
                # subject to Producao2f{t in 1..H}: #maximo de 1s
                #    Xac[1] = 0;
                return parametros['calculados']['Bombeamento Acumulado Polpa final semana anterior']
            else:
                return varBombeamentoPolpaAcumulado[horas_D14[idx_hora-1]]

        # subject to Producao1a{t in 2..H}: #maximo de 1s
        #    Xac[t] <= Xac[t-1] + 1 + (1- X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <=
                    bombeamento_acumulado_polpa_hora_anterior(idx_hora) + 1 +
                    (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_1a_{horas_D14[idx_hora]}",
            )

        # subject to Producao1b{t in 2..H}: #maximo de 1s
        #    Xac[t] >= Xac[t-1] + 1 - (1- X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] >=
                    bombeamento_acumulado_polpa_hora_anterior(idx_hora) + 1 -
                    (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_1b_{horas_D14[idx_hora]}",
            )

        # subject to Producao1c{t in 2..H}: #maximo de 1s
        #    Xac[t] <= X[t]*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <= lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc)*BIG_M_MINERODUTO,
                f"rest_seq_bomb_1c_{horas_D14[idx_hora]}",
            )

        # subject to Producao2a{t in 2..H}: #maximo de 1s
        #    Xf[t] <= Xac[t-1] + (1 - X[t-1] + X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaFinal[horas_D14[idx_hora]] <=
                    bombeamento_acumulado_polpa_hora_anterior(idx_hora) +
                    (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)
                    + lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_2a_{horas_D14[idx_hora]}",
            )

        # subject to Producao2b{t in 2..H}: #maximo de 1s
        #    Xf[t] >= Xac[t-1] - (1 - X[t-1] + X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaFinal[horas_D14[idx_hora]] >=
                    bombeamento_acumulado_polpa_hora_anterior(idx_hora) -
                    (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)
                    + lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_2b_{horas_D14[idx_hora]}",
            )

        # subject to Producao2c{t in 2..H}: #maximo de 1s
        #    Xf[t] <= X[t-1]*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)*BIG_M_MINERODUTO,
                f"rest_seq_bomb_2c_{horas_D14[idx_hora]}",
            )

        # subject to Producao2d{t in 2..H}: #maximo de 1s
        #    Xf[t] <= (1-X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaFinal[horas_D14[idx_hora]] <=
                    (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_2d_{horas_D14[idx_hora]}",
            )

        # subject to Producao2e{t in 1..H}: #maximo de 1s
        #    Xf[t] <= dmax;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= parametros['config']['janela_max_bombeamento_polpa'],
                f"rest_seq_bomb_2e_{horas_D14[idx_hora]}",
            )

        # subject to Producao2ee{t in 1..H}: #maximo de 1s
        #    Xac[t] <= dmax;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <= parametros['config']['janela_max_bombeamento_polpa'],
                f"rest_seq_bomb_2ee_{horas_D14[idx_hora]}",
            )



        # Restrições de SEQUENCIAMENTO FÁBRICA - CLIENTE para Bombeamento de Água

        # Contabiliza o bombeamento acumulado de água - Xac
        varBombeamentoAguaAcumulado = LpVariable.dicts("Mineroduto_Bombeamento_Agua_Acumulado", (horas_D14), 0, len(horas_D14), LpInteger)

        # Indica o bombeamento final de água
        varBombeamentoAguaFinal = LpVariable.dicts("Mineroduto_Bombeamento_Agua_Final", (horas_D14), 0, len(horas_D14), LpInteger)

        def bombeamento_acumulado_agua_hora_anterior(idx_hora):
            if idx_hora == 0:
                # subject to Producao2f{t in 1..H}: #maximo de 1s
                #    Xac[1] = 0;
                return parametros['calculados']['Bombeamento Acumulado Agua final semana anterior']
            else:
                return varBombeamentoAguaAcumulado[horas_D14[idx_hora-1]]

        # subject to Producao1a{t in 2..H}: #maximo de 1s
        #    Xac[t] <= Xac[t-1] + 1 + (1- X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <=
                    bombeamento_acumulado_agua_hora_anterior(idx_hora) + 1 +
                    (1 - (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_agua_1a_{horas_D14[idx_hora]}",
            )

        # subject to Producao1b{t in 2..H}: #maximo de 1s
        #    Xac[t] >= Xac[t-1] + 1 - (1- X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaAcumulado[horas_D14[idx_hora]] >=
                    bombeamento_acumulado_agua_hora_anterior(idx_hora) + 1 -
                    (1 - (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_agua_1b_{horas_D14[idx_hora]}",
            )

        # subject to Producao1c{t in 2..H}: #maximo de 1s
        #    Xac[t] <= X[t]*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <=
                    (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_agua_1c_{horas_D14[idx_hora]}",
            )

        # subject to Producao2a{t in 2..H}: #maximo de 1s
        #    Xf[t] <= Xac[t-1] + (1 - X[t-1] + X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaFinal[horas_D14[idx_hora]] <=
                    bombeamento_acumulado_agua_hora_anterior(idx_hora) +
                    (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
                    + (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_agua_2a_{horas_D14[idx_hora]}",
            )

        # subject to Producao2b{t in 2..H}: #maximo de 1s
        #    Xf[t] >= Xac[t-1] - (1 - X[t-1] + X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaFinal[horas_D14[idx_hora]] >=
                    bombeamento_acumulado_agua_hora_anterior(idx_hora) -
                    (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
                    + (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_agua_2b_{horas_D14[idx_hora]}",
            )

        # subject to Producao2c{t in 2..H}: #maximo de 1s
        #    Xf[t] <= X[t-1]*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaFinal[horas_D14[idx_hora]] <=
                    (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_agua_2c_{horas_D14[idx_hora]}",
            )

        # subject to Producao2d{t in 2..H}: #maximo de 1s
        #    Xf[t] <= (1-X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaFinal[horas_D14[idx_hora]] <=
                    (1 - (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_agua_2d_{horas_D14[idx_hora]}",
            )

        # subject to Producao2e{t in 1..H}: #maximo de 1s
        #    Xf[t] <= dmax;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaFinal[horas_D14[idx_hora]] <= parametros['config']['janela_max_bombeamento_agua'],
                f"rest_seq_bomb_agua_2e_{horas_D14[idx_hora]}",
            )

        # subject to Producao2ee{t in 1..H}: #maximo de 1s
        #    Xac[t] <= dmax;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <= parametros['config']['janela_max_bombeamento_agua'],
                f"rest_seq_bomb_agua_2ee_{horas_D14[idx_hora]}",
            )


        logger.info('[OK]')

        logger.info('Definindo variáveis e restrições da Pelotização')

        # Indica chegada de polpa em Ubu, por produto, por hora
        varPolpaUbu = LpVariable.dicts("Ubu_Chegada_Polpa", (produtos_conc, horas_D14), 0, None, LpContinuous)

        # Define a chegada de polpa em Ubu
        for produto in produtos_conc:
            for i in range(3*24,len(horas_Dm3_D14)):
                modelo += (
                    varPolpaUbu[produto][horas_Dm3_D14[i]]
                        == varBombeadoEB07[produto][horas_Dm3_D14[i-(parametros['config']['tempo_mineroduto_Germano_Ubu']-parametros['config']['tempo_mineroduto_Germano_Matipo'])]] +
                        ajuste_polpa_Ubu,
                    f"rest_define_PolpaUbu_{produto}_{horas_Dm3_D14[i]}",
                )

        # Indica a produção sem incorporação em Ubu, por dia
        varProducaoSemIncorporacao = LpVariable.dicts("Pelot_Producao_sem_Incorporacao", (produtos_usina, horas_D14), 0, parametros['capacidades']['TaxaAlim_Pelot']['max'], LpContinuous)

        # Variável que indica o final da campanha de um produto na pelotização, por hora
        varFimCampanhaPelot = LpVariable.dicts("Pelot_FimCampanha", (produtos_usina, horas_D14),  0, 1, LpInteger)

        # Variável que indica o produto que está sendo entregue pela pelotização, por hora
        varProdutoPelot = LpVariable.dicts("Pelot_ConversaoProduto", (produtos_conc, produtos_usina, horas_D14),  0, 1, LpInteger)

        # Indica a produção em Ubu, por hora
        varProducaoUbu = LpVariable.dicts("Pelot_Alimentacao", (produtos_conc, produtos_usina, horas_D14), 0, None, LpContinuous)

        # Variável para definir a produção sem incorporação acumulada, por produto da pelotização, por hora
        varProdSemIncorpAcumulada = LpVariable.dicts("Pelot_Producao_sem_Incorporacao_Acumulada",
                                                (produtos_usina, horas_D14),
                                                0, None,
                                                LpContinuous)

        # Variável para definir da janela de produção sem incorporação acumulada, por produto da pelotização, por hora
        varJanelaProdSemIncorpAcumulada = LpVariable.dicts("Pelot_Janela_Acumulada",
                                                  (produtos_usina, horas_D14),
                                                  0, None,
                                                  LpInteger)

        # Restrição para garantir que a pelotização um produto por vez
        for hora in horas_D14:
            modelo += (
                lpSum([varProdutoPelot[produto_c][produto_u][hora] for produto_c in produtos_conc for produto_u in produtos_usina]) <= 1,
                f"rest_UmProdutoPelot_{hora}"
            )

        # Define a produção em Ubu
        for produto_c in produtos_conc:
            for produto_u in produtos_usina:
                for hora in horas_D14:
                    if de_para_produtos_conc_usina[produto_c][produto_u] == 1:
                        modelo += (
                            varProdutoPelot[produto_c][produto_u][hora] <= 1,
                            f"rest_ProdutoPelot_{produto_c}_{produto_u}_{hora}"
                        )
                        modelo += (
                            varProducaoUbu[produto_c][produto_u][hora] ==
                                varProducaoSemIncorporacao[produto_u][hora]*(1+parametros['gerais']['Fator_Conv'][extrair_dia(hora)]),
                            f"rest_define_ProducaoUbu_{produto_c}_{produto_u}_{hora}",
                        )
                    else:
                        modelo += (
                            varProdutoPelot[produto_c][produto_u][hora] == 0,
                            f"rest_ProdutoPelot_{produto_c}_{produto_u}_{hora}"
                        )
                        modelo += (
                            varProducaoUbu[produto_c][produto_u][hora] == 0,
                            f"rest_zera_ProducaoUbu_{produto_c}_{produto_u}_{hora}",
                        )

        # Restrição para amarrar a produção em Ubu ao único produto produzido por vez
        for produto_c in produtos_conc:
            for produto_u in produtos_usina:
                for hora in horas_D14:
                    modelo += (
                        varProducaoUbu[produto_c][produto_u][hora] <= BIG_M*varProdutoPelot[produto_c][produto_u][hora],
                        f"rest_amarra_producaoUbu_varProdPelot_{produto_c}_{produto_u}_{hora}",
                    )

        # Restrições para definir os valores das variáveis de início e fim das campanhas de
        # produtos na pelotização

        def produto_pelot_anterior(produto_usina, idx_hora):
            if idx_hora > 0:
                return lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora-1]] for produto_conc in produtos_conc])
            elif parametros['limites_campanhas'][produto_usina]['acum'] > 0:
                return 1
            else:
                return 0

        for produto_usina in produtos_usina:
            for idx_hora in range(1, len(horas_D14)):

                modelo += (
                    varFimCampanhaPelot[produto_usina][horas_D14[idx_hora-1]] >=
                        produto_pelot_anterior(produto_usina, idx_hora) -
                        lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]),
                    f"rest_1_FimCampanhaPelot_{produto_usina}_{horas_D14[idx_hora-1]}"
                )
                modelo += (
                    varFimCampanhaPelot[produto_usina][horas_D14[idx_hora-1]] <=
                        2 -
                        lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]) -
                        produto_pelot_anterior(produto_usina, idx_hora),
                    f"rest_2_FimCampanhaPelot_{produto_usina}_{horas_D14[idx_hora-1]}"
                )
                modelo += (
                    varFimCampanhaPelot[produto_usina][horas_D14[idx_hora-1]] <=
                        BIG_M*produto_pelot_anterior(produto_usina, idx_hora),
                    f"rest_3_FimCampanhaPelotr_{produto_usina}_{horas_D14[idx_hora-1]}"
                )

            modelo += (
                varFimCampanhaPelot[produto_usina][horas_D14[-1]] == 0,
                f"rest_3_FimCampanhaPelot_{produto_usina}_{horas_D14[-1]}"
            )

        # Restrições para calcular a produção sem incorporação acumulada na pelotização, por produto, por hora

        def massa_pelot_anterior(produto_usina, idx_hora):
            if idx_hora > 0:
                return varProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora-1]]
            else:
                return parametros['limites_campanhas'][produto_usina]['acum']

        for produto_usina in produtos_usina:

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] <=
                        massa_pelot_anterior(produto_usina, idx_hora)
                        + varProducaoSemIncorporacao[produto_usina][horas_D14[idx_hora]]
                        + (1 - lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]))*BIG_M,
                    f"rest_1a_prodSemIncorpAcum_{produto_usina}_{horas_D14[idx_hora]}",
                )

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] >=
                        massa_pelot_anterior(produto_usina, idx_hora)
                        + varProducaoSemIncorporacao[produto_usina][horas_D14[idx_hora]]
                        - (1 - lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]))*BIG_M,
                    f"rest_1b_prodSemIncorp_{produto_usina}_{horas_D14[idx_hora]}",
                )

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] <=
                    lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc])*BIG_M,
                    f"rest_1c_prodSemIncorp_{produto_usina}_{horas_D14[idx_hora]}",
                )

        for produto_usina in produtos_usina:
            for hora in horas_D14:
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][hora] >=
                        parametros['limites_campanhas'][produto_usina]['min'] -
                        (1 - varFimCampanhaPelot[produto_usina][hora])*BIG_M,
                        f"rest_limiteMinCampanhaPelot_{produto_usina}_{hora}",
                )
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][hora] <=
                        parametros['limites_campanhas'][produto_usina]['max'],
                        f"rest_limiteMaxCampanhaPelot_{produto_usina}_{hora}",
                )

        # Restrições para calcular a janela da produção sem incorporação acumulada na pelotização, por produto, por hora

        def janela_pelot_anterior(produto_usina, idx_hora):
            if idx_hora > 0:
                return varJanelaProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora-1]]
            else:
                return parametros['janelas_campanhas'][produto_usina]['acum']

        for produto_usina in produtos_usina:

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] <=
                        janela_pelot_anterior(produto_usina, idx_hora)
                        + 1
                        + (1 - lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]))*BIG_M,
                    f"rest_1a_janelaProdSemIncorpAcum_{produto_usina}_{horas_D14[idx_hora]}",

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] >=
                        janela_pelot_anterior(produto_usina, idx_hora)
                        + 1
                        - (1 - lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]))*BIG_M,
                    f"rest_1b_janelaProdSemIncorpAcum_{produto_usina}_{horas_D14[idx_hora]}",
                )

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] <=
                    lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc])*BIG_M,
                    f"rest_1c_janelaProdSemIncorpAcum_{produto_usina}_{horas_D14[idx_hora]}",
                )

        # Restrições para garantir que as campanhas de produto no concentrador respeitam os
        # limites mínimos e máximos de massa

        for produto_usina in produtos_usina:
            for hora in horas_D14:
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][hora] >=
                        parametros['janelas_campanhas'][produto_usina]['min'] -
                        (1 - varFimCampanhaPelot[produto_usina][hora])*BIG_M,
                        f"rest_limiteMinJanelaCampanhaPelot_{produto_usina}_{hora}",
                )
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][hora] <=
                        parametros['janelas_campanhas'][produto_usina]['max'],
                        f"rest_limiteMaxJanelaCampanhaPelot_{produto_usina}_{hora}",
                )

        # Indica o estoque de polpa em Ubu, por hora
        varEstoquePolpaUbu = LpVariable.dicts("Ubu_Estoque_Polpa", (produtos_conc, horas_D14),
                                            parametros['capacidades']['TQ_UBU']['min'], parametros['capacidades']['TQ_UBU']['max'],
                                            LpContinuous)

        varVolumePraca  = LpVariable.dicts("Praca_Ubu_Filtragem", (produtos_conc, horas_D14), 0, parametros['config']['taxa_max_envio_praca'], LpContinuous)
        varEstoquePraca = LpVariable.dicts("Praca_Ubu_Estoque_Acumul_(ignorado)", (produtos_conc, horas_D14),
                                        parametros['capacidades']['praca_Usina']['min'], parametros['capacidades']['praca_Usina']['max'],
                                        LpContinuous)

        varRetornoPraca = LpVariable.dicts("Praca_Ubu_Retorno", (produtos_conc, horas_D14),
                                        parametros['capacidades']['Taxa_Retorno_Praca_Usina']['min'],
                                        parametros['capacidades']['Taxa_Retorno_Praca_Usina']['max'],
                                        LpContinuous)
        varEstoqueRetornoPraca = LpVariable.dicts("Praca_Ubu_Estoque_Acumul_Previamente_(pode_usar)",
                                                (produtos_conc, horas_D14), parametros['capacidades']['praca_Usina']['min'], parametros['capacidades']['praca_Usina']['max'], LpContinuous)

        varLiberaVolumePraca = LpVariable.dicts("Praca_Ubu_Libera_Transf_Estoque", (horas_D14), 0, 1, LpInteger)

        # Define o estoque de polpa em Ubu da segunda hora em diante
        for produto in produtos_conc:
            for i in range(1, len(horas_D14)):
                modelo += (
                    varEstoquePolpaUbu[produto][horas_D14[i]] == varEstoquePolpaUbu[produto][horas_D14[i-1]]
                                                                + varPolpaUbu[produto][horas_D14[i]] *
                                                                    parametros['config']['perc_solidos'] *
                                                                    parametros['config']['densidade']
                                                                - lpSum(varProducaoUbu[produto][produto_u][horas_D14[i]]
                                                                        for produto_u in produtos_usina)
                                                                - varVolumePraca[produto][horas_D14[i]]
                                                                + varRetornoPraca[produto][horas_D14[i]],
                    f"rest_define_EstoquePolpaUbu_{produto}_{horas_D14[i]}",
                )
            # Define o estoque de polpa em Ubu da primeira hora
            modelo += (
                varEstoquePolpaUbu[produto][horas_D14[0]] == parametros['estoque_inicial']['TQ_UBU'][produto]  +
                                                    varPolpaUbu[produto][horas_D14[0]] *
                                                        parametros['config']['perc_solidos'] *
                                                        parametros['config']['densidade']
                                                    - lpSum(varProducaoUbu[produto][produto_u][horas_D14[0]]
                                                            for produto_u in produtos_usina)
                                                    - varVolumePraca[produto][horas_D14[0]]
                                                    + varRetornoPraca[produto][horas_D14[0]],
                f"rest_define_EstoquePolpaUbu_{produto}_{horas_D14[0]}",
            )

        # Trata a taxa máxima de transferência (retorno) de material do pátio para a usina
        for hora in horas_D14:
            modelo += (
                lpSum(varRetornoPraca[produto][hora] for produto in produtos_conc) <= parametros['capacidades']['Taxa_Retorno_Praca_Usina']['max'],
                f"rest_define_taxa_retorno_praca_Pelot_{hora}",
            )

        #limita o estoque total dos produtos
        for hora in horas_D14:
            modelo += (
                lpSum(varEstoquePolpaUbu[produto][hora]
                    for produto in produtos_conc) <= parametros['capacidades']['TQ_UBU']['max'],
                f"rest_define_limite_estoque_polpa_{hora}",
            )

        # Define o estoque do pátio da usina, que pode (não pode mais) retornar ou virar pellet feed
        for i in range(1, len(horas_D14)):
            for produto in produtos_conc:
                modelo += (
                    varEstoquePraca[produto][horas_D14[i]] == varEstoquePraca[produto][horas_D14[i-1]]
                                                                + varVolumePraca[produto][horas_D14[i]]
                                                                # - varRetornoPatio[produto][horas_D14[i]],
                                                                ,
                    f"rest_define_EstoquePatio_{produto}_{horas_D14[i]}",
                )

        # Define o estoque do pátio da usina da primeira hora
        for produto in produtos_conc:
            modelo += (
                varEstoquePraca[produto][horas_D14[0]] == 0
                                                + varVolumePraca[produto][horas_D14[0]]
                                                # - varRetornoPatio[produto][horas_D14[0]],
                                                ,
                f"rest_define_EstoquePatio_{produto}_{horas_D14[0]}",
            )

        # Define o estoque do pátio de retorno da usina, que pode retornar ou virar pellet feed
        for i in range(1, len(horas_D14)):
            for produto in produtos_conc:
                modelo += (
                    varEstoqueRetornoPraca[produto][horas_D14[i]] ==
                                                        varEstoqueRetornoPraca[produto][horas_D14[i-1]]
                                                        # + varVolumePatio[produto][horas_D14[i]]
                                                        - varRetornoPraca[produto][horas_D14[i]]
                                                        ,
                    f"rest_define_EstoqueRetornoPatio_{produto}_{horas_D14[i]}",
                )
        # Define o estoque do pátio de retorno da usina da primeira hora
        for produto in produtos_conc:
            modelo += (
                varEstoqueRetornoPraca[produto][horas_D14[0]] == parametros['estoque_inicial']['praca_Usina'][produto]
                                                        - varRetornoPraca[produto][horas_D14[0]]
                                                        ,
                f"rest_define_EstoqueRetornoPatio_{produto}_{horas_D14[0]}",
            )

        #
        for i in range(1, len(horas_D14)):
            modelo += (
                lpSum(varVolumePraca[produto][horas_D14[i]]
                    for produto in produtos_conc)
                <=  parametros['config']['taxa_max_envio_praca'] * varLiberaVolumePraca[horas_D14[i]],
                f"rest_define_taxa_tranferencia_para_patio_{horas_D14[i]}",
            )

        # Restricao de controle de transferencia para estoque de patio
        for i in range(1, len(horas_D14)):
            modelo += (
                lpSum(varEstoquePolpaUbu[produto][horas_D14[i]]
                    for produto in produtos_conc)
                - parametros['config']['limite_perc_envio_praca']*parametros['capacidades']['TQ_UBU']['max']
                <= BIG_M * varLiberaVolumePraca[horas_D14[i]],
                f"rest_define_liberacao_tranferencia_para_pataio_{horas_D14[i]}",
            )

        for i in range(1, len(horas_D14)):
            modelo += (
                parametros['config']['limite_perc_envio_praca']*parametros['capacidades']['TQ_UBU']['max']
                - lpSum(varEstoquePolpaUbu[produto][horas_D14[i]]
                        for produto in produtos_conc)
                <= BIG_M * (1-varLiberaVolumePraca[horas_D14[i]]),
                f"rest_define_tranferencia_para_patio_{horas_D14[i]}",
            )

        logger.info('[OK]')

        logger.info('Definindo variáveis e restrições dos Navios')

        # Indica, para cada navio, se é a hora que inicia o carregamento
        varInicioCarregNavio = LpVariable.dicts("Porto_Inicio_Carregamento", (navios, horas_D14), 0, 1, LpInteger)

        # Indica, para cada navio, em que data começa o carregamento
        varDataInicioCarregNavio = LpVariable.dicts("Porto_Data_Carregamento", (navios), 0, None, LpContinuous)

        # Indica o estoque de produto no pátio de Ubu, por hora
        varEstoqueProdutoPatio = LpVariable.dicts("Porto_Estoque_Patio", (produtos_usina, horas_D14),
                                                parametros['capacidades']['Patio_Porto']['min'], parametros['capacidades']['Patio_Porto']['max'],
                                                LpContinuous)

        for navio in navios:
            for idx_hora in range(len(horas_D14)):
                modelo += (
                    (varInicioCarregNavio[navio][horas_D14[idx_hora]] +
                    lpSum(varInicioCarregNavio[navio_j][horas_D14[s]]
                            for navio_j in navios
                                for s in range(idx_hora, min(idx_hora+math.ceil(parametros['navios'][navio]['Carga']/parametros['navios'][navio]['Taxa']), len(horas_D14)))
                                    if navio_j != navio)
                    ) <= parametros['config']['capacidade_carreg_porto'],
                    f"rest_Producao1_{navio}_{horas_D14[idx_hora]}",
                )

        # Restrições para garantir que cada navio até D14 começa o carregamento uma única vez
        for navio in navios_ate_d14:
            modelo += (
                lpSum([varInicioCarregNavio[navio][hora] for hora in horas_D14]) == 1,
                f"rest_define_InicioCarregNavio_{navio}",
            )

        for navio in navios:
            if not navio in navios_ate_d14:
                modelo += (
                    lpSum([varInicioCarregNavio[navio][hora] for hora in horas_D14]) == 0,
                    f"rest_define_InicioCarregNavio_{navio}",
                )

        # Restrições para garantir consistência do carregamento
        for navio in navios:
            modelo += (
                varDataInicioCarregNavio[navio] >=
                    lpSum([idx_hora*varInicioCarregNavio[navio][horas_D14[idx_hora]]
                        for idx_hora in range(len(horas_D14))]),
                f"rest_consistencia_DataInicioCarregNavio_{navio}",
            )

        # Restrições para garantir que carregamento só começa após navio chegar
        for navio in navios_ate_d14:
            modelo += (
            lpSum([idx_hora*varInicioCarregNavio[navio][horas_D14[idx_hora]] for idx_hora in range(len(horas_D14))]) >= extrair_hora(parametros['navios'][navio]['Data_chegada']),
                f"rest_limita_DataInicioCarregNavio_{navio}",
            )

        # Define o estoque de produto no pátio de Ubu da segunda hora em diante
        for produto in produtos_usina:
            for idx_hora in range(1, len(horas_D14)):
                modelo += (
                    varEstoqueProdutoPatio[produto][horas_D14[idx_hora]]
                        == varEstoqueProdutoPatio[produto][horas_D14[idx_hora-1]] +
                            varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] -
                            lpSum([varInicioCarregNavio[navio][horas_D14[idx_hora_s]] *
                                parametros['navios'][navio]['Taxa'] *
                                produtos_de_cada_navio[navio][produto]
                                    for navio in navios
                                        for idx_hora_s in range(max(idx_hora-math.ceil(parametros['navios'][navio]['Carga']/parametros['navios'][navio]['Taxa'])+1,1), idx_hora+1)]),
                    f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[idx_hora]}",
                )
            # Define o estoque de produto no pátio de Ubu do primeiro dia
            modelo += (
                varEstoqueProdutoPatio[produto][horas_D14[0]]
                    == parametros['estoque_inicial']['Patio_Porto'][produto] +
                    varProducaoSemIncorporacao[produto][horas_D14[0]] -
                    lpSum([varInicioCarregNavio[navio][horas_D14[0]] *
                            parametros['navios'][navio]['Taxa'] *
                            produtos_de_cada_navio[navio][produto]
                            for navio in navios]),
                f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[0]}",
            )

        varVolumeAtrasadoNavio = LpVariable.dicts("Porto_Volume_Atrasado_Navios", (navios_ate_d14), 0, None, LpContinuous)

        for navio in navios_ate_d14:
            modelo += (
                varVolumeAtrasadoNavio[navio] ==
                    (varDataInicioCarregNavio[navio] - extrair_hora(parametros['navios'][navio]['Data_chegada'])) *
                    parametros['navios'][navio]['Taxa'],
                f"rest_define_VolumeAtrasadoNavio_{navio}",
            )

        logger.info('[OK]')

        w_teste = LpVariable.dicts("w_teste", (produtos_conc, horas_D14), 0, 1, LpInteger)
        Fixadas = LpVariable.dicts("fixadas", (produtos_conc, horas_D14), 0, 1, LpInteger)

        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (w_teste[produto][hora] >= 0,  f"teste7_{produto}_{hora}")
                modelo += (Fixadas[produto][hora] >= 0,  f"teste8_{produto}_{hora}")

        # -----------------------------------------------------------------------------

        logger.info('Definindo a Função Objetivo')

        funcao_objetivo = [fo.strip() for fo in args.funcao_objetivo[1:-1].split(',')]

        for fo in funcao_objetivo:
            if not fo in ['max_brit', 'min_atr_nav', 'max_conc', 'max_pelot', 'max_bombEB07']:
                raise Exception(f"Função objetivo {fo} não implementada!")

        # Definindo a função objetivo
        fo = 0
        if 'min_atr_nav' in funcao_objetivo:
            fo += - (lpSum([varVolumeAtrasadoNavio[navio] for navio in navios_ate_d14]))
        if 'max_brit' in funcao_objetivo:
            fo += lpSum([varTaxaBritagem[produto_mina][hora] for produto_mina in produtos_mina for hora in horas_D14])
        if 'max_conc' in funcao_objetivo:
            fo += lpSum([varTaxaAlim[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
        if 'max_pelot' in funcao_objetivo:
            fo += lpSum([varProducaoSemIncorporacao[produto_usina][hora] for produto_usina in produtos_usina for hora in horas_D14])
        if 'max_bombEB07' in funcao_objetivo:
            fo += lpSum([varBombeadoEB07[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])

        modelo += (fo, "FO",)
        solver.solve(modelo)
