from openpyxl import load_workbook # usado para ler a planilha
from pulp import *                 # usado para resolver o problema de otimização
import argparse                    # usado para tratar os argumentos do script
import csv                         # usado para gerar o resutlado em um arquivo CSV
import json                        # usado para gerar o resultado em um arquivo JSON
import logging                     # usado para gerar o log do otimizador
import orloge                      # usado para obter as informações de saída do solver
import math
import os
import numpy as np
from itertools import accumulate
import time
import instance_reader

VERSAO_OTIMIZADOR = '0.9.10'
DATA_VERSAO = '2024-02-19'

# Log de alterações das versões:
#
# 0.9.10:
# - Inclusão da Heurística de Otimização por Partes para tratar as variáveis do mineroduto.
# - E atualização da Heurística anterior (Relax and Fix).
# - Alteração nos argumentos do script: remoção de parâmetros das heurísticas e inclusão dos
#   argumentos --heuristica-relax-and-fix', --heuristica-otim-partes e --param-adicionais
# 0.9.9:
# - Validação dos dados de entrada (da planilha) no script instance_reader.py
# - Preparação para execução via container Docker
# 0.9.8:
# - Heurística para tratar variáveis do mineroduto.
# - E consequente criação de novos argumentos para o script:
#   --heuristica-mineroduto, --desab-warmstart-heuristica', --desab-solucao-pos-heuristica
#   --heuristica-limite-inf, --heuristica-limite-fix, --heuristica-limite-set, --desab-heuristica-Normal
# - Uso de valor de BIG_M menor para restrições do mineroduto (corrigindo problemas de precisão numérica)
# - Acrescentadas informações da heurística e dos nomes dos arquivos gerados no JSON de resultados
# - Criação do argumento --gurobi-options que permite passar parâmetros para o Gurobi
# - Criação do argumento --arquivo-sumario que permite acrescentar uma linha de resultado no arquivo CSV de sumarização
# - Correção no cálculo da qualidade (divisão por 100)
# 0.9.7:
# - Tratamento de janelas de campanha (de massa e hora) para concentrador e pelotização
# - Geração de informações sobre restrições e limites que inviabilizam o modelo
# - Novos argumentos de entrada para o script: --gurobi-path e --verificar-inviabilidade
# - Correção na restrição que evita dois navios carregando ao mesmo tempo (na hora final do carregamento)
# - Correção na restrição usada pela configuração 'config_janela_final'
# - Correção de declaração de variáveis na opção 'fixado_pelo_modelo' para concentrador e pelotização
# 0.9.6:
# - Inclusão do argumento -v que retorna a versão do script.
# 0.9.5:
# - Vazão de EB07 é ignorada. Considera-se que a vazão de EB06 continua na segunda seção do Mineroduto
# - Correção no limite mínimo da taxa de alimentação do concentrador e da produção sem incorporação da pelotização
# 0.9.4:
# - Puxada agora é calculada em TMS em vez de TMN.
# - Alteração na leitura da aba Config (aceitando tipos de dados que vêm da planilha).
# - Correção na obtenção do produto do último batch do D-3.
# - Correção na hora do final das janelas de manutenção

def gerar_nome_arquivo_saida(nome_base_arquivo, extensao, sobrescrever=True):
    """ Gera o nome padronizado do arquivo de saída """
    if sobrescrever or not os.path.exists(f'{nome_base_arquivo}.{extensao}'):
        nome_arquivo = f'{nome_base_arquivo}.{extensao}'
    else:
        contador = 1
        while os.path.exists(f"{nome_base_arquivo}_{contador}.{extensao}"):
            contador += 1
        nome_arquivo = f"{nome_base_arquivo}_{contador}.{extensao}"

    if sobrescrever and os.path.exists(nome_arquivo):
        os.remove(nome_arquivo)

    return nome_arquivo

def exportar_variaveis_csv(nome_arquivo_saida, valores_variaveis, horas_D14):
    # Abrir o arquivo CSV para escrita
    with open(nome_arquivo_saida, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)

        # Escrever o cabeçalho do CSV
        header = ['Variavel'] + [f'{hora}' for hora in horas_D14]
        csvwriter.writerow(header)

        # Escrever os valores das variáveis
        for variavel in sorted(valores_variaveis.keys()):
            row = [variavel]
            for hora in horas_D14:
                valor = valores_variaveis[variavel].get(hora, '')  # Se não houver valor, deixe em branco
                row.append(valor)
            csvwriter.writerow(row)

def extrair_dia(hora):
    ''' Retorna o dia de uma hora no formato dXX_hYY '''
    if hora[:2] != 'dm':
        return hora.split('_')[0]
    else:
        return 'd'+hora[2:].split('_')[0]

def extrair_hora(dia):
    return (int(dia[1:])-1)*24

def indice_da_hora(hora):
    return (int(hora[1:3])-1)*24+int(hora[-2:])-1

def calcular_hora_pelo_inicio_programacao(inicio, data):
    return int((data-inicio).total_seconds()/3600)

def verifica_status_solucao(nome_arquivo_log_solver):
    status_solucao = LpStatus[modelo.status]
    gap = None
    valor_fo = None

    # Obtendo os dados de log do solver como um dicionário
    logs_solver = orloge.get_info_solver(nome_arquivo_log_solver, 'GUROBI')

    melhor_limite, melhor_solucao = logs_solver["best_bound"], logs_solver["best_solution"]

    if melhor_limite is not None and melhor_solucao is not None :
        gap = abs(melhor_limite - melhor_solucao) / (1e-10 + abs(melhor_solucao)) * 100 # Gap in %. We add 1e-10 to avoid division by zero.
    else :
        gap = 'N/A'

    if LpStatus[modelo.status] == 'Optimal':
        valor_fo = modelo.objective.value()
        if gap == 0:
            logger.info(f'Solução ÓTIMA encontrada: {melhor_solucao:.1f} (gap: {gap:.1f}%)')
        else:
            status_solucao = 'Feasible'
            logger.info(f'Solução viável encontrada: {melhor_solucao:.1f} (gap: {gap:.1f}%)')
        logger.info('[OK]')
    elif logs_solver['status'] == 'Model is infeasible':
        status_solucao = 'Infeasible'
        logger.warning(f'Não foi possível encontrar solução!')
    else:
        logger.warning(f'Não foi possível encontrar solução!')',

    return valor_fo, status_solucao, gap

def heuristica_relax_and_fix(modelo, gurobi_options, nome_instancia, parametros, varBombeamentoPolpaEB06, produtos_conc, horas_D14, solver, args):
    for option, value in gurobi_options:
        if option == "MIPgap":
            gurobi_options.remove((option, value))
    gurobi_options.append(("MIPgap", 0))
    foRelax = -  lpSum([varBombeamentoPolpaEB06[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
    modelo.setObjective(foRelax)
    nome_arquivo_log_solver = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_solver_relaxado', 'log', not args.nao_sobrescrever_arquivos)
    logger.info('RESOLVENDO o modelo relaxado (heurística Relax and Fix habilitada)')
    solver.optionsDict['logPath'] = nome_arquivo_log_solver
    # The problem is solved using PuLP's choice of Solver
    solver.solve(modelo)
    tempo_modelo_relaxado = modelo.solutionTime
    valor_fo_modelo_relaxado, status_solucao_modelo_relaxado, gap_modelo_relaxado = verifica_status_solucao(nome_arquivo_log_solver)

    ############################  Heuristica ###################################

    FixadaT = None
    if status_solucao_modelo_relaxado in ['Optimal', 'Feasible']:
        logger.info('Tratando a heurística Relax and Fix para variáveis do mineroduto')

        resultados_variavel_ac = {}
        for produto_conc in produtos_conc:
           acumulado = list(itertools.accumulate([varBombeamentoPolpaEB06[produto_conc][hora].varValue for hora in horas_D14]))
           resultados_variavel_ac[produto_conc] = {horas_D14[i] : acumulado[i] for i in range(len(horas_D14))}

        if parametros['config']['config_janela_bombeamento_polpa'] == 'fixado_pelo_usuario':
            LIp = parametros['config']['config_valor_janela_bombeamento_polpa']
            LSp = LIp
        else:
            LIp = parametros['config']['janela_min_bombeamento_polpa']
            LSp = parametros['config']['janela_max_bombeamento_polpa']

        if parametros['config']['config_janela_bombeamento_agua'] == 'fixado_pelo_usuario':
            LIa = parametros['config']['config_valor_janela_bombeamento_agua']
            LSa = LIa
        else:
            LIa = parametros['config']['janela_min_bombeamento_agua']
            LSa = parametros['config']['janela_max_bombeamento_agua']

        limite_inf = 0.99
        AjustePolpa = 0.8 #0.8
        Gap_Relax_Fix = 0.05

        if args.param_adicionais:
            # Lê o arquivo JSON com os parâmetros do solver
            with open(args.param_adicionais, 'r') as arquivo:
                arq_param_adicionais = json.load(arquivo)
                if "heuristica" in arq_param_adicionais:
                    if "limite_inf" in arq_param_adicionais["heuristica"]:
                        limite_inf = arq_param_adicionais["heuristica"]["limite_inf"]
                    if "polpa_janela" in arq_param_adicionais["heuristica"]:
                        AjustePolpa = arq_param_adicionais["heuristica"]["polpa_janela"]
                    if "Gap_Relax_Fix" in arq_param_adicionais["heuristica"]:
                        Gap_Relax_Fix = arq_param_adicionais["heuristica"]["Gap_Relax_Fix"]

        Agua = round(max(LSp + min(LSa,2.66*LIa), LSp*2.66)) #30
        Polpa = round(AjustePolpa*LIp) #round(LIp*AjustePolpa)

        #Mínimo a ser fixado
        FatorJanelaMin = 0.1
        JanelaMinFixacao = max(round(Polpa*FatorJanelaMin,0),2)
        JanelaMinFixacaoOrg = JanelaMinFixacao

        Fixada = np.zeros(len(produtos_conc))
        FixadaT = 0

        limite_inf_org = limite_inf

        ORIGINAL_VALUE = Gap_Relax_Fix

        for option, value in gurobi_options:
            if option == "MIPgap":
                gurobi_options.remove((option, value))
        gurobi_options.append(("MIPgap", ORIGINAL_VALUE))

        cont_horas = 0
        DataMin = 0
        FixIni = 0
        #FixIniOld = 0

        while cont_horas < len(horas_D14):

            hora = horas_D14[cont_horas]

            if cont_horas > DataMin:

                prod = None
                cont_conc = 0
                maior = 0
                for produto in produtos_conc:

                    maxValue = max(varBombeamentoPolpaEB06[produto][hora].varValue for hora in horas_D14[cont_horas:cont_horas+Polpa])

                    if resultados_variavel_ac[produto][hora] >= Fixada[cont_conc] and varBombeamentoPolpaEB06[produto][hora].varValue >=limite_inf and maxValue > maior:
                        prod = produto
                        prodN = cont_conc
                        maior = maxValue
                    cont_conc +=1

                if prod != None:

                    for option, value in gurobi_options:
                        if option == "MIPgap":
                            gurobi_options.remove((option, value))
                        if option == "SolutionLimit ":
                            gurobi_options.remove((option, value))
                    gurobi_options.append(("MIPgap", ORIGINAL_VALUE))
                    gurobi_options.append(("SolutionLimit", 1000))

                    for hora_p in range(cont_horas, min(cont_horas+Polpa, 336)):

                        if resultados_variavel_ac[prod][horas_D14[hora_p]] >= Fixada[prodN] and varBombeamentoPolpaEB06[prod][horas_D14[hora_p]].varValue >= limite_inf:

                            modelo += (varBombeamentoPolpaEB06[prod][horas_D14[hora_p]] >= 1, f"rest_fixado_{prod}_{horas_D14[hora_p]}")
                            DataMin = min(hora_p + Agua,335)
                            FixadaT +=1
                            Fixada[prodN] +=1

                    for produto in produtos_conc:
                        for horas in horas_D14[FixIni:DataMin]:
                            modelo += (varBombeamentoPolpaEB06[produto][horas] <= 0 + BIG_M*w_teste[produto][horas], f"rest_teste3_{produto}_{horas}")
                            modelo += (varBombeamentoPolpaEB06[produto][horas] >= 1 - BIG_M*(1 - w_teste[produto][horas]), f"rest_teste4_{produto}_{horas}")

                    for v in modelo.variables():
                        if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
                            v.setInitialValue(v.lowBound)
                        elif v.upBound is not None and v.varValue > v.upBound - 0.001:
                            v.setInitialValue(v.upBound)
                        else:
                            v.setInitialValue(v.varValue)


                    # Aproveitar valor da memória
                    logger.info(f'RESOLVENDO o modelo relaxado (fixando de {horas_D14[FixIni]} até {horas_D14[DataMin]})')
                    solver.optionsDict['warmStart'] = True
                    solver.solve(modelo)


                    valor_fo_RaF, status_solucao_RaF, gap_RaF = verifica_status_solucao(nome_arquivo_log_solver)

                    Window_Inv = 12
                    contInv = 1

                    while not  status_solucao_RaF in ['Optimal', 'Feasible']:

                        Window_Inv = Window_Inv*contInv

                        for produto in produtos_conc:

                            valor_hist = FixIni-Window_Inv

                            for horas in horas_D14[valor_hist:DataMin]:
                                if f"rest_fixado2_{produto}_{horas}" in modelo.constraints:
                                    del modelo.constraints[f"rest_fixado2_{produto}_{horas}"]
                                # if f"rest_fixado_{produto}_{horas}" in modelo.constraints:
                                #     del modelo.constraints[f"rest_fixado_{produto}_{horas}"]
                                if f"rest_teste3_{produto}_{horas}" in modelo.constraints:
                                    del modelo.constraints[f"rest_teste3_{produto}_{horas}"]
                                if f"rest_teste4_{produto}_{horas}" in modelo.constraints:
                                    del modelo.constraints[f"rest_teste4_{produto}_{horas}"]

                        logger.info(f'RESOLVENDO o modelo relaxado ajustando INVIABILIDADE (de {horas_D14[valor_hist]} até {horas_D14[DataMin]})')

                        for option, value in gurobi_options:
                            if option == "MIPgap":
                                gurobi_options.remove((option, value))
                            if option == "SolutionLimit ":
                                gurobi_options.remove((option, value))
                        gurobi_options.append(("SolutionLimit", 1))
                        gurobi_options.append(("MIPgap", 2*ORIGINAL_VALUE))

                        solver.solve(modelo)

                        for option, value in gurobi_options:
                            if option == "MIPgap":
                                gurobi_options.remove((option, value))
                            if option == "SolutionLimit ":
                                gurobi_options.remove((option, value))
                        gurobi_options.append(("MIPgap", ORIGINAL_VALUE))
                        gurobi_options.append(("SolutionLimit", 1000))

                        contInv +=1

                        valor_fo_RaF, status_solucao_RaF, gap_RaF = verifica_status_solucao(nome_arquivo_log_solver)

                        FixIni = valor_hist

                    for produto in produtos_conc:
                        for horas in horas_D14[FixIni:DataMin]:
                            # if varBombeamentoPolpaEB06[produto][horas].varValue == 0:
                            #     modelo += (varBombeamentoPolpaEB06[produto][horas] <=0, f"rest_fixado2_{produto}_{horas}")
                            if varBombeamentoPolpaEB06[produto][horas].varValue == 1:
                                modelo += (varBombeamentoPolpaEB06[produto][horas] >= 1, f"rest_fixado2_{produto}_{horas}")

                    #FixIniOld = FixIni
                    FixIni = DataMin
                    limite_inf = limite_inf_org
                    JanelaMinFixacao = JanelaMinFixacaoOrg

                if prod == None and cont_horas - DataMin > Agua + Polpa :
                    cont_horas = DataMin
                    limite_inf = limite_inf-0.05
                    JanelaMinFixacao = 1


            cont_horas += 1

        if FixIni < 335:
            for produto in produtos_conc:
                for hora in horas_D14[FixIni:335]:
                    modelo += (varBombeamentoPolpaEB06[produto][hora] <= 0 + BIG_M*w_teste[produto][hora], f"rest_teste3_{produto}_{hora}")
                    modelo += (varBombeamentoPolpaEB06[produto][hora] >= 1 - BIG_M*(1 - w_teste[produto][hora]), f"rest_teste4_{produto}_{hora}")

            # Aproveitar valor da memória
            solver.optionsDict['warmStart'] = True

            for option, value in gurobi_options:
                if option == "MIPgap":
                    gurobi_options.remove((option, value))
                if option == "SolutionLimit ":
                    gurobi_options.remove((option, value))
            gurobi_options.append(("MIPgap",  args.mipgap))
            gurobi_options.append(("SolutionLimit", 1000))

            logger.info(f'RESOLVENDO o modelo relaxado (fixando até {horas_D14[FixIni]}) - {FixadaT} variáveis fixadas')
            solver.solve(modelo)


        logger.info('[OK]')


        logger.info('Inicializando variáveis do modelo com a solução Relax and Fix')


        for v in modelo.variables():
            if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
                v.setInitialValue(v.lowBound)
            elif v.upBound is not None and v.varValue > v.upBound - 0.001:
                v.setInitialValue(v.upBound)
            else:
                v.setInitialValue(v.varValue)

        logger.info('[OK]')



        logger.info('RESOLVENDO o modelo original iniciado com a solução Relax and Fix')

        modelo.setObjective(fo)
        for option, value in gurobi_options:
            if option == "MIPgap":
                gurobi_options.remove((option, value))
            if option == "SolutionLimit ":
                gurobi_options.remove((option, value))
        gurobi_options.append(("MIPgap", args.mipgap))
        gurobi_options.append(("SolutionLimit", 1000))


        for produto in produtos_conc:
            for hora in horas_D14:
                if f"rest_fixado_{produto}_{hora}" in modelo.constraints:
                    del modelo.constraints[f"rest_fixado_{produto}_{hora}"]
                if f"rest_fixado2_{produto}_{hora}" in modelo.constraints:
                    del modelo.constraints[f"rest_fixado2_{produto}_{hora}"]

        for v in modelo.variables():
            if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
                v.setInitialValue(v.lowBound)
            elif v.upBound is not None and v.varValue > v.upBound - 0.001:
                v.setInitialValue(v.upBound)
            else:
                v.setInitialValue(v.varValue)


        solver.optionsDict['warmStart'] = True
        nome_arquivo_log_solver = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_solver_completo', 'log', not args.nao_sobrescrever_arquivos)
        solver.optionsDict['logPath'] = nome_arquivo_log_solver
        solver.solve(modelo)

        tempo_modelo_completo = modelo.solutionTime
        valor_fo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo = verifica_status_solucao(nome_arquivo_log_solver)

    return valor_fo_modelo_relaxado, tempo_modelo_relaxado, gap_modelo_relaxado, valor_fo_modelo_completo, tempo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo, nome_arquivo_log_solver


def heuristica_otim_por_partes(modelo, nome_instancia, varBombeamentoPolpaEB06, produtos_conc, horas_D14, solver, args):

    foRelax = lpSum([varBombeamentoPolpaEB06[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
    modelo.setObjective(foRelax)
    nome_arquivo_log_solver = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_solver_relaxado', 'log', not args.nao_sobrescrever_arquivos)
    logger.info('RESOLVENDO o modelo relaxado (heurística de Otimização por Partes)')
    solver.optionsDict['logPath'] = nome_arquivo_log_solver
    # The problem is solved using PuLP's choice of Solver
    solver.solve(modelo)
    tempo_modelo_relaxado = modelo.solutionTime
    valor_fo_modelo_relaxado, status_solucao_modelo_relaxado, gap_modelo_relaxado = verifica_status_solucao(nome_arquivo_log_solver)

    ############################  Heuristica ###################################

    if status_solucao_modelo_relaxado in ['Optimal', 'Feasible']:
        logger.info('Tratando a heurística de Otimização por Partes para variáveis do mineroduto')

        gap_heuristica = 0.25
        FindSolutionsCount = 5
        Janelas = 5

        if args.param_adicionais:
            # Lê o arquivo JSON com os parâmetros do solver
            with open(args.param_adicionais, 'r') as arquivo:
                arq_param_adicionais = json.load(arquivo)
                if "heuristica_otim_por_partes" in arq_param_adicionais:
                    if "gap_heuristica" in arq_param_adicionais["heuristica_otim_por_partes"]:
                        gap_heuristica = arq_param_adicionais["heuristica_otim_por_partes"]["gap_heuristica"]
                    if "FindSolutionsCount" in arq_param_adicionais["heuristica_otim_por_partes"]:
                        FindSolutionsCount = arq_param_adicionais["heuristica_otim_por_partes"]["FindSolutionsCount"]
                    if "Janelas" in arq_param_adicionais["heuristica_otim_por_partes"]:
                        Janelas = arq_param_adicionais["heuristica_otim_por_partes"]["Janelas"]

        DataMin = 0
        cont_horas = 0
        ORIGINAL_VALUE = gap_heuristica

        for option, value in gurobi_options:
            if option == "MIPgap":
                gurobi_options.remove((option, value))
        gurobi_options.append(("MIPgap", ORIGINAL_VALUE))
        gurobi_options.append(("SolutionLimit", FindSolutionsCount))

        total_Horas = len(horas_D14)
        Window = round(total_Horas/Janelas)

        for hora in horas_D14:

            if cont_horas >= DataMin and cont_horas + Window < 335:

                DataMin = min(cont_horas + Window,335)

                for produto in produtos_conc:
                    for horas in horas_D14[cont_horas:DataMin]:
                        modelo += (varBombeamentoPolpaEB06[produto][horas] <= 0 + BIG_M*w_teste[produto][horas], f"rest_teste3_{produto}_{horas}")
                        modelo += (varBombeamentoPolpaEB06[produto][horas] >= 1 - BIG_M*(1 - w_teste[produto][horas]), f"rest_teste4_{produto}_{horas}")

                for v in modelo.variables():
                    if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
                        v.setInitialValue(v.lowBound)
                    elif v.upBound is not None and v.varValue > v.upBound - 0.001:
                        v.setInitialValue(v.upBound)
                    else:
                        v.setInitialValue(v.varValue)

                # Aproveitar valor da memória
                logger.info(f'RESOLVENDO o modelo relaxado (fixando de {horas_D14[cont_horas]} até {horas_D14[DataMin]})')
                solver.optionsDict['warmStart'] = True
                solver.solve(modelo)

                valor_fo_RaF, status_solucao_RaF, gap_RaF = verifica_status_solucao(nome_arquivo_log_solver)

                Window_Inv = 24
                contInv = 1

                while not  status_solucao_RaF in ['Optimal', 'Feasible']:

                    Window_Inv = Window_Inv*contInv
                    for produto in produtos_conc:
                        valor_hist = cont_horas-Window_Inv
                        for horas in horas_D14[valor_hist:cont_horas]:
                            if f"rest_fixado2_{produto}_{horas}" in modelo.constraints:
                                del modelo.constraints[f"rest_fixado2_{produto}_{horas}"]

                    logger.info(f'RESOLVENDO o modelo relaxado ajustando INVIABILIDADE (de {horas_D14[valor_hist]} até {horas_D14[DataMin]})')

                    for option, value in gurobi_options:
                        if option == "MIPgap":
                            gurobi_options.remove((option, value))
                        if option == "SolutionLimit ":
                            gurobi_options.remove((option, value))
                    gurobi_options.append(("SolutionLimit", 1))
                    gurobi_options.append(("MIPgap", 2*ORIGINAL_VALUE))

                    solver.solve(modelo)

                    for option, value in gurobi_options:
                        if option == "MIPgap":
                            gurobi_options.remove((option, value))
                        if option == "SolutionLimit ":
                            gurobi_options.remove((option, value))
                    gurobi_options.append(("MIPgap", ORIGINAL_VALUE))
                    gurobi_options.append(("SolutionLimit", FindSolutionsCount))


                    contInv +=1

                    valor_fo_RaF, status_solucao_RaF, gap_RaF = verifica_status_solucao(nome_arquivo_log_solver)


                for produto in produtos_conc:
                    for horas in horas_D14[0:DataMin]:
                        if varBombeamentoPolpaEB06[produto][horas].varValue == 0 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
                            modelo += (varBombeamentoPolpaEB06[produto][horas] <=0, f"rest_fixado2_{produto}_{horas}")
                        if varBombeamentoPolpaEB06[produto][horas].varValue == 1 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
                            modelo += (varBombeamentoPolpaEB06[produto][horas] >= 1, f"rest_fixado2_{produto}_{horas}")


            cont_horas += 1

        logger.info('RESOLVENDO o modelo original iniciado com a solução do Otimizador por Partes')

        modelo.setObjective(fo)
        for option, value in gurobi_options:
            if option == "MIPgap":
                gurobi_options.remove((option, value))
            if option == "SolutionLimit ":
                gurobi_options.remove((option, value))
        gurobi_options.append(("MIPgap", args.mipgap))
        gurobi_options.append(("SolutionLimit", 1000))

        for produto in produtos_conc:
            for hora in horas_D14:
                if f"rest_fixado_{produto}_{hora}" in modelo.constraints:
                    del modelo.constraints[f"rest_fixado_{produto}_{hora}"]
                if f"rest_fixado2_{produto}_{hora}" in modelo.constraints:
                    del modelo.constraints[f"rest_fixado2_{produto}_{hora}"]

        for v in modelo.variables():
            if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
                v.setInitialValue(v.lowBound)
            elif v.upBound is not None and v.varValue > v.upBound - 0.001:
                v.setInitialValue(v.upBound)
            else:
                v.setInitialValue(v.varValue)

        # Aproveitar valor da memória
        # solver.optionsDict['warmStart'] = True
        nome_arquivo_log_solver = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_solver_completo', 'log', not args.nao_sobrescrever_arquivos)
        solver.optionsDict['logPath'] = nome_arquivo_log_solver
        # print("RODANDO NOVAMENTE O MODELO")
        solver.solve(modelo)

        tempo_modelo_completo = modelo.solutionTime
        valor_fo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo = verifica_status_solucao(nome_arquivo_log_solver)

    return valor_fo_modelo_relaxado, tempo_modelo_relaxado, gap_modelo_relaxado, valor_fo_modelo_completo, tempo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo, nome_arquivo_log_solver

try:
    parser = argparse.ArgumentParser(description='Otimizador Plano Semanal')
    parser.add_argument('-n', '--nome', default='cenario', type=str, help='Nome do cenário (usado para os arquivos de saída gerados)')
    parser.add_argument('-s', '--solver', default='GUROBI_CMD', type=str, help='Nome do otimizador a ser usado')
    parser.add_argument('-c', '--cenario', default='../instancias/template_input.xlsx', type=str, help='Caminho para a planilha com o cenário a ser experimentado')
    parser.add_argument('-o', '--pasta-saida', default='experimentos', type=str, help='Pasta onde serão salvos os arquivos de resultados')
    parser.add_argument('-w', '--nao-sobrescrever-arquivos', action='store_true', help='Não sobrescreve os arquivos de saída (gera novos com contador)')
    parser.add_argument('-q', '--verificar-qualidade', action='store_true', help='Indica se a qualidade será verificada na fase de pré-processamento')
    parser.add_argument('-f', '--funcao-objetivo', default='[max_pelot]', type=str, help='Função objetivo utilizada (qualquer combinação de: [max_brit, max_conc, max_pelot, min_atr_nav])')
    parser.add_argument('-g', '--mipgap', default=0.01, type=float, help='Valor % de GAP provado para a solução ótima (0.1 = 10%).')
    parser.add_argument('-t', '--limite-tempo', default=600, type=float, help='Limite de tempo do solver em segundos.')
    parser.add_argument('-l', '--log-level', default='INFO', type=str, help='Nível de log gerado')
    parser.add_argument('-v', '--version', action='store_true', help='Exibe a versão do otimizador')
    parser.add_argument('--desab-verif-inviabilidade', action='store_true', help='Desabilita análise de inviabilidade do modelo (computar IIS)')
    parser.add_argument('--gurobi-path', default='C:/gurobi1002/win64', type=str, help='Pasta onde o Gurobi está instalado para encontrar as restrições que inviabilizam o modelo, se necessário')
    parser.add_argument('--heuristica-relax-and-fix', action='store_true', help='Habilita a heurística Relax And Fix das variáveis do mineroduto')
    parser.add_argument('--heuristica-otim-partes', action='store_true', help='Habilita a heurística de otimização por partes')
    parser.add_argument('--param-adicionais', default=None, type=str, help='Arquivo JSON com parâmetros adicionais para o solver (Heurística, pesos FO, etc.)')
    parser.add_argument('--gurobi-options', default=None, type=str, help='Define as opções do Gurobi (se não informado, usa apenas MipFocus=1)')
    parser.add_argument('--arquivo-sumario', default=None, type=str, help='Caminho para arquivo CSV de sumarização (acrescenta uma linha no arquivo com os dados dessa execução)')

    args = parser.parse_args()

    if args.version:
        print(f'Otimizador Versão: {VERSAO_OTIMIZADOR} Data: {DATA_VERSAO}')
        exit(0)
    else:
        print('******** EXECUTANDO OTIMIZADOR ********')

    #------------------------------------------------------------------------------

    logging.basicConfig(level=args.log_level,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    logger = logging.getLogger(__name__)

    logger.info(f'>> Versão: {VERSAO_OTIMIZADOR}    <<')
    logger.info(f'>> Data: {DATA_VERSAO} <<')

    # -----------------------------------------------------------------------------
    # Lendos parâmetros do modelo da planilha informada

    # Cria a pasta com os resultados dos experimentos se ainda não existir
    if not os.path.exists(args.pasta_saida):
        os.makedirs(args.pasta_saida)

    # Obtém apenas o nome do arquivo da planilha, ignorando a pasta e a extensão
    nome_instancia = os.path.splitext(os.path.basename(args.cenario))[0]
    # Cria a pasta para salvar o arquivo, se ainda não existir
    if not os.path.exists(args.pasta_saida):
        os.makedirs(args.pasta_saida)

    nome_arquivo_parametros = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_parametros', 'json', not args.nao_sobrescrever_arquivos)

    # lê os parâmetros do problema a partir da planilha de entrada
    parametros = instance_reader.extrair_parametros(args.cenario, logger, nome_arquivo_parametros)

    if 'ERRO' in parametros:
        logger.error(f'Dados informados na planilha estão inconsistentes. Verifique o log para mais informações.')
        exit(0)

    # Ajuste no bombeado (tem na planilha de programação 'Polpa Ubu (65Hs) - AJUSTE', mas ainda não na planilha do Derval)
    ajuste_polpa_Ubu = 0

    # Alguns parâmetros são salvos em variáveis por legibilidade

    hora_inicio_programacao = parametros['config']['hora_inicio_programacao']

    dias      = parametros['config']['dias']
    horas_D14 = parametros['config']['horas_D14']
    horas_Dm3 = parametros['config']['horas_Dm3']
    horas_Dm3_D14 = parametros['config']['horas_Dm3_D14']

    produtos_britagem = parametros['produtos']['britagem']
    produtos_mina     =  parametros['produtos']['mina']
    produtos_conc     =  parametros['produtos']['conc']
    produtos_usina    =  parametros['produtos']['usina']
    elem_qualidade    =  parametros['produtos']['elem_qualidade']
    de_para_produtos_mina_conc = parametros['produtos']['de_para_produtos_mina_conc']
    de_para_produtos_conc_usina = parametros['produtos']['de_para_produtos_conc_usina']

    navios = list(parametros['navios'].keys())
    navios_ate_d14 = parametros['navios_ate_d14']
    produtos_de_cada_navio = parametros['produtos_de_cada_navio']

    # -----------------------------------------------------------------------------

    BIG_M = 10e6 # Big M
    BIG_M_MINERODUTO = 10e3 # Big M para a variável binária de bombeado do mineroduto

    opcoes_restricoes = ['fixado_pelo_usuario', 'fixado_pelo_modelo', 'livre']

    resultados_planilha = {}

    # Solver
    logger.info(f'Instanciando solver {args.solver}')

    # MIPFocus=1 prioriza encontrar solução viável
    gurobi_options=[("MIPgap", args.mipgap)]
    if args.gurobi_options:
        # Lê o arquivo JSON com as opções do Gurobi e acrescenta à lista de opções
        with open(args.gurobi_options, 'r') as arquivo:
            options = json.load(arquivo)
            for option in options:
                gurobi_options.append((option, options[option]))
    else:
        gurobi_options.append(("MIPFocus", 1))

    solver = getSolver(args.solver,
                    timeLimit=args.limite_tempo,
                    options=gurobi_options)
    logger.info('[OK]')
    # -----------------------------------------------------------------------------

    logger.info('Criando objeto do modelo de otimização')

    # A variável prob é criada para conter os dados do problema
    modelo = LpProblem("Programacao_Semanal", LpMaximize)

    logger.info('[OK]')

    logger.info('Definindo variáveis e restrições da Britagem e Concentrador')

    # Variável para definir a taxa de produção da britagem, por produto da mina, por hora
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
        # Y_t-1? >= X_t - X_t-1
        # Y_t-1? <= 2 - X_t - X_t-1
        # Y_t-1? <= X_t * M

        # Z_t-1 >= X_t-1 - X_t
        # Z_t-1 <= 2 - X_t - X_t-1
        # Z_t-1 <= X_t-1 * M
        # Z_H'-1 = 0
        for idx_hora in range(1, len(horas_D14)):
            # modelo += (
            #     varInicioCampanhaConcentrador[produto_conc][horas_D14[idx_hora-1]] >=
            #         lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]) -
            #         produto_concentrador_anterior(produto_conc, idx_hora),
            #     f"rest_1_InicioCampanhaConcentrador_{produto_conc}_{horas_D14[idx_hora]}"
            # )
            # modelo += (
            #     varInicioCampanhaConcentrador[produto_conc][horas_D14[idx_hora-1]] <=
            #         2 -
            #         lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]) -
            #         produto_concentrador_anterior(produto_conc, idx_hora),
            #     f"rest_2_InicioCampanhaConcentrador_{produto_conc}_{horas_D14[idx_hora]}"
            # )
            # modelo += (
            #     varInicioCampanhaConcentrador[produto_conc][horas_D14[idx_hora-1]] <=
            #         BIG_M*lpSum([varProdutoConcentrador[produto_mina][produto_conc][horas_D14[idx_hora]] for produto_mina in produtos_mina]),
            #     f"rest_3_InicioCampanhaConcentrador_{produto_conc}_{horas_D14[idx_hora]}"
            # )

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

    # Indica a hora de início das manutenções da britagem
    varInicioManutencoesBritagem = LpVariable.dicts("Britagem_Inicio_Manutencao", (range(len(parametros['manutencao']['Britagem3'])), horas_Dm3_D14), 0, 1, LpInteger)

    # Restrição para garantir que a manutenção da britagem se inicia uma única vez e dentro da janela de manutenção
    for idx_manut in range(len(parametros['manutencao']['Britagem3'])):
        idx_hora1_inicio_janela = calcular_hora_pelo_inicio_programacao(
                                    hora_inicio_programacao,
                                    parametros['manutencao']['Britagem3'][idx_manut]['inicio_janela'])
        idx_hora1_fim_janela    = 24 + calcular_hora_pelo_inicio_programacao(
                                    hora_inicio_programacao,
                                    parametros['manutencao']['Britagem3'][idx_manut]['fim_janela'])
        modelo += (
            lpSum([varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(idx_hora1_inicio_janela)]) == 0,
            f"rest_evita_InicioManutencoesBritagem_antesDaJanela_{idx_manut}",
        )
        ultima_hora_inicio_manutencao = idx_hora1_fim_janela-parametros['manutencao']['Britagem3'][idx_manut]['duração']
        modelo += (
            lpSum([varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(idx_hora1_inicio_janela, ultima_hora_inicio_manutencao+1)]) == 1,
            f"rest_define_InicioManutencoesBritagem_{idx_manut}",
        )
        modelo += (
            lpSum([varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(ultima_hora_inicio_manutencao+1, len(horas_D14))]) == 0,
            f"rest_evita_InicioManutencoesBritagem_depoisDaJanela_{idx_manut}",
        )

    # Restrições para evitar que manutenções ocorram ao mesmo tempo
    for idx_hora in range(len(horas_D14)):
        for idx_manut in range(len(parametros['manutencao']['Britagem3'])):
            modelo += (
                varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]] +
                lpSum(varInicioManutencoesBritagem[s][horas_D14[j]]
                    for j in range(idx_hora - parametros['manutencao']['Britagem3'][idx_manut]['duração'] + 1, idx_hora + 1)
                    for s in range(len(parametros['manutencao']['Britagem3']))
                    if s != idx_manut
                    )
                <= 1,
                f"rest_separa_manutencoesBritagem_{idx_manut}_{idx_hora}",
            )

    # Fixa o horário de início da manutenção do britagem se foi escolhido pelo usuário
    for idx_manut, manutencao in enumerate(parametros['manutencao']['Britagem3']):
        if not manutencao['hora_inicio'] is None:
            idx_hora1_dia = calcular_hora_pelo_inicio_programacao(hora_inicio_programacao,
                                                            parametros['manutencao']['Britagem3'][idx_manut]['inicio_janela'])
            idx_hora = int(idx_hora1_dia + parametros['manutencao']['Britagem3'][idx_manut]['hora_inicio'])
            modelo += (
                varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]] == 1,
                f"rest_fixa_InicioManutencaoBritagem_{idx_manut}",
            )

    # Restrição tratar manutenção, lower bound e valor fixo de taxa de produção da britagem

    for idx_hora in range(len(horas_D14)):
        # se está em manutenção, limita a taxa de produção da britagem
        for idx_manut in range(len(parametros['manutencao']['Britagem3'])):
            modelo += (
                lpSum([varTaxaBritagem[produto][horas_D14[idx_hora]] for produto in produtos_mina])
                    <= parametros['calculados']['Taxa_Prod_Brit3'][extrair_dia(horas_D14[idx_hora])]*(
                            1 -
                            parametros['manutencao']['Britagem3'][idx_manut]['impacto_DF'] *
                                lpSum(varInicioManutencoesBritagem[idx_manut][horas_D14[j]]
                                      for j in range(idx_hora - parametros['manutencao']['Britagem3'][idx_manut]['duração'] + 1, idx_hora + 1))
                            ),
                    f"rest_manutencao_britagem_{idx_manut}_{horas_D14[idx_hora]}",
            )

        # Define lower bound
        # (não parece ser necessário, pois não há limite mínimo da britagem)
        # modelo += (
        #     varTaxaBritagem[horas_D14[idx_hora]] >= 0 # min_taxa_britagem
        #                                         - BIG_M*(lpSum(varInicioManutencoesBritagem[idx_manut][horas_D14[j]]
        #                                                     for idx_manut in range(len(parametros['manutencao']['Britagem3']))
        #                                                     for j in range(idx_hora - parametros['manutencao']['Britagem3'][idx_manut]['duração'] + 1, idx_hora + 1))),
        #     f"rest_LB_taxa_alim1_{horas_D14[idx_hora]}",
        # )

    # Indica a hora de início das manutenções do concentrador
    varInicioManutencoesConcentrador = LpVariable.dicts("Concentrador_Inicio_Manutencao", (range(len(parametros['manutencao']['Concentrador3'])), horas_Dm3_D14), 0, 1, LpInteger)

    # Restrição para garantir que a manutenção do concentrador se inicia uma única vez, e dentro da janela de manutenção
    for idx_manut in range(len(parametros['manutencao']['Concentrador3'])):
        idx_hora1_inicio_janela = calcular_hora_pelo_inicio_programacao(
                                    hora_inicio_programacao,
                                    parametros['manutencao']['Concentrador3'][idx_manut]['inicio_janela'])
        idx_hora1_fim_janela    = 24 + calcular_hora_pelo_inicio_programacao(
                                    hora_inicio_programacao,
                                    parametros['manutencao']['Concentrador3'][idx_manut]['fim_janela'])
        modelo += (
            lpSum([varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(idx_hora1_inicio_janela)]) == 0,
            f"rest_evita_InicioManutencoesConcentrador_antesDaJanela_{idx_manut}",
        )
        ultima_hora_inicio_manutencao = idx_hora1_fim_janela-parametros['manutencao']['Concentrador3'][idx_manut]['duração']
        modelo += (
            lpSum([varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(idx_hora1_inicio_janela, ultima_hora_inicio_manutencao+1)]) == 1,
            f"rest_define_InicioManutencoesConcentrador_{idx_manut}",
        )
        modelo += (
            lpSum([varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(ultima_hora_inicio_manutencao+1, len(horas_D14))]) == 0,
            f"rest_evita_InicioManutencoesConcentrador_depoisDaJanela_{idx_manut}",
        )

    # Restrições para evitar que manutenções ocorram ao mesmo tempo
    for idx_hora in range(len(horas_D14)):
        for idx_manut in range(len(parametros['manutencao']['Concentrador3'])):
            modelo += (
                varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]] +
                lpSum(varInicioManutencoesConcentrador[s][horas_D14[j]]
                    for j in range(idx_hora - parametros['manutencao']['Concentrador3'][idx_manut]['duração'] + 1, idx_hora + 1)
                    for s in range(len(parametros['manutencao']['Concentrador3']))
                    if s != idx_manut
                    )
                <= 1,
                f"rest_separa_manutencoesConcentrador_{idx_manut}_{idx_hora}",
            )

    # Fixa o horário de início da manutenção do concentrador se foi escolhido pelo usuário
    for idx_manut, manutencao in enumerate(parametros['manutencao']['Concentrador3']):
        if not manutencao['hora_inicio'] is None:
            idx_hora1_dia = calcular_hora_pelo_inicio_programacao(hora_inicio_programacao,
                                                            parametros['manutencao']['Concentrador3'][idx_manut]['inicio_janela'])
            idx_hora = int(idx_hora1_dia + parametros['manutencao']['Concentrador3'][idx_manut]['hora_inicio'])
            modelo += (
                varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]] == 1,
                f"rest_fixa_InicioManutencaoConcentrador_{idx_manut}",
            )

    # Restrição tratar manutenção, lower bound e valor fixo de taxa de alimentação

    if parametros['config']['config_Taxa_C3'] == 'fixado_pelo_modelo':
        varTaxaAlimFixa = LpVariable("Concentrador_Taxa_Alimentacao_Fixa", 0, parametros['capacidades']['Taxa_C3']['max'], LpContinuous)

    for idx_hora in range(len(horas_D14)):
        # se está em manutenção, limita a taxa de alimentação
        for idx_manut in range(len(parametros['manutencao']['Concentrador3'])):
            modelo += (
                lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
                    <= parametros['capacidades']['Taxa_C3']['max']*(
                            1 -
                            parametros['manutencao']['Concentrador3'][idx_manut]['impacto_DF'] *
                            lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
                                  for j in range(idx_hora - parametros['manutencao']['Concentrador3'][idx_manut]['duração'] + 1, idx_hora + 1))
                        ),
                f"rest_manutencao_concentrador_{idx_manut}_{horas_D14[idx_hora]}",
            )

        # Define lower bound
        modelo += (
            lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
                >= parametros['capacidades']['Taxa_C3']['min']
                - BIG_M*(lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
                               for idx_manut in range(len(parametros['manutencao']['Concentrador3']))
                               for j in range(idx_hora - parametros['manutencao']['Concentrador3'][idx_manut]['duração'] + 1, idx_hora + 1))),
            f"rest_LB_taxa_alim1_{horas_D14[idx_hora]}",
        )
        # modelo += (
        #     lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
        #         <= BIG_M*(1 - lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
        #                             for idx_manut in range(len(parametros['manutencao']['Concentrador3']))
        #                             for j in range(idx_hora - parametros['manutencao']['Concentrador3'][idx_manut]['duração'] + 1, idx_hora + 1))),
        #     f"rest_LB_taxa_alim2_{horas_D14[idx_hora]}",
        # )

        # se a taxa de alimentacao é fixada pelo modelo ou pelo usuário
        if parametros['config']['config_Taxa_C3'] in ['fixado_pelo_modelo','fixado_pelo_usuario']:
            taxa_fixa = parametros['config']['config_valor_Taxa_C3']
            if parametros['config']['config_Taxa_C3'] == 'fixado_pelo_modelo':
                taxa_fixa = varTaxaAlimFixa
            modelo += (
                lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
                    >= taxa_fixa
                       - BIG_M*(lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
                                      for idx_manut in range(len(parametros['manutencao']['Concentrador3']))
                                      for j in range(idx_hora - parametros['manutencao']['Concentrador3'][idx_manut]['duração'] + 1, idx_hora + 1))),
                f"rest_taxa_alim_fixa1_{horas_D14[idx_hora]}",
            )
            # modelo += (
            #     lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
            #         <= BIG_M*(1 - lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
            #                             for idx_manut in range(len(parametros['manutencao']['Concentrador3']))
            #                             for j in range(idx_hora - parametros['manutencao']['Concentrador3'][idx_manut]['duração'] + 1, idx_hora + 1))),
            #     f"rest_taxa_alim_fixa2_{horas_D14[idx_hora]}",
            # )
            modelo += (
                lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc]) <= taxa_fixa,
                f"rest_taxa_alim_fixa3_{horas_D14[idx_hora]}",
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

    logger.info('[OK]')

    logger.info('Definindo variáveis e restrições dos Estoques EB06 e EB04')

    # Indica o estoque EB06, por hora
    varEstoqueEB06 = LpVariable.dicts("EB06_Estoque", (produtos_conc, horas_D14), 0, None, LpContinuous)
    varEstoqueEB04 = LpVariable.dicts("EB04_Estoque", (produtos_conc, horas_D14), 0, None, LpContinuous)

    # Restrição de capacidade do estoque EB06
    for hora in horas_D14:
        modelo += (
            lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc)
                <= parametros['capacidades']['EB6']['max'],
            f"rest_capacidade_EstoqueEB06_{hora}",
        )

    # Restrição de capacidade do estoque EB04
    for hora in horas_D14:
        modelo += (
            lpSum(varEstoqueEB04[produto][hora] for produto in produtos_conc)
                <= parametros['capacidades']['EB4']['max'],
            f"rest_capacidade_EstoqueEB04_{hora}",
        )

    # Define se ha transferencia entre os tanques
    varEnvioEB04EB06 = LpVariable.dicts("EB04_envio_para_EB06", (produtos_conc, horas_D14), 0, 1, LpInteger)
    varEnvioEB06EB04 = LpVariable.dicts("EB06_envio_para_EB04", (produtos_conc, horas_D14), 0, 1, LpInteger)
    # Define a quantidade da transferência entre os tanques
    varTaxaEnvioEB04EB06 = LpVariable.dicts("EB04_taxa_envio_EB06", (produtos_conc, horas_D14), 0, parametros['config']['taxa_max_transferencia_entre_eb6_eb4'], LpContinuous)
    varTaxaEnvioEB06EB04 = LpVariable.dicts("EB06_taxa_envio_EB04", (produtos_conc, horas_D14), 0, parametros['config']['taxa_max_transferencia_entre_eb6_eb4'], LpContinuous)

    # Indica se há bombeamento de polpa a partir do EB06 em cada hora
    if args.heuristica_relax_and_fix and args.heuristica_otim_partes:
        raise Exception('Não é possível rodar as heurísticas Relax And Fix e Otimizador por Partes ao mesmo tempo!')
    elif not (args.heuristica_relax_and_fix or args.heuristica_otim_partes):
        varBombeamentoPolpaEB06 = LpVariable.dicts("Mineroduto_Bombeamento_Polpa_EB06", (produtos_conc, horas_Dm3_D14), 0, 1, LpInteger)
    else: # Se for rodar a heurística, a variável é relaxada
        varBombeamentoPolpaEB06 = LpVariable.dicts("Mineroduto_Bombeamento_Polpa_EB06", (produtos_conc, horas_Dm3_D14), 0, 1, LpContinuous)

    for produto in produtos_conc:
        for hora in horas_D14:
            modelo += (
                varTaxaEnvioEB06EB04[produto][hora] <= parametros['config']['taxa_max_transferencia_entre_eb6_eb4']*varEnvioEB06EB04[produto][hora],
                f"rest_define_TaxaEnvioEB06EB04_{produto}_{hora}",
            )
            modelo += (
                varTaxaEnvioEB04EB06[produto][hora] <= parametros['config']['taxa_max_transferencia_entre_eb6_eb4']*varEnvioEB04EB06[produto][hora],
                f"rest_define_TaxaEnvioEB04EB06_{produto}_{hora}",
            )

    # Define o valor de estoque de EB06, por produto, da segunda hora em diante
    for produto in produtos_conc:
        for i in range(1, len(horas_D14)):
            modelo += (
                varEstoqueEB06[produto][horas_D14[i]]
                    == varEstoqueEB06[produto][horas_D14[i-1]]
                    + varProducaoVolume[produto][horas_D14[i]]
                    - varBombeamentoPolpaEB06[produto][horas_D14[i]]*parametros['gerais']['Vazao_EB6'][extrair_dia(horas_D14[i])]
                    + varTaxaEnvioEB04EB06[produto][horas_D14[i]]
                    - varTaxaEnvioEB06EB04[produto][horas_D14[i]],
                    # + (varEnvioEB04EB06[produto][horas_D14[i]]-varEnvioEB06EB04[produto][horas_D14[i]])*parametros['config']['taxa_max_transferencia_entre_eb6_eb4'],
                f"rest_define_EstoqueEB06_{produto}_{horas_D14[i]}",
            )

    # Define o valor de estoque de EB06, por produto, da primeira hora
    for produto in produtos_conc:
        modelo += (
            varEstoqueEB06[produto][horas_D14[0]]
                == parametros['estoque_inicial']['EB6'][produto] +
                varProducaoVolume[produto][horas_D14[0]] -
                varBombeamentoPolpaEB06[produto][horas_D14[0]]*parametros['gerais']['Vazao_EB6'][extrair_dia(horas_D14[0])]
                + varTaxaEnvioEB04EB06[produto][horas_D14[0]]
                    - varTaxaEnvioEB06EB04[produto][horas_D14[0]],
                # +(varEnvioEB04EB06[produto][horas_D14[0]] - varEnvioEB06EB04[produto][horas_D14[0]])*parametros['config']['taxa_max_transferencia_entre_eb6_eb4'],
            f"rest_define_EstoqueEB06_{produto}_{horas_D14[0]}",
        )

    # Define o valor de estoque de EB04, por produto, da segunda hora em diante
    for produto in produtos_conc:
        for i in range(1, len(horas_D14)):
            modelo += (
                varEstoqueEB04[produto][horas_D14[i]]
                    == varEstoqueEB04[produto][horas_D14[i-1]]
                    - varTaxaEnvioEB04EB06[produto][horas_D14[i]]
                    + varTaxaEnvioEB06EB04[produto][horas_D14[i]],
                    # + (varEnvioEB06EB04[produto][horas_D14[i]] - varEnvioEB04EB06[produto][horas_D14[i]])*parametros['config']['taxa_max_transferencia_entre_eb6_eb4'],
                f"rest_define_EstoqueEB04_{produto}_{horas_D14[i]}",
            )

    # Define o valor de estoque de EB04, por produto, da primeira hora
    for produto in produtos_conc:
        modelo += (
            varEstoqueEB04[produto][horas_D14[0]]
                == parametros['estoque_inicial']['EB4'][produto] +
                    - varTaxaEnvioEB04EB06[produto][horas_D14[0]]
                    + varTaxaEnvioEB06EB04[produto][horas_D14[0]],
                    # (varEnvioEB06EB04[produto][horas_D14[0]] - varEnvioEB04EB06[produto][horas_D14[0]])*parametros['config']['taxa_max_transferencia_entre_eb6_eb4'],
            f"rest_define_EstoqueEB04_{produto}_{horas_D14[0]}",
        )

    # Restrição de transferência em unico sentido
    for hora in horas_D14:
        modelo += (
            lpSum(varEnvioEB04EB06[produto][hora] + varEnvioEB06EB04[produto][hora] for produto in produtos_conc) <= 1,
            f"rest_tranferencia_sentido_unico_{hora}",
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


    if parametros['config']['config_janela_bombeamento_agua'] == 'fixado_pelo_usuario':

        # limite_hora = -parametros['config']['config_valor_janela_bombeamento_agua']
        limite_hora = parametros['config']['config_janela_total_fixar_bombeamento_agua'] - parametros['config']['config_valor_janela_bombeamento_agua']
        #for produto in produtos_conc:
        for i, hora in enumerate(horas_D14[0:limite_hora]):
            modelo += (
                lpSum(varBombeamentoPolpaEB06[produto][horas_D14[i]] for produto in produtos_conc) +
                    lpSum([varBombeamentoPolpaEB06[produto][horas_D14[j]] for produto in produtos_conc for j in range(i+1, i+parametros['config']['config_valor_janela_bombeamento_agua'])]) <=
                        parametros['config']['config_valor_janela_bombeamento_agua']*(1 + lpSum(varBombeamentoPolpaEB06[produto][horas_D14[i]]for produto in produtos_conc) - lpSum(bombeamento_hora_anterior(produto, i) for produto in produtos_conc)),

                f"rest_parametros['config']['config_janela_bombeamento_agua']_{produto}_{hora}",
            )

        #for produto in produtos_conc:
        for i, hora in enumerate(horas_D14[0:limite_hora]):
            modelo += (
                lpSum(varBombeamentoPolpaEB06[produto][horas_D14[i+parametros['config']['config_valor_janela_bombeamento_agua']]] for produto in produtos_conc) >=
                -lpSum(varBombeamentoPolpaEB06[produto][horas_D14[i]] for produto in produtos_conc) + lpSum(bombeamento_hora_anterior(produto, i)for produto in produtos_conc),
                f"rest_retornar_bombeamento_polpa_{produto}_{hora}",
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

    # Indica a hora de início das manutenções do mineroduto
    varInicioManutencoesMineroduto = LpVariable.dicts("Mineroduto_Inicio_Manutencao", (range(len(parametros['manutencao']['Mineroduto3'])), horas_Dm3_D14), 0, 1, LpInteger)

    # Restrição para garantir que a manutenção do mineroduto se inicia uma única vez, e dentro da janela de manutenção
    for idx_manut in range(len(parametros['manutencao']['Mineroduto3'])):
        idx_hora1_inicio_janela = calcular_hora_pelo_inicio_programacao(
                                    hora_inicio_programacao,
                                    parametros['manutencao']['Mineroduto3'][idx_manut]['inicio_janela'])
        idx_hora1_fim_janela    = 24 + calcular_hora_pelo_inicio_programacao(
                                    hora_inicio_programacao,
                                    parametros['manutencao']['Mineroduto3'][idx_manut]['fim_janela'])
        modelo += (
            lpSum([varInicioManutencoesMineroduto[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(idx_hora1_inicio_janela)]) == 0,
            f"rest_evita_InicioManutencoesMineroduto_antesDaJanela_{idx_manut}",
        )
        ultima_hora_inicio_manutencao = idx_hora1_fim_janela-parametros['manutencao']['Mineroduto3'][idx_manut]['duração']
        modelo += (
            lpSum([varInicioManutencoesMineroduto[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(idx_hora1_inicio_janela, ultima_hora_inicio_manutencao+1)]) == 1,
            f"rest_define_InicioManutencoesMineroduto_{idx_manut}",
        )
        modelo += (
            lpSum([varInicioManutencoesMineroduto[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(ultima_hora_inicio_manutencao+1, len(horas_D14))]) == 0,
            f"rest_evita_InicioManutencoesMineroduto_depoisDaJanela_{idx_manut}",
        )

    # Restrições para evitar que manutenções ocorram ao mesmo tempo
    for idx_hora in range(len(horas_D14)):
        for idx_manut in range(len(parametros['manutencao']['Mineroduto3'])):
            modelo += (
                varInicioManutencoesMineroduto[idx_manut][horas_D14[idx_hora]] +
                lpSum(varInicioManutencoesMineroduto[s][horas_D14[j]]
                    for j in range(idx_hora - parametros['manutencao']['Mineroduto3'][idx_manut]['duração'] + 1, idx_hora + 1)
                    for s in range(len(parametros['manutencao']['Mineroduto3']))
                    if s != idx_manut
                    )
                <= 1,
                f"rest_separa_manutencoesMineroduto_{idx_manut}_{idx_hora}",
            )

    # Fixa o horário de início da manutenção do mineroduto se foi escolhido pelo usuário
    for idx_manut, manutencao in enumerate(parametros['manutencao']['Mineroduto3']):
        if not manutencao['hora_inicio'] is None:
            idx_hora1_dia = calcular_hora_pelo_inicio_programacao(hora_inicio_programacao,
                                                            parametros['manutencao']['Mineroduto3'][idx_manut]['inicio_janela'])
            idx_hora = int(idx_hora1_dia + parametros['manutencao']['Mineroduto3'][idx_manut]['hora_inicio'])
            modelo += (
                varInicioManutencoesMineroduto[idx_manut][horas_D14[idx_hora]] == 1,
                f"rest_fixa_InicioManutencaoMineroduto_{idx_manut}",
            )


    # Restrição para zerar o bombeado se o mineroduto está em manutenção
    for produto in produtos_conc:
        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeadoEB07[produto][horas_D14[idx_hora]] <= BIG_M*(1 -
                                            lpSum(varInicioManutencoesMineroduto[idx_manut][horas_D14[j]]
                                            for idx_manut in range(len(parametros['manutencao']['Mineroduto3']))
                                            for j in range(idx_hora - parametros['manutencao']['Mineroduto3'][idx_manut]['duração'] + 1, idx_hora + 1))),
                f"rest_manutencao_mineroduto_{produto}_{horas_D14[idx_hora]}",
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

    # subject to Producao2i{t in 1..H}: #maximo de 1s
    #    X[1] = 0;
    # Já tratado nas restrições rest_define_Bombeamento_inicial_

    # se a janela de bombeamento é fixada pelo modelo ou pelo usuário
    if parametros['config']['config_janela_bombeamento_polpa'] in ['fixado_pelo_modelo','fixado_pelo_usuario']:
        janela_fixa = parametros['config']['config_valor_janela_bombeamento_polpa']
        if parametros['config']['config_janela_bombeamento_polpa'] == 'fixado_pelo_modelo':
            varJanelaFixaBombeamento = LpVariable("Mineroduto_Janela_Fixa_Polpa",
                                                parametros['config']['janela_min_bombeamento_polpa'], parametros['config']['janela_max_bombeamento_polpa'],
                                                LpInteger)
            janela_fixa = varJanelaFixaBombeamento

        # subject to Producao3a{t in 2..H}: #maximo de 1s
        #    Xf[t] <= TB + (1 - X[t-1] + X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaFinal[horas_D14[idx_hora]] <=
                    janela_fixa + (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)
                                    + lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_3a_{horas_D14[idx_hora]}",
            )

        # subject to Producao3b{t in 2..H}: #maximo de 1s
        #    Xf[t] >= TB - (1 - X[t-1] + X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaFinal[horas_D14[idx_hora]] >=
                    janela_fixa - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)
                                    + lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_3b_{horas_D14[idx_hora]}",
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

    # subject to Producao2i{t in 1..H}: #maximo de 1s
    #    X[1] = 0;
    # Já tratado nas restrições rest_define_Bombeamento_inicial_


    # se a janela de bombeamento é fixada pelo modelo ou pelo usuário
    if parametros['config']['config_janela_bombeamento_agua'] in ['fixado_pelo_modelo','fixado_pelo_usuario']:
        janela_fixa = parametros['config']['config_valor_janela_bombeamento_agua']
        if parametros['config']['config_janela_bombeamento_agua'] == 'fixado_pelo_modelo':
            varJanelaFixaBombeamentoAgua = LpVariable("Mineroduto_Janela_Fixa_Agua",
                                                    parametros['config']['janela_min_bombeamento_agua'], parametros['config']['janela_max_bombeamento_agua'],
                                                    LpInteger)
            janela_fixa = varJanelaFixaBombeamentoAgua

        # subject to Producao3a{t in 2..H}: #maximo de 1s
        #    Xf[t] <= TB + (1 - X[t-1] + X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaFinal[horas_D14[idx_hora]] <=
                    janela_fixa + (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
                                    + (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_agua_3a_{horas_D14[idx_hora]}",
            )

        # subject to Producao3b{t in 2..H}: #maximo de 1s
        #    Xf[t] >= TB - (1 - X[t-1] + X[t])*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaFinal[horas_D14[idx_hora]] >=
                    janela_fixa - (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
                                    + (1 - lpSum(varBombeamentoPolpaEB06[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
                f"rest_seq_bomb_agua_3b_{horas_D14[idx_hora]}",
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
            return parametros['limites_campanhas'][produto_usina]['acum']

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
                    parametros['janelas_campanhas'][produto_usina]['min'] -
                    (1 - varFimCampanhaPelot[produto_usina][hora])*BIG_M,
                    f"rest_limiteMinJanelaCampanhaPelot_{produto_usina}_{hora}",
            )
            modelo += (
                varJanelaProdSemIncorpAcumulada[produto_usina][hora] <=
                    parametros['janelas_campanhas'][produto_usina]['max'],
                    f"rest_limiteMaxJanelaCampanhaPelot_{produto_usina}_{hora}",
            )

    # Indica a hora de início das manutenções da usina
    varInicioManutencoesUsina = LpVariable.dicts("Pelot_Inicio_Manutencao", (range(len(parametros['manutencao']['Pelotização'])), horas_Dm3_D14), 0, 1, LpInteger)

    # Restrição para garantir que a manutenção da pelotização se inicia uma única vez, e dentro da janela de manutenção
    for idx_manut in range(len(parametros['manutencao']['Pelotização'])):
        idx_hora1_inicio_janela = calcular_hora_pelo_inicio_programacao(
                                    hora_inicio_programacao,
                                    parametros['manutencao']['Pelotização'][idx_manut]['inicio_janela'])
        idx_hora1_fim_janela    = 24 + calcular_hora_pelo_inicio_programacao(
                                    hora_inicio_programacao,
                                    parametros['manutencao']['Pelotização'][idx_manut]['fim_janela'])
        modelo += (
            lpSum([varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(idx_hora1_inicio_janela)]) == 0,
            f"rest_evita_InicioManutencoesPelot_antesDaJanela_{idx_manut}",
        )
        ultima_hora_inicio_manutencao = idx_hora1_fim_janela-parametros['manutencao']['Pelotização'][idx_manut]['duração']
        modelo += (
            lpSum([varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(idx_hora1_inicio_janela, ultima_hora_inicio_manutencao+1)]) == 1,
            f"rest_define_InicioManutencoesPelot_{idx_manut}",
        )
        modelo += (
            lpSum([varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]]
                for idx_hora in range(ultima_hora_inicio_manutencao+1, len(horas_D14))]) == 0,
            f"rest_evita_InicioManutencoesPelot_depoisDaJanela_{idx_manut}",
        )

    # Restrições para evitar que manutenções ocorram ao mesmo tempo
    for idx_hora in range(len(horas_D14)):
        for idx_manut in range(len(parametros['manutencao']['Pelotização'])):
            modelo += (
                varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]] +
                lpSum(varInicioManutencoesUsina[s][horas_D14[j]]
                    for j in range(idx_hora - parametros['manutencao']['Pelotização'][idx_manut]['duração'] + 1, idx_hora + 1)
                    for s in range(len(parametros['manutencao']['Pelotização']))
                    if s != idx_manut
                    )
                <= 1,
                f"rest_separa_manutencoesPelot_{idx_manut}_{idx_hora}",
            )

    # Fixa o horário de início da manutenção do usina se foi escolhido pelo usuário
    for idx_manut, manutencao in enumerate(parametros['manutencao']['Pelotização']):
        if not manutencao['hora_inicio'] is None:
            idx_hora1_dia = calcular_hora_pelo_inicio_programacao(hora_inicio_programacao,
                                                            parametros['manutencao']['Pelotização'][idx_manut]['inicio_janela'])
            idx_hora = int(idx_hora1_dia + parametros['manutencao']['Pelotização'][idx_manut]['hora_inicio'])
            modelo += (
                varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]] == 1,
                f"rest_fixa_InicioManutencaoPelot_{idx_manut}",
            )

    # Restrição tratar manutenção, lower bound e valor fixo de produção sem incorporação

    if parametros['config']['config_TaxaAlim_Pelot'] == 'fixado_pelo_modelo':
        varProducaoSemIncorporacaoFixa = LpVariable("Producao sem incorporacao Fixa", 0, parametros['capacidades']['TaxaAlim_Pelot']['max'], LpContinuous)

    for idx_hora in range(len(horas_D14)):
        # se está em manutenção, limita a produção
        for idx_manut in range(len(parametros['manutencao']['Pelotização'])):
            modelo += (
                lpSum([varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] for produto in produtos_usina]) <=
                    parametros['capacidades']['TaxaAlim_Pelot']['max']*(
                        1 -
                        parametros['manutencao']['Pelotização'][idx_manut]['impacto_DF'] *
                        lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
                                for j in range(idx_hora - parametros['manutencao']['Pelotização'][idx_manut]['duração'] + 1, idx_hora + 1))
                    ),
                f"rest_manutencao_Pelot_{produto}_{idx_manut}_{horas_D14[idx_hora]}",
            )

        # Define lower bound
        modelo += (
            lpSum([varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] for produto in produtos_usina])
            >= parametros['capacidades']['TaxaAlim_Pelot']['min']
               - BIG_M*(lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
                              for idx_manut in range(len(parametros['manutencao']['Pelotização']))
                              for j in range(idx_hora - parametros['manutencao']['Pelotização'][idx_manut]['duração'] + 1, idx_hora + 1))),
            f"rest_LB_prod_sem_incorp1_{produto}_{horas_D14[idx_hora]}",
        )
        # modelo += (
        #     varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] <= BIG_M*(1 - lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
        #                                                     for idx_manut in range(len(parametros['manutencao']['Pelotização']))
        #                                                     for j in range(idx_hora - parametros['manutencao']['Pelotização'][idx_manut]['duração'] + 1, idx_hora + 1))),
        #     f"rest_LB_prod_sem_incorp2_{produto}_{horas_D14[idx_hora]}",
        # )

        # se a produção sem incorporação é fixada pelo modelo ou pelo usuário
        if parametros['config']['config_TaxaAlim_Pelot'] in ['fixado_pelo_modelo','fixado_pelo_usuario']:
            taxa_fixa = parametros['config']['config_valor_TaxaAlim_Pelot']
            if parametros['config']['config_TaxaAlim_Pelot'] == 'fixado_pelo_modelo':
                taxa_fixa = varProducaoSemIncorporacaoFixa
            modelo += (
                lpSum([varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] for produto in produtos_usina])
                  >= taxa_fixa
                     - BIG_M*(lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
                                    for idx_manut in range(len(parametros['manutencao']['Pelotização']))
                                    for j in range(idx_hora - parametros['manutencao']['Pelotização'][idx_manut]['duração'] + 1, idx_hora + 1))),
                f"rest_prod_sem_incorp_fixa1_{produto}_{horas_D14[idx_hora]}",
            )
            # modelo += (
            #     lpSum([varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] for produto in produtos_usina]) <= BIG_M*(1 - lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
            #                                                     for idx_manut in range(len(parametros['manutencao']['Pelotização']))
            #                                                     for j in range(idx_hora - parametros['manutencao']['Pelotização'][idx_manut]['duração'] + 1, idx_hora + 1))),
            #     f"rest_prod_sem_incorp_fixa2_{produto}_{horas_D14[idx_hora]}",
            # )
            modelo += (
                lpSum([varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] for produto in produtos_usina]) <= taxa_fixa,
                f"rest_prod_sem_incorp_fixa3_{produto}_{horas_D14[idx_hora]}",
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
                                                    # + lpSum(varVolumePatio[produto][horas_D14[0]]
                                                    #    for produto in produtos_conc)
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
        # print(navio, extrair_hora(parametros['navios'][navio]['Data_chegada']))
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

    logger.info('[OK]')

    # The problem data is written to an .lp file
    # prob.writeLP("PSemanal.lp")

    valor_fo_modelo_completo = None
    tempo_modelo_completo = 0
    status_solucao_modelo_completo = None
    gap_modelo_completo = None

    valor_fo_modelo_relaxado = None
    tempo_modelo_relaxado = 0
    status_solucao_modelo_relaxado = None
    gap_modelo_relaxado = None

    # TODO: remover
    valor_fo_modelo_fixado = None
    tempo_modelo_fixado = 0
    status_solucao_modelo_fixado = None
    gap_modelo_fixado = None

    tempo_inicio_solver = time.time()

    if not (args.heuristica_relax_and_fix or args.heuristica_otim_partes):
        logger.info('RESOLVENDO o modelo')
        nome_arquivo_log_solver = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_solver_completo', 'log', not args.nao_sobrescrever_arquivos)
        solver.optionsDict['logPath'] = nome_arquivo_log_solver
        # The problem is solved using PuLP's choice of Solver
        solver.solve(modelo)
        tempo_modelo_completo = modelo.solutionTime
        valor_fo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo = verifica_status_solucao(nome_arquivo_log_solver)
    elif args.heuristica_otim_partes:
        valor_fo_modelo_relaxado, tempo_modelo_relaxado, gap_modelo_relaxado, valor_fo_modelo_completo, tempo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo, nome_arquivo_log_solver = heuristica_otim_por_partes(modelo, nome_instancia, varBombeamentoPolpaEB06, produtos_conc, horas_D14, solver, args)
    elif args.heuristica_relax_and_fix:
        valor_fo_modelo_relaxado, tempo_modelo_relaxado, gap_modelo_relaxado, valor_fo_modelo_completo, tempo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo, nome_arquivo_log_solver = heuristica_relax_and_fix(modelo, gurobi_options, nome_instancia, parametros, varBombeamentoPolpaEB06, produtos_conc, horas_D14, solver, args)

    nome_arquivo_ILP = None
    restricoes_limitantes = None
    variaveis_limitantes = None
    if status_solucao_modelo_completo == 'Infeasible':
        if args.desab_verif_inviabilidade:
            logger.info(f'Dica: execute script sem a opção --desab-verif-inviabilidade para obter mais informações')
        else:
            logger.info(f'Escrevendo modelo em arquivo para procurar por restrições que inviabilizam o modelo')
            nome_arquivo_MPS = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_modelo', 'mps', not args.nao_sobrescrever_arquivos)
            modelo.writeMPS(nome_arquivo_MPS)

            logger.info(f'Computando IIS!')
            nome_arquivo_ILP = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_IISresults', 'ilp', not args.nao_sobrescrever_arquivos)
            os.system(f'{args.gurobi_path}/bin/gurobi_cl TimeLimit={args.limite_tempo} ResultFile={nome_arquivo_ILP} {nome_arquivo_MPS}')

            if not os.path.exists(nome_arquivo_ILP):
                logger.warning(f'Não foi possível obter arquivo ILP do IIS!')
            else:
                arquivoILP = open(nome_arquivo_ILP)
                prefixo_variaveis = ['Britagem', 'Concentrador', 'EB04', 'EB06', 'EB07', 'Mineroduto', 'Pelot', 'Porto', 'Praca', 'Ubu']
                restricoes_limitantes = set()
                variaveis_limitantes = set()
                lendo_restricoes = True
                for linha in arquivoILP.readlines():
                    linha = linha.strip()
                    if lendo_restricoes:
                        if linha.startswith('rest_'):
                            restricoes_limitantes.add(linha.split()[0][:-1])
                        elif linha == 'Bounds':
                            lendo_restricoes = False
                    else:
                        for prefixo_variavel in prefixo_variaveis:
                            if linha.startswith(prefixo_variavel):
                                variaveis_limitantes.add(linha.split()[0])
                arquivoILP.close()

                def remover_sufixo_horas(conjunto_completo):
                    conjunto = set()
                    for rest_ou_variavel in conjunto_completo:
                        pos_underscore = rest_ou_variavel.rfind('_')
                        pos_underscore = rest_ou_variavel[:pos_underscore].rfind('_')
                        if rest_ou_variavel[pos_underscore+1:] in horas_Dm3_D14:
                            conjunto.add(rest_ou_variavel[:pos_underscore])
                        else:
                            conjunto.add(rest_ou_variavel)
                    lista = list(conjunto)
                    lista.sort()
                    return lista

                restricoes_limitantes = remover_sufixo_horas(restricoes_limitantes)
                variaveis_limitantes = remover_sufixo_horas(variaveis_limitantes)

                logger.warning(f'RESTRIÇÕES que inviabilizam o modelo: {restricoes_limitantes}')
                logger.warning(f'VARIÁVEIS cujos limites inviabilizam o modelo: {variaveis_limitantes}')
                logger.info(f'Veja informações mais detalhadas no arquivo {nome_arquivo_ILP}')

    ## Tratando qualidade ####

    # Se encontrou alguma solução
    if args.verificar_qualidade and LpStatus[modelo.status] == 'Optimal':

        logger.info('Pós-processamento: verificando os limites de qualidade')

        def listaParaDicionarioHoras(lista):
            return {horas_D14[idx]: valor for idx, valor in enumerate(lista)}

        def converteHorasDicionario(dicionario):
            ''' Converte um dicionario de produtos: lista de horas para produtos e dicionários de horas'''
            return {chave: listaParaDicionarioHoras(dicionario[chave]) for chave in dicionario}

        # PREMISSAS DO CÁLCULO DE QUALIDADE

        # O modelo vai encontrar uma solução sem calcular a qualidade.
        # - Em uma etapa de pós-processamento, usaremos a solução do modelo para calcular o
        #   blending de qualidade em todas as etapas do processo.
        # - Onde o valor de qualidade ficar fora da especificação de valores mínimos e máximos
        #   a ferramenta mostrará para o usuário.

        # - Consideramos uma aproximação ao tratar o blending de qualidade nos estoques:
        #   Assumimos que, a cada período, todo o material chega no início e sai ao final.
        #   Portanto, o blending de qualidade é dado pela massa que chega (não considera o que sai).

        #===================== Calcula a qualidade dos estoques EB06 e EB04 =======================#

        logger.info('Verificando qualidade dos Estoques EB06 e EB04')

        qualidadeEB06 = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_conc} for elem in elem_qualidade}
        qualidadeEB04 = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_conc} for elem in elem_qualidade}

        verif_qualidade_EB06 = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_conc} for elem in elem_qualidade}
        verif_qualidade_EB04 = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_conc} for elem in elem_qualidade}

        for elem in elem_qualidade:
            for produto in produtos_conc:
                massa_blendagem = (parametros['estoque_inicial']['EB6'][produto] +
                                   varProducaoVolume[produto][horas_D14[0]].varValue +
                                   varTaxaEnvioEB04EB06[produto][horas_D14[0]].varValue)
                # print(f"{elem} {produto} {horas_D14[0]} = ")
                if round(massa_blendagem,1) > 0:
                    qualidadeEB06[elem][produto][horas_D14[0]] = (
                        parametros['estoque_inicial']['EB6'][produto]*parametros['qualidade_inicial']['EB6'][elem][produto] +
                        varProducaoVolume[produto][horas_D14[0]].varValue*parametros['alvo'][elem][produto] +
                        varTaxaEnvioEB04EB06[produto][horas_D14[0]].varValue*parametros['qualidade_inicial']['EB4'][elem][produto]
                        )/massa_blendagem
                    # print(f"    {estoque_eb06_d0[produto]*parametros['qualidade_inicial']['EB6'][elem][produto]}")
                    # print(f"  + {varProducaoVolume[produto][horas_D14[0]].varValue*parametros['alvo'][elem][produto]}")
                    # print(f"  + {varTaxaEnvioEB04EB06[produto][horas_D14[0]].varValue*parametros['qualidade_inicial']['EB4'][elem][produto]}")
                    # print(f"  / {massa_blendagem}")
                    # print(f"  = {qualidadeEB06[elem][produto][horas_D14[0]]}")

                    # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                    if parametros['lim_min'][elem][produto] >  round(qualidadeEB06[elem][produto][horas_D14[0]],4):
                        verif_qualidade_EB06[elem][produto][horas_D14[0]] = -1
                    elif parametros['lim_max'][elem][produto] < round(qualidadeEB06[elem][produto][horas_D14[0]],4):
                        verif_qualidade_EB06[elem][produto][horas_D14[0]] = 1
                    if verif_qualidade_EB06[elem][produto][horas_D14[0]] != 0:
                        logger.debug(f"Qualidade EB06_Estoque fora da especificação: {elem} {produto} {horas_D14[0]} {qualidadeEB06[elem][produto][horas_D14[0]]}")
                # else:
                #     print(f" Estoque anterior + o que chegou = 0 - qualidade {qualidadeEB06[elem][produto][horas_D14[i]]}")

                # if (qualidadeEB06[elem][produto][horas_D14[i]] != parametros['alvo'][elem][produto]):
                #     print("BLENDING")

        for elem in elem_qualidade:
            for produto in produtos_conc:
                massa_blendagem = (parametros['estoque_inicial']['EB4'][produto] +
                                   varTaxaEnvioEB06EB04[produto][horas_D14[0]].varValue)
                # print(f"{elem} {produto} {horas_D14[0]} = ")
                if round(massa_blendagem,1) > 0:
                    qualidadeEB04[elem][produto][horas_D14[0]] = (
                        parametros['estoque_inicial']['EB4'][produto]*parametros['qualidade_inicial']['EB4'][elem][produto] +
                        varTaxaEnvioEB06EB04[produto][horas_D14[0]].varValue*parametros['qualidade_inicial']['EB6'][elem][produto]
                        )/massa_blendagem
                    # print(f"    {parametros['estoque_inicial']['EB4'][produto]*parametros['qualidade_inicial']['EB4'][elem][produto]}")
                    # print(f"  + {varTaxaEnvioEB06EB04[produto][horas_D14[0]].varValue*parametros['qualidade_inicial']['EB6'][elem][produto]}")
                    # print(f"  / {massa_blendagem}")
                    # print(f"  = {qualidadeEB04[elem][produto][horas_D14[0]]}")

                    # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                    if parametros['lim_min'][elem][produto] >  round(qualidadeEB04[elem][produto][horas_D14[0]],4):
                        verif_qualidade_EB04[elem][produto][horas_D14[0]] = -1
                    elif parametros['lim_max'][elem][produto] < round(qualidadeEB04[elem][produto][horas_D14[0]],4):
                        verif_qualidade_EB04[elem][produto][horas_D14[0]] = 1
                    if verif_qualidade_EB04[elem][produto][horas_D14[0]] != 0:
                        logger.debug(f"Qualidade EB04_Estoque fora da especificação: {elem} {produto} {horas_D14[0]} {qualidadeEB04[elem][produto][horas_D14[0]]}")
                # else:
                #     print(f" Estoque anterior + o que chegou = 0 - qualidade {qualidadeEB04[elem][produto][horas_D14[i]]}")

                # if (qualidadeEB04[elem][produto][horas_D14[i]] != parametros['alvo'][elem][produto]):
                #     print("BLENDING")

        for elem in elem_qualidade:
            for produto in produtos_conc:
                for i in range(1, len(horas_D14)):
                    massa_blendagemEB06 = (varEstoqueEB06[produto][horas_D14[i-1]].varValue +
                                    varProducaoVolume[produto][horas_D14[i]].varValue +
                                    varTaxaEnvioEB04EB06[produto][horas_D14[i]].varValue)
                    # print(f"EB06 {elem} {produto} {horas_D14[i]} = ")
                    if round(massa_blendagemEB06,1) > 0:
                        qualidadeEB06[elem][produto][horas_D14[i]] = (
                            varEstoqueEB06[produto][horas_D14[i-1]].varValue*qualidadeEB06[elem][produto][horas_D14[i-1]] +
                            varProducaoVolume[produto][horas_D14[i]].varValue*parametros['alvo'][elem][produto] +
                            varTaxaEnvioEB04EB06[produto][horas_D14[i]].varValue*qualidadeEB04[elem][produto][horas_D14[i-1]]
                            )/massa_blendagemEB06
                        # print(f"    {varEstoqueEB06[produto][horas_D14[i-1]].varValue*qualidadeEB06[elem][produto][horas_D14[i-1]]}")
                        # print(f"  + {varProducaoVolume[produto][horas_D14[i]].varValue*parametros['alvo'][elem][produto]}")
                        # print(f"  + {varTaxaEnvioEB04EB06[produto][horas_D14[i]].varValue*qualidadeEB04[elem][produto][horas_D14[i-1]]}")
                        # print(f"  / {massa_blendagemEB06}")
                        # print(f"  = {qualidadeEB06[elem][produto][horas_D14[i]]}")

                        # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                        if parametros['lim_min'][elem][produto] >  round(qualidadeEB06[elem][produto][horas_D14[i]],4):
                            verif_qualidade_EB06[elem][produto][horas_D14[i]] = -1
                        elif parametros['lim_max'][elem][produto] < round(qualidadeEB06[elem][produto][horas_D14[i]],4):
                            verif_qualidade_EB06[elem][produto][horas_D14[i]] = 1
                        if verif_qualidade_EB06[elem][produto][horas_D14[i]] != 0:
                            logger.debug(f"Qualidade EB06_Estoque fora da especificação: {elem} {produto} {horas_D14[i]} {qualidadeEB06[elem][produto][horas_D14[i]]}")
                    # else:
                    #     print(f"EB06 Estoque anterior + o que chegou = 0 - qualidade {qualidadeEB06[elem][produto][horas_D14[i]]}")

                    # if (qualidadeEB06[elem][produto][horas_D14[i]] != parametros['alvo'][elem][produto]):
                    #     print("BLENDING")

                    massa_blendagemEB04 = (varEstoqueEB04[produto][horas_D14[i-1]].varValue +
                                    varTaxaEnvioEB06EB04[produto][horas_D14[i]].varValue)
                    # print(f"EB04 {elem} {produto} {horas_D14[i]} = ")
                    if round(massa_blendagemEB04,1) > 0:
                        qualidadeEB04[elem][produto][horas_D14[i]] = (
                            varEstoqueEB04[produto][horas_D14[i-1]].varValue*qualidadeEB04[elem][produto][horas_D14[i-1]] +
                            varTaxaEnvioEB06EB04[produto][horas_D14[i]].varValue*qualidadeEB06[elem][produto][horas_D14[i-1]]
                            )/massa_blendagemEB04
                        # print(f"    {varEstoqueEB04[produto][horas_D14[i-1]].varValue*qualidadeEB04[elem][produto][horas_D14[i-1]]}")
                        # print(f"  + {varTaxaEnvioEB06EB04[produto][horas_D14[i]].varValue*qualidadeEB06[elem][produto][horas_D14[i-1]]}")
                        # print(f"  / {massa_blendagemEB04}")
                        # print(f"  = {qualidadeEB04[elem][produto][horas_D14[i]]}")

                        # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                        if parametros['lim_min'][elem][produto] >  round(qualidadeEB04[elem][produto][horas_D14[i]],4):
                            verif_qualidade_EB04[elem][produto][horas_D14[i]] = -1
                        elif parametros['lim_max'][elem][produto] < round(qualidadeEB04[elem][produto][horas_D14[i]],4):
                            verif_qualidade_EB04[elem][produto][horas_D14[i]] = 1
                        if verif_qualidade_EB04[elem][produto][horas_D14[i]] != 0:
                            logger.debug(f"Qualidade EB04_Estoque fora da especificação: {elem} {produto} {horas_D14[i]} {qualidadeEB04[elem][produto][horas_D14[i]]}")
                    # else:
                    #     print(f" EB06 Estoque anterior + o que chegou = 0 - qualidade {qualidadeEB06[elem][produto][horas_D14[i]]}")

                    # if (qualidadeEB06[elem][produto][horas_D14[i]] != parametros['alvo'][elem][produto]):
                    #     print("BLENDING")

        qualidade_mineroduto_EB06 = {elem: {produto: {hora: 0 for hora in horas_Dm3_D14} for produto in produtos_conc} for elem in elem_qualidade}
        for elem in elem_qualidade:
            for produto in produtos_conc:
                for hora in horas_Dm3:
                    qualidade_mineroduto_EB06[elem][produto][hora] = parametros['bombEB06_dm3']['qualidade'][elem][produto][hora]

        for elem in elem_qualidade:
            for produto in produtos_conc:
                for hora in horas_D14:
                    qualidade_mineroduto_EB06[elem][produto][hora] = qualidadeEB06[elem][produto][hora]

        nro_violacoes_EB06 = {elem: sum([sum([1 for hora in horas_D14 if verif_qualidade_EB06[elem][produto][hora] != 0]) for produto in produtos_conc]) for elem in elem_qualidade}
        nro_violacoes_EB04 = {elem: sum([sum([1 for hora in horas_D14 if verif_qualidade_EB04[elem][produto][hora] != 0]) for produto in produtos_conc]) for elem in elem_qualidade}

        if sum(nro_violacoes_EB06.values()) == 0 and sum(nro_violacoes_EB04.values()) == 0:
            logger.info('[OK]')
        else:
            for elem, nro_violacoes in nro_violacoes_EB06.items():
                if nro_violacoes != 0:
                    logger.warning(f"Qualidade: '{elem}' fora da especificação: {nro_violacoes} ocorrências em EB06_Estoque")
            for elem, nro_violacoes in nro_violacoes_EB04.items():
                if nro_violacoes != 0:
                    logger.warning(f"Qualidade: '{elem}' fora da especificação: {nro_violacoes} ocorrências em EB04_Estoque")

        #===================== Calcula a qualidade do estoque EB07 (Matipó) =======================#

        logger.info('Verificando qualidade do Estoque EB07')

        qualidadeEB07 = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_conc} for elem in elem_qualidade}

        verif_qualidade_EB07 = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_conc} for elem in elem_qualidade}

        for elem in elem_qualidade:
            for produto in produtos_conc:
                vazaoEB06 = parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]]
                massa_blendagemEB07 = (parametros['estoque_inicial']['EB7'][produto] +
                                   vazaoEB06 * varBombeamentoPolpaEB06[produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]].varValue)
                # print(f"EB07 {elem} {produto} {horas_D14[0]} = ")
                if round(massa_blendagemEB07,1) > 0:
                    qualidadeEB07[elem][produto][horas_D14[0]] = (
                        parametros['estoque_inicial']['EB7'][produto]*parametros['qualidade_inicial']['EB7'][elem][produto] +
                        vazaoEB06 * varBombeamentoPolpaEB06[produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]].varValue *
                           qualidade_mineroduto_EB06[elem][produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]]
                        )/massa_blendagemEB07
                    # print(f"    {parametros['estoque_inicial']['EB7'][produto]*parametros['qualidade_inicial']['EB7'][elem][produto]}")
                    # print(f"  + {vazaoEB06 * varBombeamentoPolpa[produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]].varValue * qualidade_mineroduto_EB06[elem][produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]]}")
                    # print(f"  / {massa_blendagemEB07}")
                    # print(f"  = {qualidadeEB07[elem][produto][horas_D14[0]]}")

                    # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                    if parametros['lim_min'][elem][produto] >  round(qualidadeEB07[elem][produto][horas_D14[0]],4):
                        verif_qualidade_EB07[elem][produto][horas_D14[0]] = -1
                    elif parametros['lim_max'][elem][produto] < round(qualidadeEB07[elem][produto][horas_D14[0]],4):
                        verif_qualidade_EB07[elem][produto][horas_D14[0]] = 1
                    if verif_qualidade_EB07[elem][produto][horas_D14[0]] != 0:
                        logger.debug(f"Qualidade EB07_Estoque fora da especificação: {elem} {produto} {horas_D14[0]} {qualidadeEB07[elem][produto][horas_D14[0]]}")
                # else:
                #     print(f"EB07 Estoque anterior + o que chegou = 0 - qualidade {qualidadeEB07[elem][produto][horas_D14[0]]}")

                # if (qualidadeEB07[elem][produto][horas_D14[0]] != qualidade_mineroduto[elem][produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]]):
                #     print("BLENDING")

        for elem in elem_qualidade:
            for produto in produtos_conc:
                for i in range(len(horas_Dm3)+1, len(horas_Dm3_D14)):
                    hora_saiu = i-parametros['config']['tempo_mineroduto_Germano_Matipo']
                    if (hora_saiu < len(horas_Dm3)):
                        vazaoEB06 = parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[hora_saiu]]
                    else:
                        vazaoEB06 = parametros['gerais']['Vazao_EB6'][extrair_dia(horas_Dm3_D14[hora_saiu])]

                    massa_blendagemEB07 = (varEstoque_eb07[produto][horas_Dm3_D14[i-1]].varValue +
                                    vazaoEB06 * varBombeamentoPolpaEB06[produto][horas_Dm3_D14[hora_saiu]].varValue)
                    # print(f"EB07 {elem} {produto} {horas_Dm3_D14[i]} = ")
                    if round(massa_blendagemEB07,1) > 0:
                        qualidadeEB07[elem][produto][horas_Dm3_D14[i]] = (
                            varEstoque_eb07[produto][horas_Dm3_D14[i-1]].varValue*qualidadeEB07[elem][produto][horas_Dm3_D14[i-1]] +
                            vazaoEB06 * varBombeamentoPolpaEB06[produto][horas_Dm3_D14[hora_saiu]].varValue *
                                qualidade_mineroduto_EB06[elem][produto][horas_Dm3_D14[hora_saiu]]
                            )/massa_blendagemEB07
                        # print(f"    {varEstoque_eb07[produto][horas_Dm3_D14[i-1]].varValue*qualidadeEB07[elem][produto][horas_Dm3_D14[i-1]]}")
                        # print(f"  + {vazaoEB06 * varBombeamentoPolpa[produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']+i]].varValue * qualidade_mineroduto_EB06[elem][produto][horas_Dm3_D14[len(horas_Dm3)+i-parametros['config']['tempo_mineroduto_Germano_Matipo']]]}")
                        # print(f"  / {massa_blendagemEB07}")
                        # print(f"  = {qualidadeEB07[elem][produto][horas_Dm3_D14[i]]}")

                        # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                        if parametros['lim_min'][elem][produto] >  round(qualidadeEB07[elem][produto][horas_Dm3_D14[i]],4):
                            verif_qualidade_EB07[elem][produto][horas_Dm3_D14[i]] = -1
                        elif parametros['lim_max'][elem][produto] < round(qualidadeEB07[elem][produto][horas_Dm3_D14[i]],4):
                            verif_qualidade_EB07[elem][produto][horas_Dm3_D14[i]] = 1
                        if verif_qualidade_EB07[elem][produto][horas_Dm3_D14[i]] != 0:
                            logger.debug(f"Qualidade EB07_Estoque fora da especificação: {elem} {produto} {horas_Dm3_D14[i]} {qualidadeEB07[elem][produto][horas_Dm3_D14[i]]}")
                    # else:
                    #     print(f" EB07 Estoque anterior + o que chegou = 0 - qualidade {qualidadeEB07[elem][produto][horas_D14[i]]}")

                    # if (qualidadeEB07[elem][produto][horas_D14[i]] != qualidade_mineroduto[elem][produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']+i]]):
                    #     print("BLENDING")

        qualidade_mineroduto_EB07 = {elem: {produto: {hora: 0 for hora in horas_Dm3_D14} for produto in produtos_conc} for elem in elem_qualidade}
        for elem in elem_qualidade:
            for produto in produtos_conc:
                for hora in horas_Dm3:
                    qualidade_mineroduto_EB07[elem][produto][hora] = parametros['bombEB07_dm3']['qualidade'][elem][produto][hora]

        for elem in elem_qualidade:
            for produto in produtos_conc:
                for hora in horas_D14:
                    qualidade_mineroduto_EB07[elem][produto][hora] = qualidadeEB07[elem][produto][hora]

        nro_violacoes_EB07 = {elem: sum([sum([1 for hora in horas_D14 if verif_qualidade_EB07[elem][produto][hora] != 0]) for produto in produtos_conc]) for elem in elem_qualidade}

        if sum(nro_violacoes_EB07.values()) == 0:
            logger.info('[OK]')
        else:
            for elem, nro_violacoes in nro_violacoes_EB07.items():
                if nro_violacoes:
                    logger.warning(f"Qualidade: '{elem}' fora da especificação: {nro_violacoes} ocorrências em EB07_Estoque")

        #===================== Calcula a qualidade do estoque de polpa de UBU =======================#

        logger.info('Verificando qualidade dos Estoques de Polpa de Ubu')

        qualidadeTanqueUbu = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_conc} for elem in elem_qualidade}

        verif_qualidade_TanqueUbu = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_conc} for elem in elem_qualidade}

        tempo_matipo_ubu = parametros['config']['tempo_mineroduto_Germano_Ubu']-parametros['config']['tempo_mineroduto_Germano_Matipo']

        for elem in elem_qualidade:
            for produto in produtos_conc:
                massa_blendagem_tanqueUbu = (
                    parametros['estoque_inicial']['TQ_UBU'][produto] +
                    varPolpaUbu[produto][horas_D14[0]].varValue *
                        parametros['config']['perc_solidos'] *
                        parametros['config']['densidade'] +
                    varRetornoPraca[produto][horas_D14[0]].varValue)
                # print(f"TanqueUbu {elem} {produto} {horas_D14[0]} = ")
                if round(massa_blendagem_tanqueUbu,1) > 0:
                    qualidadeTanqueUbu[elem][produto][horas_D14[0]] = (
                        parametros['estoque_inicial']['TQ_UBU'][produto]*parametros['qualidade_inicial']['TQ_UBU'][elem][produto] +
                        varPolpaUbu[produto][horas_D14[0]].varValue *
                            parametros['config']['perc_solidos'] *
                            parametros['config']['densidade'] *
                            qualidade_mineroduto_EB07[elem][produto][horas_Dm3_D14[len(horas_Dm3)-tempo_matipo_ubu]]  +
                        varRetornoPraca[produto][horas_D14[0]].varValue * parametros['qualidade_inicial']['praca_Usina'][elem][produto]
                        )/massa_blendagem_tanqueUbu
                    # print(f"    {parametros['estoque_inicial']['TQ_UBU'][produto]*parametros['qualidade_inicial']['TQ_UBU'][elem][produto]}")
                    # print(f"  + {varPolpaUbu[produto][horas_D14[0]].varValue *  parametros['config']['perc_solidos'] * parametros['config']['densidade'] * qualidade_mineroduto_EB07[elem][produto][horas_Dm3_D14[len(horas_Dm3)-tempo_matipo_ubu]]}")
                    # print(f"  + {varRetornoPraca[produto][horas_D14[0]].varValue * parametros['qualidade_inicial']['praca_Usina'][elem][produto]}")
                    # print(f"  / {massa_blendagem_tanqueUbu}")
                    # print(f"  = {qualidadeTanqueUbu[elem][produto][horas_D14[0]]}")

                    # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                    if parametros['lim_min'][elem][produto] >  round(qualidadeTanqueUbu[elem][produto][horas_D14[0]],4):
                        verif_qualidade_TanqueUbu[elem][produto][horas_D14[0]] = -1
                    elif parametros['lim_max'][elem][produto] < round(qualidadeTanqueUbu[elem][produto][horas_D14[0]],4):
                        verif_qualidade_TanqueUbu[elem][produto][horas_D14[0]] = 1
                    if verif_qualidade_TanqueUbu[elem][produto][horas_D14[0]] != 0:
                        logger.debug(f"Qualidade Ubu_Estoque_Polpa fora da especificação: {elem} {produto} {horas_D14[0]} {qualidadeTanqueUbu[elem][produto][horas_D14[0]]}")
                # else:
                #     print(f"TanqueUbu Estoque anterior + o que chegou = 0 - qualidade {qualidadeTanqueUbu[elem][produto][horas_D14[0]]}")

                # if (qualidadeTanqueUbu[elem][produto][horas_D14[0]] != qualidade_mineroduto[elem][produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]]):
                #     print("BLENDING")

        for elem in elem_qualidade:
            for produto in produtos_conc:
                for i in range(1, len(horas_D14)):
                    hora_saiu = horas_Dm3_D14[len(horas_Dm3)+i-tempo_matipo_ubu]

                    massa_blendagem_tanqueUbu = (
                        varEstoquePolpaUbu[produto][horas_D14[i-1]].varValue +
                        varPolpaUbu[produto][horas_D14[i]].varValue *
                            parametros['config']['perc_solidos'] *
                            parametros['config']['densidade'] +
                        varRetornoPraca[produto][horas_D14[i]].varValue)
                    # print(f"TanqueUbu {elem} {produto} {horas_D14[i]} = ")
                    if round(massa_blendagem_tanqueUbu,1) > 0:
                        qualidadeTanqueUbu[elem][produto][horas_D14[i]] = (
                            varEstoquePolpaUbu[produto][horas_D14[i-1]].varValue*qualidadeTanqueUbu[elem][produto][horas_D14[i-1]] +
                            varPolpaUbu[produto][horas_D14[i]].varValue *
                                parametros['config']['perc_solidos'] *
                                parametros['config']['densidade'] *
                                qualidade_mineroduto_EB07[elem][produto][hora_saiu] +
                            varRetornoPraca[produto][horas_D14[i]].varValue*parametros['qualidade_inicial']['praca_Usina'][elem][produto]
                            )/massa_blendagem_tanqueUbu
                        # print(f"    {varEstoquePolpaUbu[produto][horas_D14[i-1]].varValue}")
                        # print(f"  + {varPolpaUbu[produto][horas_D14[i]].varValue }")
                        # print(f"    {varRetornoPraca[produto][horas_D14[i]].varValue}")
                        # print(f"  = {massa_blendagem_tanqueUbu}")

                        # print(f"    {varEstoquePolpaUbu[produto][horas_D14[i-1]].varValue*qualidadeTanqueUbu[elem][produto][horas_D14[i-1]]}")
                        # print(f"  + {varPolpaUbu[produto][horas_D14[i]].varValue * parametros['config']['perc_solidos'] * parametros['config']['densidade'] * qualidade_mineroduto_EB07[elem][produto][hora_saiu]}")
                        # print(f"    {varRetornoPraca[produto][horas_D14[i]].varValue*parametros['qualidade_inicial']['praca_Usina'][elem][produto]}")
                        # print(f"  / {massa_blendagem_tanqueUbu}")
                        # print(f"  = {qualidadeTanqueUbu[elem][produto][horas_D14[i]]}")

                        # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                        if parametros['lim_min'][elem][produto] >  round(qualidadeTanqueUbu[elem][produto][horas_D14[i]],4):
                            verif_qualidade_TanqueUbu[elem][produto][horas_D14[i]] = -1
                        elif parametros['lim_max'][elem][produto] < round(qualidadeTanqueUbu[elem][produto][horas_D14[i]],4):
                            verif_qualidade_TanqueUbu[elem][produto][horas_D14[i]] = 1
                        if verif_qualidade_TanqueUbu[elem][produto][horas_D14[i]] != 0:
                            logger.debug(f"Qualidade Ubu_Estoque_Polpa fora da especificação: {elem} {produto} {horas_D14[i]} {qualidadeTanqueUbu[elem][produto][horas_D14[i]]}")
                    # else:
                    #     print(f" TanqueUbu Estoque anterior + o que chegou = 0 - qualidade {qualidadeTanqueUbu[elem][produto][horas_D14[i]]}")

        nro_violacoes_TanqueUbu = {elem: sum([sum([1 for hora in horas_D14 if verif_qualidade_TanqueUbu[elem][produto][hora] != 0]) for produto in produtos_conc]) for elem in elem_qualidade}

        if sum(nro_violacoes_TanqueUbu.values()) == 0:
            logger.info('[OK]')
        else:
            for elem, nro_violacoes in nro_violacoes_TanqueUbu.items():
                if nro_violacoes:
                    logger.warning(f"Qualidade: '{elem}' fora da especificação: {nro_violacoes} ocorrências em Ubu_Estoque_Polpa")


        #===================== Calcula a qualidade do estoque de produto do pátio (Ubu) =======================#

        logger.info('Verificando qualidade dos Estoques de Produto do Pátio Ubu')

        qualidadeProdutoPatio = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_usina} for elem in elem_qualidade}

        verif_qualidade_ProdutoPatio = {elem: {produto: {hora: 0 for hora in horas_D14} for produto in produtos_usina} for elem in elem_qualidade}

        for elem in elem_qualidade:
            for produto in produtos_usina:
                massa_blendagemProdutoPatio = (
                     parametros['estoque_inicial']['Patio_Porto'][produto] +
                     sum(varProducaoUbu[produto_c][produto][horas_D14[0]].varValue for produto_c in produtos_conc) /
                      (1+parametros['gerais']['Fator_Conv'][extrair_dia(hora)]))
                # print(f"EstoqueProdutoPatio {elem} {produto} {horas_D14[0]} = ")
                if round(massa_blendagemProdutoPatio,1) > 0:
                    qualidadeProdutoPatio[elem][produto][horas_D14[0]] = (
                        parametros['estoque_inicial']['Patio_Porto'][produto] * parametros['qualidade_inicial']['Patio_Porto'][elem][produto] +
                        sum(varProducaoUbu[produto_c][produto][horas_D14[0]].varValue * qualidadeTanqueUbu[elem][produto_c][horas_D14[0]] for produto_c in produtos_conc) /
                         (1+parametros['gerais']['Fator_Conv'][extrair_dia(horas_D14[0])])
                        )/massa_blendagemProdutoPatio
                    # print(f"    {parametros['estoque_inicial']['Patio_Porto'][produto] * parametros['qualidade_inicial']['Patio_Porto'][elem][produto]}")
                    # print(f"  + {sum(varProducaoUbu[produto_c][produto][horas_D14[0]].varValue * qualidadeTanqueUbu[elem][produto_c][horas_D14[0]] for produto_c in produtos_conc) / (1+parametros['gerais']['Fator_Conv'][extrair_dia(horas_D14[0])]/100)}")
                    # print(f"  / {massa_blendagemProdutoPatio}")
                    # print(f"  = {qualidadeProdutoPatio[elem][produto][horas_D14[0]]}")

                    # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                    if parametros['lim_min'][elem][produto] >  round(qualidadeProdutoPatio[elem][produto][horas_D14[0]],4):
                        verif_qualidade_ProdutoPatio[elem][produto][horas_D14[0]] = -1
                    elif parametros['lim_max'][elem][produto] < round(qualidadeProdutoPatio[elem][produto][horas_D14[0]],4):
                        verif_qualidade_ProdutoPatio[elem][produto][horas_D14[0]] = 1
                    if verif_qualidade_ProdutoPatio[elem][produto][horas_D14[0]] != 0:
                        logger.debug(f"Qualidade Porto_Estoque_Patio fora da especificação: {elem} {produto} {horas_D14[0]} {qualidadeProdutoPatio[elem][produto][horas_D14[0]]}")
                # else:
                #     print(f"EstoqueProdutoPatio Estoque anterior + o que chegou = 0 - qualidade {qualidadeProdutoPatio[elem][produto][horas_D14[0]]}")

        for elem in elem_qualidade:
            for produto in produtos_usina:
                for i in range(1, len(horas_D14)):
                    massa_blendagemProdutoPatio = (
                        varEstoqueProdutoPatio[produto][horas_D14[i-1]].varValue +
                        sum(varProducaoUbu[produto_c][produto][horas_D14[i]].varValue for produto_c in produtos_conc) /
                         (1+parametros['gerais']['Fator_Conv'][extrair_dia(hora)]) )
                    # print(f"EstoqueProdutoPatio {elem} {produto} {horas_D14[i]} = ")
                    if round(massa_blendagemProdutoPatio,1) > 0:
                        qualidadeProdutoPatio[elem][produto][horas_D14[i]] = (
                            varEstoqueProdutoPatio[produto][horas_D14[i-1]].varValue * qualidadeProdutoPatio[elem][produto][horas_D14[i-1]] +
                            sum(varProducaoUbu[produto_c][produto][horas_D14[i]].varValue * qualidadeTanqueUbu[elem][produto_c][horas_D14[i]] for produto_c in produtos_conc) /
                             (1+parametros['gerais']['Fator_Conv'][extrair_dia(horas_D14[i])])
                            )/massa_blendagemProdutoPatio
                        # print(f"M   {varEstoqueProdutoPatio[produto][horas_D14[i-1]].varValue}")
                        # print(f"  + {sum(varProducaoUbu[produto_c][produto][horas_D14[i]].varValue for produto_c in produtos_conc) / (1+parametros['gerais']['Fator_Conv'][extrair_dia(horas_D14[i])]/100)}")
                        # print(f"  = {massa_blendagemProdutoPatio}")

                        # print(f"Q   {varEstoqueProdutoPatio[produto][horas_D14[i-1]].varValue * qualidadeProdutoPatio[elem][produto][horas_D14[i-1]]}")
                        # print(f"  + {sum(varProducaoUbu[produto_c][produto][horas_D14[i]].varValue * qualidadeTanqueUbu[elem][produto_c][horas_D14[i]] for produto_c in produtos_conc) / (1+parametros['gerais']['Fator_Conv'][extrair_dia(horas_D14[i])]/100)}")
                        # print(f"  / {massa_blendagemProdutoPatio}")
                        # print(f"  = {qualidadeProdutoPatio[elem][produto][horas_D14[i]]}")

                        # Se chegou massa no estoque, a qualidade deve estar dentro da especificação
                        if parametros['lim_min'][elem][produto] >  round(qualidadeProdutoPatio[elem][produto][horas_D14[i]],4):
                            verif_qualidade_ProdutoPatio[elem][produto][horas_D14[i]] = -1
                        elif parametros['lim_max'][elem][produto] < round(qualidadeProdutoPatio[elem][produto][horas_D14[i]],4):
                            verif_qualidade_ProdutoPatio[elem][produto][horas_D14[i]] = 1
                        if verif_qualidade_ProdutoPatio[elem][produto][horas_D14[i]] != 0:
                            logger.debug(f"Qualidade Porto_Estoque_Patio fora da especificação: {elem} {produto} {horas_D14[i]} {qualidadeProdutoPatio[elem][produto][horas_D14[i]]}")
                    # else:
                    #     print(f" EstoqueProdutoPatio Estoque anterior + o que chegou = 0 - qualidade {qualidadeProdutoPatio[elem][produto][horas_D14[i]]}")

        nro_violacoes_ProdutoPatio = {elem: sum([sum([1 for hora in horas_D14 if verif_qualidade_ProdutoPatio[elem][produto][hora] != 0]) for produto in produtos_usina]) for elem in elem_qualidade}

        if sum(nro_violacoes_ProdutoPatio.values()) == 0:
            logger.info('[OK]')
        else:
            for elem, nro_violacoes in nro_violacoes_ProdutoPatio.items():
                if nro_violacoes:
                    logger.warning(f"Qualidade: '{elem}' fora da especificação: {nro_violacoes} ocorrências em Porto_Estoque_Patio")

    # Nome do arquivo CSV de saída
    nome_arquivo_variaveis = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_valores_variaveis', 'csv', not args.nao_sobrescrever_arquivos)

    if LpStatus[modelo.status] == 'Optimal':

        logger.info(f'Exportando os resultados das Variáveis, no arquivo {nome_arquivo_variaveis}')

        # Criando um dicionário contendo os valores por hora de cada variável (em vez de contar como variáveis separadas)
        variaveis = set({v.name[:-8] for v in modelo.variables() if v.name[-7:] in horas_D14})
        valores_variaveis = {v: {hora: 0 for hora in horas_D14} for v in variaveis}
        for v in modelo.variables():
            nome = v.name[:-8]
            if nome in variaveis:
                hora = v.name[-7:]
                valores_variaveis[nome][hora] = v.varValue

        exportar_variaveis_csv(nome_arquivo_variaveis, valores_variaveis, horas_D14)
        logger.info('[OK]')

    # Nome do arquivo CSV de saída com os dados de qualidade
    nome_arquivo_qualidade = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_valores_qualidade', 'csv', not args.nao_sobrescrever_arquivos)

    if not args.verificar_qualidade:
        nome_arquivo_qualidade = None
    elif LpStatus[modelo.status] == 'Optimal':
        logger.info(f'Exportando os resultados de Qualidade, no arquivo {nome_arquivo_qualidade}')

        valores_qualidade = {}
        for produto in produtos_conc:
            for elem in elem_qualidade:
                valores_qualidade[f'EB04_Estoque_{produto}_{elem}'] = {hora: qualidadeEB04[elem][produto][hora] for hora in horas_D14}
                valores_qualidade[f'EB06_Estoque_{produto}_{elem}'] = {hora: qualidadeEB06[elem][produto][hora] for hora in horas_D14}
                valores_qualidade[f'EB07_Estoque_{produto}_{elem}'] = {hora: qualidadeEB07[elem][produto][hora] for hora in horas_D14}
                valores_qualidade[f'Ubu_Estoque_Polpa_{produto}_{elem}'] = {hora: qualidadeTanqueUbu[elem][produto][hora] for hora in horas_D14}

                valores_qualidade[f'Verif_EB04_Estoque_{produto}_{elem}'] = {hora: verif_qualidade_EB04[elem][produto][hora] for hora in horas_D14}
                valores_qualidade[f'Verif_EB06_Estoque_{produto}_{elem}'] = {hora: verif_qualidade_EB06[elem][produto][hora] for hora in horas_D14}
                valores_qualidade[f'Verif_EB07_Estoque_{produto}_{elem}'] = {hora: verif_qualidade_EB07[elem][produto][hora] for hora in horas_D14}
                valores_qualidade[f'Verif_Ubu_Estoque_Polpa_{produto}_{elem}'] = {hora: verif_qualidade_TanqueUbu[elem][produto][hora] for hora in horas_D14}


        for produto in produtos_usina:
            for elem in elem_qualidade:
                valores_qualidade[f'Porto_Estoque_Patio_{produto}_{elem}'] = {hora: qualidadeProdutoPatio[elem][produto][hora] for hora in horas_D14}
                valores_qualidade[f'Verif_Porto_Estoque_Patio_{produto}_{elem}'] = {hora: verif_qualidade_ProdutoPatio[elem][produto][hora] for hora in horas_D14}

        exportar_variaveis_csv(nome_arquivo_qualidade, valores_qualidade, horas_D14)
        logger.info('[OK]')

    # Nome do arquivo JSON de saída
    nome_arquivo_resultados = gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_resultados', 'json', not args.nao_sobrescrever_arquivos)
    logger.info(f'Exportando os resultados para JSON, no arquivo {nome_arquivo_resultados}')

    # Criando um dicionário com os resultados para salvar os resultados
    resultados = {'cenario':{'nome': args.nome, 'planilha': args.cenario}}

    if LpStatus[modelo.status] == 'Optimal':
        resultados['variaveis'] = valores_variaveis

        # Inclui também o volume atrasado dos navios, que não tem no CSV (porque não é indexado por hora)
        resultados['variaveis']['Porto_Volume_Atrasado_Navios'] = {navio: varVolumeAtrasadoNavio[navio].varValue for navio in navios_ate_d14}
        resultados['variaveis']['Concentrador_Inicio_Manutencao'] = {i: varInicioManutencoesConcentrador[i][hora].varValue for hora in horas_Dm3_D14 for i in range(len(parametros['manutencao']['Concentrador3']))}

        if args.verificar_qualidade:
            resultados['qualidade'] = valores_qualidade

    tempo_final_solver = time.time()
    tempo_total_solver = tempo_final_solver - tempo_inicio_solver

    logger.info(f'Tempo total de execução do SOLVER: {tempo_total_solver} segundos')

    # Salvando informações do solver
    resultados['otimizador'] = {
        'solver': solver.name,
        'fo': args.funcao_objetivo,
        'valor_fo': valor_fo_modelo_completo,
        'status': status_solucao_modelo_completo,
        'gap': gap_modelo_completo,
        'tempo': tempo_total_solver,
        'versao_otimizador': VERSAO_OTIMIZADOR,
        'data_versao': DATA_VERSAO
    }

    if args.heuristica_relax_and_fix or args.heuristica_otim_partes:
        # Salvando informações da heurística
        resultados['heuristica'] = {
            'valor_fo_modelo_relaxado': valor_fo_modelo_relaxado,
            'status_modelo_relaxado': status_solucao_modelo_relaxado,
            'gap_modelo_relaxado': gap_modelo_relaxado,
            'tempo_modelo_relaxado': tempo_modelo_relaxado,
            'valor_fo_modelo_fixado': valor_fo_modelo_fixado,
            'status_modelo_fixado': status_solucao_modelo_fixado,
            'gap_modelo_fixado': gap_modelo_fixado,
            'tempo_modelo_fixado': tempo_modelo_fixado,
            'tempo_modelo_completo': tempo_modelo_completo,
        }

    resultados['arquivos_saida'] = {
        'parametros': nome_arquivo_parametros,
        'log_solver': nome_arquivo_log_solver,
        'ILP': nome_arquivo_ILP,
        'variaveis': nome_arquivo_variaveis,
        'qualidade': nome_arquivo_qualidade,
        'resultados': nome_arquivo_resultados,
    }

    # Salvando informações das restrições e variáveis que inviabilizaram o modelo (se houver)
    if restricoes_limitantes or variaveis_limitantes:
        resultados['analise_viabilidade'] = {
            'restricoes_limitantes': list(restricoes_limitantes),
            'variaveis_limitantes': list(variaveis_limitantes),
            'nome_arquivo_ILP': nome_arquivo_ILP
        }

    with open(nome_arquivo_resultados, 'w') as f:
        json.dump(resultados, f, indent=4)

    logger.info('[OK]')

    if args.arquivo_sumario:
        logger.info(f'Acrescentando dados no arquivo de sumário {args.arquivo_sumario}')

        # Cria o arquivo CSV se ele ainda não existir
        if not os.path.isfile(args.arquivo_sumario):
            with open(args.arquivo_sumario, 'w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                header = ['cenario', 'maquina', 'instancia', 'fo', 'GAP_lim', 'tempo_lim', 'status',
                          'FO_relax', 'GAP_relax', 'tempo_relax', 'FO_H', 'GAP_H', 'tempo_H',
                          'FO', 'GAP', 'tempo_sol', 'tempo_total_solver', 'tempo total (min)', 'arq_resultado']
                csvwriter.writerow(header)

        import socket # usado apenas para pegar o nome do máquina
        maquina = socket.gethostname()

        # Abre o arquivo CSV para acrescentar uma linha
        with open(args.arquivo_sumario, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)

            row = [args.nome, maquina, nome_instancia, args.funcao_objetivo, args.mipgap, args.limite_tempo,
                   status_solucao_modelo_completo,
                   valor_fo_modelo_relaxado, gap_modelo_relaxado, tempo_modelo_relaxado,
                   valor_fo_modelo_fixado, gap_modelo_fixado, tempo_modelo_fixado,
                   valor_fo_modelo_completo, gap_modelo_completo, tempo_modelo_completo,
                   tempo_total_solver, round(tempo_total_solver/60), nome_arquivo_resultados]
            csvwriter.writerow(row)
        logger.info('[OK]')


except Exception as e:
    logger.exception(f'Houve uma falha na execução do script!')
    #logger.exception(f'Mensagem de exceção:\n{e}')
