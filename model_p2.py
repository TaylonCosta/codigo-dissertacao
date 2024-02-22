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

    def modelo(self, cenario, solver, data, varBombeamentoPolpa):

        # variaveis utilizadas pelo modelo
        horas_D14 = data['horas_D14']
        produtos_conc = data['produtos_conc']
        horas_Dm3 = data['horas_Dm3']
        horas_Dm3_D14 = data['horas_Dm3_D14']
        parametros_calculados = data['parametros_calculados']
        navios = data['navios']
        parametros_mineroduto_ubu = data['parametros_mineroduto_ubu']
        dias = data['dias']
        max_producao_sem_incorporacao = data['max_producao_sem_incorporacao']
        args = data['args']
        produtos_usina = data['produtos_usina']
        de_para_produtos_conc_usina = data['de_para_produtos_conc_usina']
        parametros_ubu = data['parametros_ubu']
        tempo_mineroduto = data['tempo_mineroduto']
        min_estoque_polpa_ubu = data['min_estoque_polpa_ubu']
        max_estoque_polpa_ubu = data['max_estoque_polpa_ubu']
        max_taxa_envio_patio = data['max_taxa_envio_patio']
        max_taxa_retorno_patio_usina = data['max_taxa_retorno_patio_usina']
        min_estoque_patio_usina = data['min_estoque_patio_usina']
        max_estoque_patio_usina = data['max_estoque_patio_usina']
        estoque_polpa_ubu = data['estoque_polpa_ubu']
        estoque_inicial_patio_usina = data['estoque_inicial_patio_usina']
        fator_limite_excesso_patio = data['fator_limite_excesso_patio']
        parametros_navios = data['parametros_navios']
        capacidade_carreg_porto_por_dia = data['capacidade_carreg_porto_por_dia']
        navios_ate_d14 = data['navios_ate_d14']
        produtos_de_cada_navio = data['produtos_de_cada_navio']
        estoque_produto_patio_d0 = data['estoque_produto_patio_d0']
        parametros_mineroduto_md3 = data['parametros_mineroduto_md3']

        BIG_M = 10e6
        modelo = LpProblem("Plano Semanal", LpMaximize)

        varBombeado = LpVariable.dicts("Bombeado", (produtos_conc, horas_Dm3_D14), 0, None, LpContinuous)

        # Carrega os dados de D-3
        # for idx_hora in range(len(horas_D14)):
        #     for produto in produtos_conc:
        #         if varBombeamentoPolpa[produto][horas_D14[idx_hora]] == 1:
        #             modelo += (
        #                 varBombeamentoPolpa[produto][horas_D14[idx_hora]] == 1,
        #                 f"rest_define_Bombeamento_inicial_{produto}_{horas_D14[idx_hora]}",
        #             )
        #             modelo += (
        #                 varBombeado[produto][horas_D14[idx_hora]] == 1,
        #                 f"rest_define_Bombeado_inicial_{produto}_{horas_D14[idx_hora]}",
        #             )
        #         else:
        #             modelo += (
        #                 varBombeamentoPolpa[produto][horas_D14[idx_hora]] == 0,
        #                 f"rest_define_Bombeamento_inicial_{produto}_{horas_D14[idx_hora]}",
        #             )
        #             modelo += (
        #                 varBombeado[produto][horas_D14[idx_hora]] == 0,
        #                 f"rest_define_Bombeado_inicial_{produto}_{horas_D14[idx_hora]}",
        #             )
        # Indica chegada de polpa em Ubu, por produto, por hora
        varPolpaUbu = LpVariable.dicts("Polpa Ubu (65Hs)", (produtos_conc, horas_D14), 0, None, LpContinuous)

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

        #for produto in produtos_usina:
        #    for hora in horas_D14:


        # Define a produção em Ubu
        for produto_c in produtos_conc:
            for produto_u in produtos_usina:
                for hora in horas_D14:
                    if de_para_produtos_conc_usina[produto_c][produto_u] == 1:
                        modelo += (
                            varProducaoUbu[produto_c][produto_u][hora] == varProducaoSemIncorporacao[produto_u][hora]*(1+parametros_ubu['Conv.'][self.extrair_dia(hora)]/100),
                            f"rest_define_ProducaoUbu_{produto_c}_{produto_u}_{hora}",
                        )
                    else:
                        modelo += (
                            varProducaoUbu[produto_c][produto_u][hora] == 0,
                            f"rest_zera_ProducaoUbu_{produto_c}_{produto_u}_{hora}",
                        )

        # '''
        # # Indica a hora de início das manutenções da usina
        # varInicioManutencoesUsina = LpVariable.dicts("Início Manutenção Usina", (range(len(duracao_manutencoes_usina)), horas_Dm3_D14), 0, 1, LpInteger)

        # # Restrição para garantir que a manutenção do usina se inicia uma única vez
        # for idx_manut in range(len(duracao_manutencoes_usina)):
        #     modelo += (
        #         lpSum([varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]]
        #             for idx_hora in range(0, janela_planejamento*6)]) == 1,
        #         f"rest_define_InicioManutencoesUsina_{idx_manut}",
        #     )

        # # Restrição que impede que as manutenções ocorram na segunda semana
        # for idx_manut in range(len(duracao_manutencoes_usina)):
        #     modelo += (
        #         lpSum([varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]]
        #             for idx_hora in range(janela_planejamento*6, len(horas_D14))]) == 0,
        #         f"rest_evita_InicioManutencoesUsina_{idx_manut}",
        #     )

        # # Restrições para evitar que manutenções ocorram ao mesmo tempo
        # for idx_hora in range(len(horas_D14)):
        #     for idx_manut in range(len(duracao_manutencoes_usina)):
        #         modelo += (
        #             varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]] +
        #             lpSum(varInicioManutencoesUsina[s][horas_D14[j]]
        #                 for j in range(idx_hora-duracao_manutencoes_usina[idx_manut]+1,idx_hora)
        #                 for s in range(len(duracao_manutencoes_usina))
        #                 if s != idx_manut
        #                 )
        #             <= 1,
        #         f"rest_separa_manutencoesUsina_{idx_manut}_{idx_hora}",
        #         )

        # # Fixa o horário de início da manutenção do usina se foi escolhido pelo usuário
        # for idx_manut, inicio in enumerate(inicio_manutencoes_usina):
        #     if inicio != 'livre':
        #         modelo += (
        #             varInicioManutencoesUsina[idx_manut][inicio] == 1,
        #             f"rest_fixa_InicioManutencaoUsina_{idx_manut}",
        #         )

        # # Restrição tratar manutenção, lower bound e valor fixo de produção sem incorporação
        # for produto in produtos_usina:
        #     for idx_hora in range(len(horas_D14)):
        #         # se está em manutenção, zera a taxa de alimentação
        #         for idx_manut in range(len(duracao_manutencoes_usina)):
        #             modelo += (
        #                 varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] <= BIG_M*(1 -
        #                                         lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
        #                                         for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
        #                 f"rest_manutencao_usina_{idx_manut}_{horas_D14[idx_hora]}",
        #         )

        #     # Define lower bound
        #         modelo += (
        #             varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] >= min_producao_sem_incorporacao
        #                                                 - BIG_M*(lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
        #                                                             for idx_manut in range(len(duracao_manutencoes_usina))
        #                                                             for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
        #             f"rest_LB_prod_sem_incorp1_{produto}_{horas_D14[idx_hora]}",
        #         )
        #         modelo += (
        #             varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] <= BIG_M*(1 - lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
        #                                                             for idx_manut in range(len(duracao_manutencoes_usina))
        #                                                             for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
        #             f"rest_LB_prod_sem_incorp2_{produto}_{horas_D14[idx_hora]}",
        #         )

        #         # se a produção sem incorporação é fixada pelo modelo ou pelo usuário
        #         if fixar_producao_sem_incorporacao in ['fixado_pelo_modelo','fixado_pelo_usuario']:
        #             taxa_fixa = producao_sem_incorporacao_fixa
        #             if fixar_producao_sem_incorporacao == 'fixado_pelo_modelo':
        #                 varProducaoSemIncorporacaoFixa = LpVariable("Producao sem incorporacao Fixa", 0, max_producao_sem_incorporacao, LpContinuous)
        #                 taxa_fixa = varProducaoSemIncorporacaoFixa
        #             modelo += (
        #                 varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] >= taxa_fixa
        #                                                     -BIG_M*(lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
        #                                                             for idx_manut in range(len(duracao_manutencoes_usina))
        #                                                             for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
        #                 f"rest_prod_sem_incorp_fixa1_{produto}_{horas_D14[idx_hora]}",
        #             )
        #             modelo += (
        #                 varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] <= BIG_M*(1 - lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
        #                                                                 for idx_manut in range(len(duracao_manutencoes_usina))
        #                                                                 for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
        #                 f"rest_prod_sem_incorp_fixa2_{produto}_{horas_D14[idx_hora]}",
        #             )
        #             modelo += (
        #                 varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] <= taxa_fixa,
        #                 f"rest_prod_sem_incorp_fixa3_{produto}_{horas_D14[idx_hora]}",
        #             )
        # '''
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
                varEstoquePolpaUbu[produto][horas_D14[0]] == estoque_polpa_ubu  +
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

        #
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
        #if 'min_atr_nav' in cenario['geral']['funcao_objetivo']:
        #    fo += - (lpSum([varVolumeAtrasadoNavio[navio] for navio in navios_ate_d14]))
        #if 'max_conc' in cenario['geral']['funcao_objetivo']:
        #    fo += lpSum([varTaxaAlim[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
        if 'max_usina' in cenario['geral']['funcao_objetivo']:
            fo += lpSum([varProducaoSemIncorporacao[produto_usina][hora] for produto_usina in produtos_usina for hora in horas_D14])
        # if 'max_est_polpa' in cenario['geral']['funcao_objetivo']:
        #     fo += lpSum([varEstoquePolpaUbu[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
        # if 'min_est_patio' in cenario['geral']['funcao_objetivo']:
        #     fo += - (lpSum([varEstoquePatio[hora] for hora in horas_D14]))
        #if 'max_brit' in cenario['geral']['funcao_objetivo']:
        #    fo += (lpSum([varTaxaBritagem[produto_mina][hora] for produto_mina in produtos_mina for hora in horas_D14]))

        modelo += (fo, "FO",)

        # The problem data is written to an .lp file
        # prob.writeLP("PSemanal.lp")

        # The problem is solved using PuLP's choice of Solver
        solver.solve(modelo)
        # for produto in produtos_conc:
        #     for i in range(0, len(horas_D14)):
        #         print(varPolpaUbu[produto][horas_D14[i]].varValue)
        #         print(parametros_calculados['% Sólidos - EB06'][self.extrair_dia(horas_D14[0])])
        #         print(parametros_ubu['Densid.'][self.extrair_dia(horas_D14[0])])
        #         print(varPolpaUbu[produto][horas_D14[i]].varValue*parametros_calculados['% Sólidos - EB06'][self.extrair_dia(horas_D14[0])]*parametros_ubu['Densid.'][self.extrair_dia(horas_D14[0])])

        resultados = {'variaveis':{}}
        for v in modelo.variables():
            resultados['variaveis'][v.name] = v.varValue

        #resultados['parametros']= {'produtos_britagem': produtos_britagem, 'dados': dados}

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
        nome_arquivo_saida = self.gerar_nome_arquivo_saida(f"{cenario['geral']['nome']}_resultados_2")
        with open(f'{args.pasta_saida}/{nome_arquivo_saida}', "w", encoding="utf8") as f:
            json.dump(resultados, f)

        return modelo.status, resultados
