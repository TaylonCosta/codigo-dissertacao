from pulp import *
import json
import time

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


    def modelo(self, cenario, solver, data, varBombeamentoPolpaPPO):
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
        vazao_bombas = data['vazao_bombas']
        produtos_conc = data['produtos_conc']
        parametros_calculados = data['parametros_calculados']
        max_producao_sem_incorporacao = data['max_producao_sem_incorporacao']
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
        min_producao_produtos_ubu = data['min_producao_produtos_ubu']
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
                        == varTaxaAlim[produto][hora]
                        * (1-parametros_mina['Umidade - C3'][self.extrair_dia(hora)])
                        * parametros_calculados['RP (Recuperação Mássica) - C3'][self.extrair_dia(hora)]
                        / 100 * parametros_mina['DF - C3'][self.extrair_dia(hora)]
                        * (1 - parametros_mina['Dif. de Balanço - C3'][self.extrair_dia(hora)] / 100),
                    f"rest_define_Producao_{produto}_{hora}",
                )

        # Produção Volume, por hora, é calculada a partir produção volume
        varProducaoVolume = LpVariable.dicts("Producao volume/hora - C3 - Prog", (produtos_conc, horas_D14), 0, None, LpContinuous)
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varProducaoVolume[produto][hora]
                        == varProducao[produto][hora]
                        * (1/parametros_calculados['% Sólidos - EB06'][self.extrair_dia(hora)])
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

        # Indica se há bombeamento de polpa em cada hora
        varBombeamentoPolpa = LpVariable.dicts("Bombeamento Polpa", (produtos_conc, horas_D14), 0, 1, LpInteger)

        # Restrição de capacidade do estoque EB06
        for hora in horas_D14:
            modelo += (
                lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc)
                    <= parametros_mineroduto_ubu['Capacidade EB06'][hora],
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
            # modelo += (
            #     varEstoqueEB06[produto][horas_D14[0]]
            #         == estoque_eb06_d0[produto]
            #         + varProducaoVolume[produto][horas_D14[0]]
            #         - varBombeamentoPolpa[produto][horas_D14[0]]*vazao_bombas,
            #     f"rest_define_EstoqueEB06_{produto}_{horas_D14[0]}",
            # )

        #garante um produto por vez
        for hora in horas_D14:
            modelo +=(
                lpSum(varBombeamentoPolpa[produto][hora] for produto in produtos_conc)  <= 1,
                f"rest_bombeamento_unico_produto_{hora}",
            )

        #garante fixação
        for produto in produtos_conc:
            for horas in horas_D14[0:24]:
                if varBombeamentoPolpaPPO[produto][horas] == 0 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
                    modelo += (varBombeamentoPolpa[produto][horas] <=0, f"rest_fixado2_{produto}_{horas}")
                if varBombeamentoPolpaPPO[produto][horas] == 1 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
                    modelo += (varBombeamentoPolpa[produto][horas] >=1, f"rest_fixado2_{produto}_{horas}")


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

        # Indica a produção em Ubu, por hora
        varProducaoUbu = LpVariable.dicts("Producao Ubu", (produtos_conc, produtos_usina, horas_D14), 0, None, LpContinuous)

        # Define a produção em Ubu
        for produto_c in produtos_conc:
            for produto_u in produtos_usina:
                for hora in horas_D14:
                    if de_para_produtos_conc_usina[produto_c][produto_u] == 1:
                        modelo += (
                            varProducaoUbu[produto_c][produto_u][hora] == varProducaoSemIncorporacao[produto_u][hora],
                            f"rest_define_ProducaoUbu_{produto_c}_{produto_u}_{hora}",
                        )
                    else:
                        modelo += (
                            varProducaoUbu[produto_c][produto_u][hora] == 0,
                            f"rest_zera_ProducaoUbu_{produto_c}_{produto_u}_{hora}",
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
                                                                    parametros_calculados['% Sólidos - EB06'][self.extrair_dia(horas_D14[i])] *
                                                                    parametros_ubu['Densid.'][self.extrair_dia(horas_D14[i])]
                                                                - lpSum(varProducaoUbu[produto][produto_u][horas_D14[i]]
                                                                        for produto_u in produtos_usina)
                                                                - varVolumePatio[produto][horas_D14[i]]
                                                                + varRetornoPatio[produto][horas_D14[i]],
                    f"rest_define_EstoquePolpaUbu_{produto}_{horas_D14[i]}",
                )
            # Define o estoque de polpa em Ubu da primeira hora
            modelo += (
                varEstoquePolpaUbu[produto][horas_D14[0]] == estoque_polpa_ubu[produto]  +
                                                    varPolpaUbu[produto][horas_D14[0]] *
                                                        parametros_calculados['% Sólidos - EB06'][self.extrair_dia(horas_D14[0])] *
                                                        parametros_ubu['Densid.'][self.extrair_dia(horas_D14[0])]
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

        for produto in produtos_usina:
            modelo += (
                lpSum(varProducaoSemIncorporacao[produto_u][hora] for hora in horas_D14)
                >= min_producao_produtos_ubu[produto]
            )

        # # Indica, para cada navio, se é a hora que inicia o carregamento
        # varInicioCarregNavio = LpVariable.dicts("X Inicio Carregamento", (navios, horas_D14), 0, 1, LpInteger)

        # # Indica, para cada navio, em que data começa o carregamento
        # varDataInicioCarregNavio = LpVariable.dicts("Ct Inicio Carregamento", (navios), 0, None, LpContinuous)

        # # Indica o estoque de produto no pátio de Ubu, por hora
        # varEstoqueProdutoPatio = LpVariable.dicts("S Estoque Produto Patio", (produtos_usina, horas_D14), 0, None, LpContinuous)

        # for navio in navios:
        #     for idx_hora in range(len(horas_D14)):
        #         modelo += (
        #             (varInicioCarregNavio[navio][horas_D14[idx_hora]] +
        #             lpSum(varInicioCarregNavio[navio_j][horas_D14[s]]
        #                     for navio_j in navios
        #                         for s in range(idx_hora, min(idx_hora+math.ceil(parametros_navios['VOLUME'][navio]/parametros_navios['Taxa de Carreg.'][navio])-1, len(horas_D14)))
        #                             if navio_j != navio)
        #             ) <= capacidade_carreg_porto_por_dia,
        #             f"Producao1_{navio}_{horas_D14[idx_hora]}",
        #         )

        # # Restrições para garantir que cada navio até D14 começa o carregamento uma única vez
        # for navio in navios_ate_d14:
        #     modelo += (
        #         lpSum([varInicioCarregNavio[navio][hora] for hora in horas_D14]) == 1,
        #         f"rest_define_InicioCarregNavio_{navio}",
        #     )

        # for navio in navios:
        #     if not navio in navios_ate_d14:
        #         modelo += (
        #             lpSum([varInicioCarregNavio[navio][hora] for hora in horas_D14]) == 0,
        #             f"rest_define_InicioCarregNavio_{navio}",
        #         )

        # # Restrições para garantir consistência do carregamento
        # for navio in navios:
        #     modelo += (
        #         varDataInicioCarregNavio[navio] >=
        #             lpSum([idx_hora*varInicioCarregNavio[navio][horas_D14[idx_hora]]
        #                 for idx_hora in range(len(horas_D14))]),
        #         f"rest_consistencia_DataInicioCarregNavio_{navio}",
        #     )

        # # Restrições para garantir que carregamento só começa após navio chegar
        # for navio in navios_ate_d14:
        #     # print(navio, extrair_hora(parametros_navios['DATA-REAL'][navio]))
        #     modelo += (
        #     lpSum([idx_hora*varInicioCarregNavio[navio][horas_D14[idx_hora]] for idx_hora in range(len(horas_D14))]) >= self.extrair_hora(parametros_navios['DATA-REAL'][navio]),
        #         f"rest_limita_DataInicioCarregNavio_{navio}",
        #     )

        # # Define o estoque de produto no pátio de Ubu da segunda hora em diante
        # for produto in produtos_usina:
        #     for idx_hora in range(1, len(horas_D14)):
        #         modelo += (
        #             varEstoqueProdutoPatio[produto][horas_D14[idx_hora]]
        #                 == varEstoqueProdutoPatio[produto][horas_D14[idx_hora-1]] +
        #                     varProducaoSemIncorporacao[produto][horas_D14[idx_hora]]
        #                     - lpSum([varInicioCarregNavio[navio][horas_D14[idx_hora_s]] *
        #                         parametros_navios['Taxa de Carreg.'][navio] *
        #                         produtos_de_cada_navio[navio][produto]
        #                             for navio in navios
        #                                 for idx_hora_s in range(max(idx_hora-math.ceil(parametros_navios['VOLUME'][navio]/parametros_navios['Taxa de Carreg.'][navio])+1,1), idx_hora+1)]),
        #             f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[idx_hora]}",
        #         )
        #     # Define o estoque de produto no pátio de Ubu do primeiro dia
        #     modelo += (
        #         varEstoqueProdutoPatio[produto][horas_D14[0]]
        #             == estoque_produto_patio_d0[produto] +
        #             varProducaoSemIncorporacao[produto][horas_D14[0]]
        #             - lpSum([varInicioCarregNavio[navio][horas_D14[0]] *
        #                     parametros_navios['Taxa de Carreg.'][navio] *
        #                     produtos_de_cada_navio[navio][produto]
        #                     for navio in navios]),
        #         f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[0]}",
        #     )

        # varVolumeAtrasadoNavio = LpVariable.dicts("Volume Atrasado por navio", (navios_ate_d14), 0, None, LpContinuous)

        # for navio in navios_ate_d14:
        #     modelo += (
        #         varVolumeAtrasadoNavio[navio] ==
        #             (varDataInicioCarregNavio[navio] - self.extrair_hora(parametros_navios['DATA-REAL'][navio])) *
        #             parametros_navios['Taxa de Carreg.'][navio],
        #         f"rest_define_VolumeAtrasadoNavio_{navio}",
        #     )


        for fo in cenario['geral']['funcao_objetivo']:
            if not fo in ['max_brit', 'min_atr_nav', 'max_conc', 'max_usina', 'max_est_polpa', 'max_pf', 'min_est_patio']:
                raise Exception(f"Função objetivo {fo} não implementada!")

        # Definindo a função objetivo
        fo = 0
        # if 'max_conc' in cenario['geral']['funcao_objetivo']:
        #     fo += lpSum([varTaxaAlim[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
        if 'max_usina' in cenario['geral']['funcao_objetivo']:
            fo += lpSum([varProducaoSemIncorporacao[produto_usina][hora] for produto_usina in produtos_usina for hora in horas_D14])
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

        # time.sleep(10)
        # for c_name in modelo.constraints:
        #     if not modelo.constraints[c_name].valid():
        #         print(f'{c_name}:')
        # Cria a pasta com os resultados dos experimentos se ainda não existir
        if not os.path.exists(args.pasta_saida):
            os.makedirs(args.pasta_saida)

        # Salvando os dados em arquivo binário usando pickels
        nome_arquivo_saida = self.gerar_nome_arquivo_saida(f"{cenario['geral']['nome']}_resultados_1")
        with open(f'{args.pasta_saida}/{nome_arquivo_saida}', "w", encoding="utf8") as f:
            json.dump(resultados, f)

        return modelo.status, resultados
