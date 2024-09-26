from pulp import *
import json
import csv
import pandas as pd
import matplotlib.pyplot as plt
import math


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


    def modelo(self, cenario, solver, data, varBombeamentoPolpaPPO, horizon):
        # variaveis utilizadas no modelo
        if horizon != 0:
            horas_D14 = data['horas_D14'][:horizon]
        else:
            horas_D14 = data['horas_D14']
        produtos_conc = data['produtos_conc']
        de_para_produtos_mina_conc = data['de_para_produtos_mina_conc']
        min_estoque_pulmao_concentrador = data['min_estoque_pulmao_concentrador']
        max_estoque_pulmao_concentrador = data['max_estoque_pulmao_concentrador']
        numero_faixas_producao = data['numero_faixas_producao']
        max_taxa_alimentacao = data['max_taxa_alimentacao']
        taxa_producao_britagem = data['taxa_producao_britagem']
        produtos_britagem = data['produtos_britagem']
        produtos_mina = data['produtos_mina']
        faixas_producao_concentrador = data['faixas_producao_concentrador']
        estoque_pulmao_inicial_concentrador = data['estoque_pulmao_inicial_concentrador']
        parametros_calculados = data['parametros_calculados']
        fatorGeracaoLama = data['fatorGeracaoLama']
        parametros_mineroduto_ubu = data['parametros_mineroduto_ubu']
        estoque_eb06_d0 = data['estoque_eb06_d0']
        vazao_bombas = data['vazao_bombas']
        produtos_conc = data['produtos_conc']
        parametros_calculados = data['parametros_calculados']
        max_producao_sem_incorporacao = data['max_producao_sem_incorporacao']
        produtos_usina = data['produtos_usina']
        de_para_produtos_conc_usina = data['de_para_produtos_conc_usina']
        min_estoque_polpa_ubu = data['min_estoque_polpa_ubu']
        max_estoque_polpa_ubu = data['max_estoque_polpa_ubu']
        max_taxa_envio_patio = data['max_taxa_envio_patio']
        max_taxa_retorno_patio_usina = data['max_taxa_retorno_patio_usina']
        min_estoque_patio_usina = data['min_estoque_patio_usina']
        max_estoque_patio_usina = data['max_estoque_patio_usina']
        max_capacidade_eb06 = data['max_capacidade_eb06']
        estoque_polpa_ubu = data['estoque_polpa_ubu']
        estoque_inicial_patio_usina = data['estoque_inicial_patio_usina']
        fator_limite_excesso_patio = data['fator_limite_excesso_patio']
        dias = data['dias']
        args = data['args']
        DF = data['DF']
        UD = data['UD']
        RP = data['RP']
        umidade = data['umidade']
        dif_balanco = data['dif_balanco']
        perc_solidos = data['perc_solidos']
        densidade = data['densidade']
        fator_conversao = data['fator_conv']
        prod_minima_usina = data['min_producao_produtos_ubu']
        PolpaLi = data['PolpaLi']
        PolpaLs = data['PolpaLs']
        AguaLi = data['AguaLi']
        AguaLs = data['AguaLs']
        capacidade_patio_porto_min = data['capacidade_patio_porto_min']
        capacidade_patio_porto_max = data['capacidade_patio_porto_max']
        capacidade_carreg_porto_por_dia = data['capacidade_carreg_porto_por_dia']
        taxa_carreg_navios = data['taxa_carreg_navios']
        carga_navios = data['carga_navios']
        estoque_produto_patio = data['estoque_produto_patio']
        janelas_campanhas_min = data['janelas_campanhas_min']
        janelas_campanhas_max = data['janelas_campanhas_max']
        janelas_campanha_acum = data['janelas_campanha_acum']
        limites_campanhas_min = data['limites_campanhas_min']
        limites_campanhas_max = data['limites_campanhas_max']
        limites_campanhas_acum = data['limites_campanhas_acum']
        bomb_polpa_acum_semana_anterior = data['bomb_polpa_acum_semana_anterior']
        bomb_agua_acum_semana_anterior = data['bomb_agua_acum_semana_anterior']
        data_chegada_navio = data['data_chegada_navio']
        navios = data['navios']
        navios_horizonte = data['navios_horizonte']
        produtos_navio = data['produtos_navio']


        BIG_M = 10e6
        BIG_M_MINERODUTO = 10e3
        modelo = LpProblem("Plano Semanal", LpMaximize)

        # Variável para definir a taxa de produção da britagem, por produto da mina, por hora
        varTaxaBritagem = LpVariable.dicts("Taxa Britagem", (produtos_mina, horas_D14), 0, None, LpContinuous)

        # Variável para definir o estoque pulmão pré-concentrador, por produto da mina, por hora
        varEstoquePulmaoConcentrador = LpVariable.dicts("Estoque Pulmao Concentrador", (produtos_mina, horas_D14), min_estoque_pulmao_concentrador, max_estoque_pulmao_concentrador, LpContinuous)

        # Variável que indica o produto que está sendo entregue pelo concentrador, por hora
        varProdutoConcentrador = LpVariable.dicts("Produto Concentrador", (produtos_mina, produtos_conc, horas_D14),  0, 1, LpInteger)


        varFimCampanhaConcentrador = LpVariable.dicts("Concentrador_FimCampanha", (produtos_conc, horas_D14),  0, 1, LpInteger)

        varTaxaAlimProdMinaConc = LpVariable.dicts("Concentrador_Taxa_Alimentacao_ConversaoProdutos", (produtos_mina, produtos_conc, horas_D14),
                                        0, max_taxa_alimentacao,
                                        LpContinuous)

        varTaxaAlimAcumulada = LpVariable.dicts("Concentrador_Taxa_Alimentacao_Acumulada",
                                        (produtos_conc, horas_D14),
                                        0, None,
                                        LpContinuous)
        
        varJanelaAlimAcumulada = LpVariable.dicts("Concentrador_Janela_Alimentacao_Acumulada",
                                            (produtos_conc, horas_D14),
                                            0, None,
                                            LpInteger)

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
                    varTaxaBritagem[produto][hora] <= math.floor(taxa_producao_britagem[self.extrair_dia(hora)]*produtos_britagem[produto][hora]),
                    f"rest_TaxaBritagem_{produto}_{hora}"
                )

        # Restrição para tratar o de-para de produtos da mina e do concentrador
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
        for hora in horas_D14:
            modelo += (
                lpSum([varProdutoConcentrador[produto_mina][produto_conc][hora] for produto_mina in produtos_mina for produto_conc in produtos_conc]) <= 1,
                f"rest_UmProdutoConcentrador_{hora}"
            )

        #CAMPANHAS COMECA AQUI

        def produto_concentrador_anterior(produto_conc, idx_hora):
            if idx_hora > 0:
                return lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora-1]] for produto_mina in produtos_mina])
            elif limites_campanhas_acum[produto_conc] > 0:
                return 1
            else:
                return 0
    
        for produto_conc in produtos_conc:
            # Y_t-1? >= X_t - X_t-1
            # Y_t-1? <= 2 - X_t - X_t-1
            # Y_t-1? <= X_t * M

            # Z_t-1 >= X_t-1 - X_t
            # Z_t-1 <= 2 - X_t - X_t-1
            # Z_t-1 <= X_t-1 * M
            # Z_H'-1 = 0
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

        def massa_concentrador_anterior(produto_conc, idx_hora):
            if idx_hora > 0:
                return varTaxaAlimAcumulada[produto_conc][horas_D14[idx_hora-1]]
            else:
                return limites_campanhas_acum[produto_conc]

        for produto_conc in produtos_conc:

            # subject to Producao1a{t in 2..H}: #maximo de 1s
            #    Tac[t] <= Tac[t-1] + T[t] + (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][horas_D14[idx_hora]] <= 
                        massa_concentrador_anterior(produto_conc, idx_hora) 
                        + varTaxaAlim[produto_conc][horas_D14[idx_hora]] 
                        + (1 - lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]))*BIG_M,
                    f"rest_1a_taxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

            # subject to Producao1b{t in 2..H}: #maximo de 1s
            #    Tac[t] >= Tac[t-1] + T[t] - (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][horas_D14[idx_hora]] >=
                        massa_concentrador_anterior(produto_conc, idx_hora) 
                        + varTaxaAlim[produto_conc][horas_D14[idx_hora]]
                        - (1 - lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]))*BIG_M,
                    f"rest_1b_taxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

            # subject to Producao1c{t in 2..H}: #maximo de 1s
            #    Tac[t] <= X[t]*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][horas_D14[idx_hora]] <= 
                    lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina])*BIG_M,
                    f"rest_1c_taxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

        # Restrições para garantir que as campanhas de produto no concentrador respeitam os
        # limites mínimos e máximos de massa
        
        for produto_conc in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][hora] >= 
                        limites_campanhas_min[produto_conc] -
                        (1 - varFimCampanhaConcentrador[produto_conc][hora])*BIG_M,
                        f"rest_limiteMinCampanhaConcentrador_{produto_conc}_{hora}",
                )
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][hora] <= 
                        limites_campanhas_max[produto_conc],
                        f"rest_limiteMaxCampanhaConcentrador_{produto_conc}_{hora}",
                )

        # Restrições para calcular a janela da taxa de alimentação acumulada no concentrador, por produto, por hora
                
        def janela_concentrador_anterior(produto_conc, idx_hora):
            if idx_hora > 0:
                return varJanelaAlimAcumulada[produto_conc][horas_D14[idx_hora-1]]
            else:
                return janelas_campanha_acum[produto_conc]

        for produto_conc in produtos_conc:

            # subject to Producao1a{t in 2..H}: #maximo de 1s
            #    Tac[t] <= Tac[t-1] + 1 + (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaAlimAcumulada[produto_conc][horas_D14[idx_hora]] <= 
                        janela_concentrador_anterior(produto_conc, idx_hora) 
                        + 1 
                        + (1 - lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]))*BIG_M,
                    f"rest_1a_janelaTaxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

            # subject to Producao1b{t in 2..H}: #maximo de 1s
            #    Tac[t] >= Tac[t-1] + 1 - (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaAlimAcumulada[produto_conc][horas_D14[idx_hora]] >=
                        janela_concentrador_anterior(produto_conc, idx_hora) 
                        + 1
                        - (1 - lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]))*BIG_M,
                    f"rest_1b_janelaTaxaAcum_{produto_conc}_{horas_D14[idx_hora]}",
                )

            # subject to Producao1c{t in 2..H}: #maximo de 1s
            #    Tac[t] <= X[t]*M;

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
                        janelas_campanhas_min -
                        (1 - varFimCampanhaConcentrador[produto_conc][hora])*BIG_M,
                        f"rest_limiteMinJanelaCampanhaConcentrador_{produto_conc}_{hora}",
                )
                modelo += (
                    varJanelaAlimAcumulada[produto_conc][hora] <= 
                        janelas_campanhas_max,
                        f"rest_limiteMaxJanelaCampanhaConcentrador_{produto_conc}_{hora}",
                )

        #CAMPANHAS TERMINA AQUI
        # Restrição para amarrar a taxa de alimentação do concentrador ao único produto produzido por vez
        for produto_mina in produtos_mina:
            for produto_conc in produtos_conc:
                for hora in horas_D14:
                    modelo += (
                        varTaxaAlimProdMinaConc[produto_mina][produto_conc][hora] <= BIG_M*varProdutoConcentrador[produto_mina][produto_conc][hora],
                        f"rest_amarra_taxaAlimProdMinaConc_varProdConc_{produto_mina}_{produto_conc}_{hora}",
                    )

        # # Amarra taxa de alimentação com as faixas de produção do concentrador
        # for produto_mina in produtos_mina:
        #     for produto_conc in produtos_conc:
        #         for hora in horas_D14:
        #             modelo += (
        #                 varTaxaAlimProdMinaConc[produto_mina][produto_conc][hora]
        #                     == faixas_producao_concentrador*varNivelTaxaAlim[produto_mina][produto_conc][hora],
        #                 f"rest_FaixasProducaoConcentrador_{produto_mina}_{produto_conc}_{hora}",
        #             )
        #             modelo += (
        #                 varNivelTaxaAlim[produto_mina][produto_conc][hora]
        #                     <= BIG_M*lpSum(varProdutoConcentrador[produto_mina][produto_conc][hora] for produto_mina in produtos_mina),
        #                 f"rest_TaxaAlimPorProduto_{produto_mina}_{produto_conc}_{hora}",
        #             )

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

        # Puxada, por dia, é calculada a partir da taxa de alimentação e demais parâmetros
        varPuxada = LpVariable.dicts("Puxada - C3 - Prog", (horas_D14), 0, None, LpContinuous)
        for hora in horas_D14:
            modelo += (
                varPuxada[hora] == lpSum([varTaxaAlim[produto][hora] for produto in produtos_conc])*
                                    DF[self.extrair_dia(hora)] *
                                    UD[self.extrair_dia(hora)] *
                                    (1-umidade[self.extrair_dia(hora)]),
                f"rest_define_Puxada_{hora}",
            )

        # Produção, por produto do concentrador, por dia, é calculada a partir da taxa de alimentação e demais parâmetros
        varProducao = LpVariable.dicts("Producao - C3 - Prog", (produtos_conc, horas_D14), 0, None, LpContinuous)
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varProducao[produto][hora]
                        == varTaxaAlim[produto][hora] *
                            (1-umidade[self.extrair_dia(hora)])  *
                            RP[self.extrair_dia(hora)]/100 * 
                            DF[self.extrair_dia(hora)] *
                            (1 - dif_balanco[self.extrair_dia(hora)]),
                    f"rest_define_Producao_{produto}_{hora}",
                )

        # Produção Volume, por hora, é calculada a partir produção volume
        varProducaoVolume = LpVariable.dicts("Producao volume/hora - C3 - Prog", (produtos_conc, horas_D14), 0, None, LpContinuous)
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varProducaoVolume[produto][hora]
                        == varProducao[produto][hora] * (1/perc_solidos[self.extrair_dia(hora)])
                                                    * (1/densidade[self.extrair_dia(hora)]),
                    f"rest_define_ProducaoVolume_{produto}_{hora}",
                )

        # Geração de Lama, por dia, é calculada a partir da puxada
        varGeracaoLama = LpVariable.dicts("Geracao de lama - C3 - Prog", (horas_D14), 0, None, LpContinuous)
        for hora in horas_D14:
            modelo += (
                varGeracaoLama[hora] == (varPuxada[hora]*(1-fatorGeracaoLama)),
                f"rest_define_GeracaoLama_{hora}",
            )

        # Rejeito Arenoso, por dia, é calculado a partir da puxada, geração de lama e produção
        varRejeitoArenoso = LpVariable.dicts("Geracao de rejeito arenoso - C3 - Prog", (horas_D14), 0, None, LpContinuous)
        for hora in horas_D14:
            modelo += (
                varRejeitoArenoso[hora] == varPuxada[hora] - varGeracaoLama[hora] - lpSum(varProducao[produto][hora] for produto in produtos_conc),
                f"rest_define_RejeitoArenoso_{hora}",
            )

        # Indica o estoque EB06, por hora
        varEstoqueEB06 = LpVariable.dicts("Estoque EB06", (produtos_conc, horas_D14), 0, None, LpContinuous)

        # Indica se há bombeamento de polpa em cada hora
        varBombeamentoPolpa = LpVariable.dicts("Bombeamento Polpa", (produtos_conc, horas_D14), 0, 1, LpInteger)

        # Restrição de capacidade do estoque EB06
        for hora in horas_D14:
            modelo += (
                lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc)
                    <= max_capacidade_eb06,
                f"rest_capacidade_EstoqueEB06_{hora}",
            )


        #Define o valor de estoque de EB06, por produto, da segunda hora em diante
        for produto in produtos_conc:
            for i in range(1, len(horas_D14)):
                modelo += (
                    varEstoqueEB06[produto][horas_D14[i]]
                        == varEstoqueEB06[produto][horas_D14[i-1]]
                        + varProducaoVolume[produto][horas_D14[i]]
                        - varBombeamentoPolpa[produto][horas_D14[i]]*vazao_bombas,
                    f"rest_define_EstoqueEB06_{produto}_{horas_D14[i]}",
                )

        # Define o valor de estoque de EB06, por produto, da primeira hora
        for produto in produtos_conc:
            modelo += (
                varEstoqueEB06[produto][horas_D14[0]]
                    == estoque_eb06_d0[produto] +
                    varProducaoVolume[produto][horas_D14[0]] -
                    varBombeamentoPolpa[produto][horas_D14[0]]*vazao_bombas,
                f"rest_define_EstoqueEB06_{produto}_{horas_D14[0]}",
            )

        #garante um produto por vez
        for hora in horas_D14:
            modelo +=(
                lpSum(varBombeamentoPolpa[produto][hora] for produto in produtos_conc)  <= 1,
                f"rest_bombeamento_unico_produto_{hora}",
            )

        if varBombeamentoPolpaPPO:
            #garante fixação
            for produto in produtos_conc:
                for horas in horas_D14[0:len(horas_D14)]:
                    if varBombeamentoPolpaPPO[produto][horas] == 0 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
                        modelo += (varBombeamentoPolpa[produto][horas] <=0, f"rest_fixado2_{produto}_{horas}")
                    if varBombeamentoPolpaPPO[produto][horas] == 1 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
                        modelo += (varBombeamentoPolpa[produto][horas] >=1, f"rest_fixado2_{produto}_{horas}")
        else:
            # Restrição para garantir que apenas um produto é bombeado por vez
            for hora in horas_D14:
                modelo += (
                    lpSum(varBombeamentoPolpa[produto][hora] for produto in produtos_conc) <= 1,
                    f"rest_bombeamento_unico_produto_{produto}_{hora}",
                )
                def bombeamento_hora_anterior(produto, idx_hora):
                    return varBombeamentoPolpa[produto][horas_D14[idx_hora-1]]

            # Define o bombeamento de polpa para as horas de d01 a d14, respeitando as janelas mínimas de polpa e de água respectivamente
            for produto in produtos_conc:
                for i, hora in enumerate(horas_D14[0:-PolpaLi+1]):
                    if i == 0:
                        modelo += (
                            varBombeamentoPolpa[produto][horas_D14[i]] + 
                                lpSum([varBombeamentoPolpa[produto][horas_D14[j]] for j in range(i+1, i+PolpaLi)]) >=
                                    PolpaLi - PolpaLi*(1 - varBombeamentoPolpa[produto][horas_D14[i]]),
                            f"rest_janela_bombeamento_polpa_{produto}_0",
                    )
                    else:
                        modelo += (
                            varBombeamentoPolpa[produto][horas_D14[i]] + 
                                lpSum([varBombeamentoPolpa[produto][horas_D14[j]] for j in range(i+1, i+PolpaLi)]) >= PolpaLi
                                 - PolpaLi*(1 - varBombeamentoPolpa[produto][horas_D14[i]] + bombeamento_hora_anterior(produto, i)),
                            f"rest_janela_bombeamento_polpa_{produto}_{hora}",
                    )
                        
            for i, hora in enumerate(horas_D14[0:-AguaLi+1]):
                if i == 0:
                    modelo += (
                        lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc)+ 
                        lpSum([varBombeamentoPolpa[produto][horas_D14[j]] 
                                for produto in produtos_conc for j in range(i+1, i+AguaLi)]) <=
                            BIG_M*(1 + lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc)),
                        f"rest_janela_bombeamento_agua_{produto}_{hora}",
                    )
                else:
                    modelo += (
                        lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc)+ 
                        lpSum([varBombeamentoPolpa[produto][horas_D14[j]] 
                                for produto in produtos_conc for j in range(i+1, i+AguaLi)]) <=
                            BIG_M*(1 + lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc) 
                                    - lpSum(bombeamento_hora_anterior(produto, i) for produto in produtos_conc)),
                        f"rest_janela_bombeamento_agua_{produto}_{hora}",
                    )
            # Contabiliza o bombeamento acumulado de polpa - Xac
            varBombeamentoPolpaAcumulado = LpVariable.dicts("Mineroduto_Bombeamento_Polpa_Acumulado", (horas_D14), 0, len(horas_D14), LpInteger)

            # Indica o bombeamento final de polpa
            varBombeamentoPolpaFinal = LpVariable.dicts("Mineroduto_Bombeamento_Polpa_Final", (horas_D14), 0, len(horas_D14), LpInteger)

            def bombeamento_acumulado_polpa_hora_anterior(idx_hora):
                if idx_hora == 0:
                    # subject to Producao2f{t in 1..H}: #maximo de 1s
                    #    Xac[1] = 0;
                    return bomb_polpa_acum_semana_anterior
                else:
                    return varBombeamentoPolpaAcumulado[horas_D14[idx_hora-1]]

            # subject to Producao1a{t in 2..H}: #maximo de 1s
            #    Xac[t] <= Xac[t-1] + 1 + (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <= 
                        bombeamento_acumulado_polpa_hora_anterior(idx_hora) + 1 + 
                        (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M,
                    f"seq_bomb_1a_{horas_D14[idx_hora]}",
                )

            # subject to Producao1b{t in 2..H}: #maximo de 1s
            #    Xac[t] >= Xac[t-1] + 1 - (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] >=
                        bombeamento_acumulado_polpa_hora_anterior(idx_hora) + 1 - 
                        (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M,
                    f"seq_bomb_1b_{horas_D14[idx_hora]}",
                )

            # subject to Producao1c{t in 2..H}: #maximo de 1s
            #    Xac[t] <= X[t]*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <= lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)*BIG_M,
                    f"seq_bomb_1c_{horas_D14[idx_hora]}",
                )

        
            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= 
                        bombeamento_acumulado_polpa_hora_anterior(idx_hora) + 
                        (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)
                        + lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                    f"rest_seq_bomb_2a_{horas_D14[idx_hora]}",
                )

            # subject to Producao2b{t in 2..H}: #maximo de 1s
            #    Xf[t] >= Xac[t-1] - (1 - X[t-1] + X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoPolpaFinal[horas_D14[idx_hora]] >= 
                        bombeamento_acumulado_polpa_hora_anterior(idx_hora) -
                        (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc) 
                        + lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
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
                        (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                    f"rest_seq_bomb_2d_{horas_D14[idx_hora]}",
                )

            # subject to Producao2e{t in 1..H}: #maximo de 1s
            #    Xf[t] <= dmax;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= PolpaLs,
                    f"rest_seq_bomb_2e_{horas_D14[idx_hora]}",
                )

            # subject to Producao2ee{t in 1..H}: #maximo de 1s
            #    Xac[t] <= dmax;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <= PolpaLs,
                    f"rest_seq_bomb_2ee_{horas_D14[idx_hora]}",
                )
        
            varBombeamentoAguaAcumulado = LpVariable.dicts("Mineroduto_Bombeamento_Agua_Acumulado", (horas_D14), 0, len(horas_D14), LpInteger)
            varBombeamentoAguaFinal = LpVariable.dicts("Mineroduto_Bombeamento_Agua_Final", (horas_D14), 0, len(horas_D14), LpInteger)

            def bombeamento_acumulado_agua_hora_anterior(idx_hora):
                if idx_hora == 0:
                    # subject to Producao2f{t in 1..H}: #maximo de 1s
                    #    Xac[1] = 0;
                    return bomb_agua_acum_semana_anterior
                else:
                    return varBombeamentoAguaAcumulado[horas_D14[idx_hora-1]]

            # subject to Producao1a{t in 2..H}: #maximo de 1s
            #    Xac[t] <= Xac[t-1] + 1 + (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <= 
                        bombeamento_acumulado_agua_hora_anterior(idx_hora) + 1 + 
                        (1 - (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                    f"rest_seq_bomb_agua_1a_{horas_D14[idx_hora]}",
                )

            # subject to Producao1b{t in 2..H}: #maximo de 1s
            #    Xac[t] >= Xac[t-1] + 1 - (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoAguaAcumulado[horas_D14[idx_hora]] >=
                        bombeamento_acumulado_agua_hora_anterior(idx_hora) + 1 - 
                        (1 - (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                    f"rest_seq_bomb_agua_1b_{horas_D14[idx_hora]}",
                )

            # subject to Producao1c{t in 2..H}: #maximo de 1s
            #    Xac[t] <= X[t]*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <= 
                        (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                    f"rest_seq_bomb_agua_1c_{horas_D14[idx_hora]}",
                )

            # subject to Producao2a{t in 2..H}: #maximo de 1s
            #    Xf[t] <= Xac[t-1] + (1 - X[t-1] + X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoAguaFinal[horas_D14[idx_hora]] <= 
                        bombeamento_acumulado_agua_hora_anterior(idx_hora) + 
                        (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
                        + (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                    f"rest_seq_bomb_agua_2a_{horas_D14[idx_hora]}",
                )

            # subject to Producao2b{t in 2..H}: #maximo de 1s
            #    Xf[t] >= Xac[t-1] - (1 - X[t-1] + X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoAguaFinal[horas_D14[idx_hora]] >= 
                        bombeamento_acumulado_agua_hora_anterior(idx_hora) -
                        (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
                        + (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
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
                        (1 - (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                    f"rest_seq_bomb_agua_2d_{horas_D14[idx_hora]}",
                )

            # subject to Producao2e{t in 1..H}: #maximo de 1s
            #    Xf[t] <= dmax;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoAguaFinal[horas_D14[idx_hora]] <= AguaLs,
                    f"rest_seq_bomb_agua_2e_{horas_D14[idx_hora]}",
                )

            # subject to Producao2ee{t in 1..H}: #maximo de 1s
            #    Xac[t] <= dmax;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <= AguaLs,
                    f"rest_seq_bomb_agua_2ee_{horas_D14[idx_hora]}",
                )


        varBombeado = LpVariable.dicts("Bombeado", (produtos_conc, horas_D14), 0, None, LpContinuous)
        for idx_hora in (horas_D14):
            for produto in produtos_conc:
                # if varBombeamentoPolpa[produto][idx_hora] == 1:
                modelo += (
                    varBombeado[produto][idx_hora] == varBombeamentoPolpa[produto][idx_hora]*vazao_bombas,
                    f"rest_define_Bombeado_inicial_{produto}_{idx_hora}",
                )
                # else:
                #     modelo += (
                #         varBombeado[produto][horas_D14[idx_hora]] == 0,
                #         f"rest_define_Bombeado_inicial_{produto}_{horas_D14[idx_hora]}",
                #     )

        # Indica chegada de polpa em Ubu, por produto, por hora
        varPolpaUbu = LpVariable.dicts("Polpa Ubu ", (produtos_conc, horas_D14), 0, None, LpContinuous)

        # Define a chegada de polpa em Ubu
        for produto in produtos_conc:
            for i in range(0,len(horas_D14)):
                modelo += (
                    varPolpaUbu[produto][horas_D14[i]]
                        == varBombeado[produto][horas_D14[i]],
                        #+ parametros_mineroduto_ubu['Polpa Ubu (65Hs) - AJUSTE'][horas_Dm3_D14[i]],
                    f"rest_define_PolpaUbu_{produto}_{horas_D14[i]}",
                )

        # Indica a produção sem incorporação em Ubu, por dia
        varProducaoSemIncorporacao = LpVariable.dicts("Producao sem incorporacao", (produtos_usina, horas_D14), 0, max_producao_sem_incorporacao, LpContinuous)

        varFimCampanhaPelot = LpVariable.dicts("Pelot_FimCampanha", (produtos_usina, horas_D14),  0, 1, LpInteger)

        # Indica a produção em Ubu, por hora
        varProducaoUbu = LpVariable.dicts("Producao Ubu", (produtos_conc, produtos_usina, horas_D14), 0, None, LpContinuous)

        varProdutoPelot = LpVariable.dicts("Pelot_ConversaoProduto", (produtos_conc, produtos_usina, horas_D14),  0, 1, LpInteger)

        # Variável para definir a produção sem incorporação acumulada, por produto da pelotização, por hora
        varProdSemIncorpAcumulada = LpVariable.dicts("Pelot_Producao_sem_Incorporacao_Acumulada",
                                                (produtos_usina, horas_D14), 0, None, LpContinuous)

        # Variável para definir da janela de produção sem incorporação acumulada, por produto da pelotização, por hora
        varJanelaProdSemIncorpAcumulada = LpVariable.dicts("Pelot_Janela_Acumulada",
                                                (produtos_usina, horas_D14), 0, None, LpInteger)

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
                            varProducaoUbu[produto_c][produto_u][hora] == varProducaoSemIncorporacao[produto_u][hora]*(1+fator_conversao[self.extrair_dia(hora)]),
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

        for produto_c in produtos_conc:
            for produto_u in produtos_usina:
                for hora in horas_D14:
                    modelo += (
                        varProducaoUbu[produto_c][produto_u][hora] <= BIG_M*varProdutoPelot[produto_c][produto_u][hora],
                        f"rest_amarra_producaoUbu_varProdPelot_{produto_c}_{produto_u}_{hora}",
                    )

        def produto_pelot_anterior(produto_usina, idx_hora):
            if idx_hora > 0:
                return lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora-1]] for produto_conc in produtos_conc])
            elif limites_campanhas_acum[produto_usina] > 0:
                return 1
            else:
                return 0
        
        for produto_usina in produtos_usina:
            # Z_t-1 >= X_t-1 - X_t
            # Z_t-1 <= 2 - X_t - X_t-1
            # Z_t-1 <= X_t-1 * M
            # Z_H'-1 = 0
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
                return limites_campanhas_acum[produto_usina]

        for produto_usina in produtos_usina:

            # subject to Producao1a{t in 2..H}: #maximo de 1s
            #    Tac[t] <= Tac[t-1] + T[t] + (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] <= 
                        massa_pelot_anterior(produto_usina, idx_hora) 
                        + varProducaoSemIncorporacao[produto_usina][horas_D14[idx_hora]] 
                        + (1 - lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]))*BIG_M,
                    f"rest_1a_prodSemIncorpAcum_{produto_usina}_{horas_D14[idx_hora]}",
                )

            # subject to Producao1b{t in 2..H}: #maximo de 1s
            #    Tac[t] >= Tac[t-1] + T[t] - (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] >=
                        massa_pelot_anterior(produto_usina, idx_hora) 
                        + varProducaoSemIncorporacao[produto_usina][horas_D14[idx_hora]]
                        - (1 - lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]))*BIG_M,
                    f"rest_1b_prodSemIncorp_{produto_usina}_{horas_D14[idx_hora]}",
                )

            # subject to Producao1c{t in 2..H}: #maximo de 1s
            #    Tac[t] <= X[t]*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] <= 
                    lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc])*BIG_M,
                    f"rest_1c_prodSemIncorp_{produto_usina}_{horas_D14[idx_hora]}",
                )

        # Restrições para garantir que as campanhas de produto na pelotização respeitam os
        # limites mínimos e máximos de massa
        
        for produto_usina in produtos_usina:
            for hora in horas_D14:
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][hora] >= 
                        limites_campanhas_min[produto_usina] -
                        (1 - varFimCampanhaPelot[produto_usina][hora])*BIG_M,
                        f"rest_limiteMinCampanhaPelot_{produto_usina}_{hora}",
                )
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][hora] <= 
                        limites_campanhas_max[produto_usina],
                        f"rest_limiteMaxCampanhaPelot_{produto_usina}_{hora}",
                )

        # Restrições para calcular a janela da produção sem incorporação acumulada na pelotização, por produto, por hora
                
        def janela_pelot_anterior(produto_usina, idx_hora):
            if idx_hora > 0:
                return varJanelaProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora-1]]
            else:
                return janelas_campanha_acum[produto_usina]

        for produto_usina in produtos_usina:

            # subject to Producao1a{t in 2..H}: #maximo de 1s
            #    Tac[t] <= Tac[t-1] + 1 + (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] <= 
                        janela_pelot_anterior(produto_usina, idx_hora) 
                        + 1 
                        + (1 - lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]))*BIG_M,
                    f"rest_1a_janelaProdSemIncorpAcum_{produto_usina}_{horas_D14[idx_hora]}",
                )

            # subject to Producao1b{t in 2..H}: #maximo de 1s
            #    Tac[t] >= Tac[t-1] + 1 - (1- X[t])*M;

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] >=
                        janela_pelot_anterior(produto_usina, idx_hora) 
                        + 1
                        - (1 - lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]))*BIG_M,
                    f"rest_1b_janelaProdSemIncorpAcum_{produto_usina}_{horas_D14[idx_hora]}",
                )

            # subject to Producao1c{t in 2..H}: #maximo de 1s
            #    Tac[t] <= X[t]*M;

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
                        janelas_campanhas_min -
                        (1 - varFimCampanhaPelot[produto_usina][hora])*BIG_M,
                        f"rest_limiteMinJanelaCampanhaPelot_{produto_usina}_{hora}",
                )
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][hora] <= 
                        janelas_campanhas_max,
                        f"rest_limiteMaxJanelaCampanhaPelot_{produto_usina}_{hora}",
                )

        # Indica o estoque de polpa em Ubu, por hora
        varEstoquePolpaUbu = LpVariable.dicts("Estoque Polpa Ubu", (produtos_conc, horas_D14), min_estoque_polpa_ubu, max_estoque_polpa_ubu, LpContinuous)

        varVolumePatio  = LpVariable.dicts("Volume jogado no patio", (produtos_conc, horas_D14), 0, max_taxa_envio_patio, LpContinuous)
        varEstoquePatio = LpVariable.dicts("Estoque acumulado no patio (ignorado durante a semana)", (produtos_conc, horas_D14), 0, max_estoque_patio_usina, LpContinuous)

        varRetornoPatio = LpVariable.dicts("Retorno do patio para usina", (produtos_conc, horas_D14), 0, max_taxa_retorno_patio_usina, LpContinuous)
        varEstoqueRetornoPatio = LpVariable.dicts("Estoque acumulado previamente no patio (que pode ser usado durante a semana)",
                                                (produtos_conc, horas_D14), min_estoque_patio_usina, max_estoque_patio_usina, LpContinuous)

        varLiberaVolumePatio = LpVariable.dicts("Libera transferencia de estoque para o patio", (horas_D14), 0, 1, LpInteger)

        # Define o estoque de polpa em Ubu da segunda hora em diante
        for produto in produtos_conc:
            for i in range(1, len(horas_D14)):
                modelo += (
                    varEstoquePolpaUbu[produto][horas_D14[i]] == varEstoquePolpaUbu[produto][horas_D14[i-1]]
                                                                + varPolpaUbu[produto][horas_D14[i]] *
                                                                perc_solidos[self.extrair_dia(horas_D14[i])] *
                                                                densidade[self.extrair_dia(horas_D14[i])]
                                                                - lpSum(varProducaoUbu[produto][produto_u][horas_D14[i]]
                                                                        for produto_u in produtos_usina)
                                                                - varVolumePatio[produto][horas_D14[i]]
                                                                + varRetornoPatio[produto][horas_D14[i]],
                    f"rest_define_EstoquePolpaUbu_{produto}_{horas_D14[i]}",
                )
            # Define o estoque de polpa em Ubu da primeira hora
            modelo += (
                varEstoquePolpaUbu[produto][horas_D14[0]] == estoque_polpa_ubu[produto] +
                                                    varPolpaUbu[produto][horas_D14[0]] *
                                                    perc_solidos[self.extrair_dia(horas_D14[0])] *
                                                    densidade[self.extrair_dia(horas_D14[0])]
                                                    - lpSum(varProducaoUbu[produto][produto_u][horas_D14[0]]
                                                            for produto_u in produtos_usina)
                                                    - varVolumePatio[produto][horas_D14[0]]
                                                    + varRetornoPatio[produto][horas_D14[0]],
                f"rest_define_EstoquePolpaUbu_{produto}_{horas_D14[0]}",
            )

        # Trata a taxa máxima de transferência (retorno) de material do pátio para a usina
        for hora in horas_D14:
            modelo += (
                lpSum(varRetornoPatio[produto][hora] for produto in produtos_conc) <= max_taxa_retorno_patio_usina,
                f"rest_define_taxa_retorno_patio_usina_{hora}",
            )

        #limita o estoque total dos produtos
        for hora in horas_D14:
            modelo += (
                lpSum(varEstoquePolpaUbu[produto][hora]
                    for produto in produtos_conc) <= max_estoque_polpa_ubu
            )

        # Define o estoque do pátio da usina, que pode (não pode mais) retornar ou virar pellet feed
        for i in range(1, len(horas_D14)):
            for produto in produtos_conc:
                modelo += (
                    varEstoquePatio[produto][horas_D14[i]] == varEstoquePatio[produto][horas_D14[i-1]]
                                                                + varVolumePatio[produto][horas_D14[i]]
                                                                # - varRetornoPatio[produto][horas_D14[i]],
                                                                ,
                    f"rest_define_EstoquePatio_{produto}_{horas_D14[i]}",
                )

        # Define o estoque do pátio da usina da primeira hora
        for produto in produtos_conc:
            modelo += (
                varEstoquePatio[produto][horas_D14[0]] == 0
                                                + varVolumePatio[produto][horas_D14[0]]
                                                # - varRetornoPatio[produto][horas_D14[0]],
                                                ,
                f"rest_define_EstoquePatio_{produto}_{horas_D14[0]}",
            )


        # Define o estoque do pátio de retorno da usina, que pode retornar ou virar pellet feed
        for i in range(1, len(horas_D14)):
            for produto in produtos_conc:
                modelo += (
                    varEstoqueRetornoPatio[produto][horas_D14[i]] ==
                                                        varEstoqueRetornoPatio[produto][horas_D14[i-1]]
                                                        # + varVolumePatio[produto][horas_D14[i]]
                                                        - varRetornoPatio[produto][horas_D14[i]]
                                                        ,
                    f"rest_define_EstoqueRetornoPatio_{produto}_{horas_D14[i]}",
                )

        # Define o estoque do pátio de retorno da usina da primeira hora
        for produto in produtos_conc:
            modelo += (
                varEstoqueRetornoPatio[produto][horas_D14[0]] == estoque_inicial_patio_usina[produto]
                                                        # + lpSum(varVolumePatio[produto][horas_D14[0]]
                                                        #    for produto in produtos_conc)
                                                        - varRetornoPatio[produto][horas_D14[0]]
                                                        ,
                f"rest_define_EstoqueRetornoPatio_{produto}_{horas_D14[0]}",
            )

        for i in range(1, len(horas_D14)):
            modelo += (
                lpSum(varVolumePatio[produto][horas_D14[i]]
                    for produto in produtos_conc)
                <=  max_taxa_envio_patio * varLiberaVolumePatio[horas_D14[i]],
                f"rest_define_taxa_tranferencia_para_pataio_{horas_D14[i]}",
            )

        # Restricao de controle de transferencia para estoque de patio
        for i in range(1, len(horas_D14)):
            modelo += (
                lpSum(varEstoquePolpaUbu[produto][horas_D14[i]]
                    for produto in produtos_conc)
                - fator_limite_excesso_patio*max_estoque_polpa_ubu
                <= BIG_M * varLiberaVolumePatio[horas_D14[i]],
                f"rest_define_liberacao_tranferencia_para_pataio_{horas_D14[i]}",
            )

        for i in range(1, len(horas_D14)):
            modelo += (
                fator_limite_excesso_patio*max_estoque_polpa_ubu
                - lpSum(varEstoquePolpaUbu[produto][horas_D14[i]]
                        for produto in produtos_conc)
                <= BIG_M * (1-varLiberaVolumePatio[horas_D14[i]]),
                f"rest_define_tranferencia_para_patio_{horas_D14[i]}",
            )

        varCarregamentoNavio = LpVariable.dicts("Porto_Carregamento_Navio", (navios, horas_D14), 0, None, LpContinuous)

        # Indica, para cada navio, se é a hora que inicia o carregamento
        varInicioCarregNavio = LpVariable.dicts("Porto_Inicio_Carregamento", (navios, horas_D14), 0, 1, LpInteger)

        # Indica, para cada navio, se é a hora que terminou o carregamento
        varFimCarregNavio = LpVariable.dicts("Porto_Fim_Carregamento", (navios, horas_D14), 0, 1, LpInteger)

        # Indica, para cada navio, em que data começa o carregamento
        varDataInicioCarregNavio = LpVariable.dicts("Porto_Data_Carregamento", (navios), 0, len(horas_D14), LpContinuous)

        # Indica o estoque de produto no pátio de Ubu, por hora
        varEstoqueProdutoPatio = LpVariable.dicts("Porto_Estoque_Patio", (produtos_usina, horas_D14),
                                                capacidade_patio_porto_min, capacidade_patio_porto_max,
                                                LpContinuous)

        # Restrições para garantir que a capacidade do porto é respeitada
        for navio in navios:
            for idx_hora in range(len(horas_D14)):
                modelo += (
                    (varInicioCarregNavio[navio][horas_D14[idx_hora]] + 
                    lpSum(varInicioCarregNavio[navio_j][horas_D14[s]]
                            for navio_j in navios 
                                for s in range(idx_hora, min(idx_hora+math.ceil(carga_navios[navio]/taxa_carreg_navios[navio]), len(horas_D14)))
                                    if navio_j != navio)
                    ) <= capacidade_carreg_porto_por_dia,
                    f"rest_Producao1_{navio}_{horas_D14[idx_hora]}",
                )

        # Restrições para garantir que cada navio até D14 começa o carregamento no máximo uma vez
        for navio in navios_horizonte:
            modelo += (
                lpSum([varInicioCarregNavio[navio][hora] for hora in horas_D14]) <= 1,
                f"rest_define_InicioCarregNavio_{navio}",
            )

        # Restrições para garantir que os navios depois do D14 não começam a carregar na programação
        for navio in navios:
            if not navio in navios_horizonte:
                modelo += (
                    lpSum([varInicioCarregNavio[navio][hora] for hora in horas_D14]) == 0,
                    f"rest_define_InicioCarregNavio_{navio}",
                )
        
        print(horas_D14[idx_hora])

        # Para cada navio
        for navio in navios:
            # Calcula quantas horas são necessárias para carregar o navio, incluindo a última hora que pode carregar
            # uma quantidade menor que a taxa de carregamento (o resto que sobrou)
            horas_carregamento = math.ceil(carga_navios[navio]/taxa_carreg_navios[navio])

            # Nas primeiras horas (antes do tempo necessário para carregar o navio), o carregamento não pode ter terminado
            for idx_hora in range(0, horas_carregamento-1):
                modelo += (
                    varFimCarregNavio[navio][horas_D14[idx_hora]] == 0,
                    f"rest_define_FimCarregNavio_{navio}_{horas_D14[idx_hora]}",
                )
            # Nas horas seguintes, o carregamento só pode ter terminado se ele tiver começado horas_carregamento antes
            for idx_hora in range(horas_carregamento-1, len(horas_D14)):
                modelo += (
                    varFimCarregNavio[navio][horas_D14[idx_hora]] == 
                        varInicioCarregNavio[navio][horas_D14[idx_hora-horas_carregamento+1]],
                    f"rest_define_FimCarregNavio_{navio}_{horas_D14[idx_hora]}",
                )

        for navio in navios:
            horas_carregamento = carga_navios[navio]/taxa_carreg_navios[navio]
            horas_cheias_carregamento = math.ceil(horas_carregamento)
            carreg_por_hora    = taxa_carreg_navios[navio]
            carreg_ultima_hora = carreg_por_hora*(horas_carregamento - math.floor(horas_carregamento))
            if carreg_ultima_hora == 0: # Se não tem resto para a última hora, ela carrega a taxa cheia
                carreg_ultima_hora = carreg_por_hora

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varCarregamentoNavio[navio][horas_D14[idx_hora]] <= 
                        carreg_por_hora *
                        lpSum(varInicioCarregNavio[navio][horas_D14[s]]
                                for s in range(max(idx_hora-horas_cheias_carregamento+1, 0), idx_hora+1)),
                        f"rest_define_CarregamentoNavio_1_{navio}_{horas_D14[idx_hora]}",
                )
                modelo += (
                    varCarregamentoNavio[navio][horas_D14[idx_hora]] >= 
                        carreg_por_hora *
                        lpSum(varInicioCarregNavio[navio][horas_D14[s]]
                                for s in range(max(idx_hora-math.floor(horas_carregamento)+1,0), idx_hora+1)),
                        f"rest_define_CarregamentoNavio_2_{navio}_{horas_D14[idx_hora]}",
                )
                modelo += (
                    varCarregamentoNavio[navio][horas_D14[idx_hora]] >=
                        carreg_ultima_hora *
                        varFimCarregNavio[navio][horas_D14[idx_hora]],
                        f"rest_define_CarregamentoNavio_3_{navio}_{horas_D14[idx_hora]}",
                )
                modelo += (
                    varCarregamentoNavio[navio][horas_D14[idx_hora]] <=
                        carreg_ultima_hora + (1-varFimCarregNavio[navio][horas_D14[idx_hora]])*BIG_M,
                        f"rest_define_CarregamentoNavio_4_{navio}_{horas_D14[idx_hora]}",
                )

        # Restrições para garantir consistência do carregamento
        for navio in navios:
            modelo += (
                varDataInicioCarregNavio[navio] >= 
                    lpSum([idx_hora*varInicioCarregNavio[navio][horas_D14[idx_hora]]
                        for idx_hora in range(len(horas_D14))]) + 
                        varDataInicioCarregNavio[navio].upBound*(1 - lpSum([varInicioCarregNavio[navio][horas_D14[idx_hora]] for idx_hora in range(len(horas_D14))])),
                f"rest_consistencia_DataInicioCarregNavio_{navio}",
            )

        # Restrições para garantir que se o carregamento ocorrer, ele só começa após navio chegar
        for navio in navios_horizonte:
            modelo += (
                lpSum([idx_hora*varInicioCarregNavio[navio][horas_D14[idx_hora]] for idx_hora in range(len(horas_D14))]) 
                    >= data_chegada_navio[navio] - BIG_M*(1 - lpSum([varInicioCarregNavio[navio][horas_D14[idx_hora]] for idx_hora in range(len(horas_D14))])),
                    f"rest_limita_HoraInicioCarregNavio_{navio}",
            )

        # Define o estoque de produto no pátio de Ubu da segunda hora em diante
        for produto in produtos_usina:
            for idx_hora in range(1, len(horas_D14)):
                modelo += (
                    varEstoqueProdutoPatio[produto][horas_D14[idx_hora]] 
                        == varEstoqueProdutoPatio[produto][horas_D14[idx_hora-1]] + 
                            varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] -
                            lpSum(varCarregamentoNavio[navio][horas_D14[idx_hora]] * produtos_navio[navio][produto]
                                for navio in navios),
                    f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[idx_hora]}",
                )
            # Define o estoque de produto no pátio de Ubu da primeira hora
            modelo += (
                varEstoqueProdutoPatio[produto][horas_D14[0]] 
                    == estoque_produto_patio[produto] +
                    varProducaoSemIncorporacao[produto][horas_D14[0]] -
                    lpSum(varCarregamentoNavio[navio][horas_D14[0]] * produtos_navio[navio][produto]                               
                        for navio in navios),
                f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[0]}",
            )

        # Define o limite mínimo do pátio do porto ao final do horizonte de planejamento
        for produto in produtos_usina:
            modelo += (
                varEstoqueProdutoPatio[produto][horas_D14[-1]] >= produtos_navio[produto],
                f"rest_define_limite_minimo_final_EstoquePatio_{produto}",
            )

        varVolumeAtrasadoNavio = LpVariable.dicts("Porto_Volume_Atrasado_Navios", (navios_horizonte), 0, None, LpContinuous)

        for navio in navios_horizonte:
            modelo += (
                varVolumeAtrasadoNavio[navio] == 
                    (varDataInicioCarregNavio[navio] - data_chegada_navio[navio]) *
                    taxa_carreg_navios[navio],
                f"rest_define_VolumeAtrasadoNavio_{navio}",
            )

        menor_taxa_carregamento = min([taxa_carreg_navios for navio in navios_horizonte])

        # slack = pulp.LpVariable.dicts("Slack", produtos_usina, lowBound=0)
        
        # modelo += pulp.lpSum(slack[produto_u] for produto_u in produtos_usina)

        # for produto_u in produtos_usina:
        #     modelo += (
        #         lpSum(varProducaoSemIncorporacao[produto_u][hora] for hora in horas_D14) + slack[produto_u] >= prod_minima_usina[produto_u]
        #     )



        # for fo in cenario['geral']['funcao_objetivo']:
        #     if not fo in ['max_brit', 'min_atr_nav', 'max_conc', 'max_usina', 'max_est_polpa', 'max_pf', 'min_est_patio']:
        #         raise Exception(f"Função objetivo {fo} não implementada!")

        # Definindo a função objetivo
        fo = 0
        fo += - (lpSum([varVolumeAtrasadoNavio[navio]*(1/menor_taxa_carregamento) for navio in navios_horizonte]))
        # if 'max_conc' in cenario['geral']['funcao_objetivo']:
        # fo += lpSum([varTaxaAlim[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
        # if 'max_usina' in cenario['geral']['funcao_objetivo']:
        # fo += lpSum([varProducaoSemIncorporacao[produto_usina][hora] for produto_usina in produtos_usina for hora in horas_D14])
        # if 'max_brit' in cenario['geral']['funcao_objetivo']:
        #     fo += (lpSum([varTaxaBritagem[produto_mina][hora] for produto_mina in produtos_mina for hora in horas_D14]))

        modelo += (fo, "FO",)

        # The problem is solved using PuLP's choice of Solver
        solver.solve(modelo)
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
        with open(f'{args.pasta_saida}/{nome_arquivo_saida}', "w", encoding="utf8") as f:
            json.dump(resultados, f)
            # csv.writer(resultados)
        # with open(nome_arquivo_saida, 'w', newline='') as csvfile:
            # csvwriter = csv.writer(csvfile)

            # Escrever o cabeçalho do CSV
            # header = ['Variavel'] + [f'{hora}' for hora in horas_D14]
            # csvwriter.writerow(header)

            # # Escrever os valores das variáveis
            # for variavel in resultados['variaveis']:
            #     row = [variavel]
            #     for hora in horas_D14:
            #         valor = resultados[variavel]  # Se não houver valor, deixe em branco
            #         row.append(valor)
            #     csvwriter.writerow(row)
        return modelo.status, resultados
