from pulp import *
import math
import numpy as np

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
    

    # def verifica_status_solucao(modelo, nome_arquivo_log_solver):
    #     status_solucao = LpStatus[modelo.status]
    #     gap = None
    #     valor_fo = None

    #     # Obtendo os dados de log do solver como um dicionário
    #     logs_solver = orloge.get_info_solver(nome_arquivo_log_solver, 'GUROBI')

    #     melhor_limite, melhor_solucao = logs_solver["best_bound"], logs_solver["best_solution"]

    #     if melhor_limite is not None and melhor_solucao is not None :
    #         gap = abs(melhor_limite - melhor_solucao) / (1e-10 + abs(melhor_solucao)) * 100 # Gap in %. We add 1e-10 to avoid division by zero.
    #     else :
    #         gap = 'N/A'

    #     if LpStatus[modelo.status] == 'Optimal':
    #         valor_fo = modelo.objective.value()
    #         if gap == 0:
    #             print(f'Solução ÓTIMA encontrada: {melhor_solucao:.1f} (gap: {gap:.1f}%)')
    #         else:
    #             status_solucao = 'Feasible'
    #             print(f'Solução viável encontrada: {melhor_solucao:.1f} (gap: {gap:.1f}%)')

    #     elif logs_solver['status'] == 'Model is infeasible':
    #         status_solucao = 'Infeasible'
    #         print(f'Não foi possível encontrar solução!')
    #     else:
    #         print(f'Não foi possível encontrar solução!')

    #     return valor_fo, status_solucao, gap

    # def heuristica_relax_and_fix(self, modelo, nome_instancia, parametros, varBombeamentoPolpaEB06, produtos_conc, horas_D14, solver, args, fo):
    #     foRelax = -  lpSum([varBombeamentoPolpaEB06[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
    #     modelo.setObjective(foRelax)
    #     nome_arquivo_log_solver = self.gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_solver_relaxado', 'log', not args.nao_sobrescrever_arquivos)
    #     solver.optionsDict['logPath'] = nome_arquivo_log_solver
    #     # The problem is solved using PuLP's choice of Solver
    #     solver.solve(modelo)
    #     tempo_modelo_relaxado = modelo.solutionTime
    #     valor_fo_modelo_relaxado, status_solucao_modelo_relaxado, gap_modelo_relaxado = self.verifica_status_solucao(modelo, nome_arquivo_log_solver)

    #     ############################  Heuristica ###################################

    #     FixadaT = None
    #     if status_solucao_modelo_relaxado in ['Optimal', 'Feasible']:
    #         resultados_variavel_ac = {}
    #         for produto_conc in produtos_conc:
    #             acumulado = list(itertools.accumulate([varBombeamentoPolpaEB06[produto_conc][hora].varValue for hora in horas_D14]))
    #             resultados_variavel_ac[produto_conc] = {horas_D14[i] : acumulado[i] for i in range(len(horas_D14))}

    #         LIp = parametros['PolpaLi']
    #         LSp = parametros['PolpaLs']
    #         LIa = parametros['AguaLi']
    #         LSa = parametros['AguaLs']

    #         limite_inf = 0.99
    #         AjustePolpa = 0.8 #0.8
    #         Gap_Relax_Fix = 0.05

    #         # if args.param_adicionais:
    #         #     # Lê o arquivo JSON com os parâmetros do solver
    #         #     with open(args.param_adicionais, 'r') as arquivo:
    #         #         arq_param_adicionais = json.load(arquivo)
    #         #         if "heuristica" in arq_param_adicionais:
    #         #             if "limite_inf" in arq_param_adicionais["heuristica"]:
    #         #                 limite_inf = arq_param_adicionais["heuristica"]["limite_inf"]
    #         #             if "polpa_janela" in arq_param_adicionais["heuristica"]:
    #         #                 AjustePolpa = arq_param_adicionais["heuristica"]["polpa_janela"]
    #         #             if "Gap_Relax_Fix" in arq_param_adicionais["heuristica"]:
    #         #                 Gap_Relax_Fix = arq_param_adicionais["heuristica"]["Gap_Relax_Fix"]

    #         Agua = round(max(LSp + min(LSa,2.66*LIa), LSp*2.66)) #30
    #         Polpa = round(AjustePolpa*LIp) #round(LIp*AjustePolpa)

    #         #Mínimo a ser fixado
    #         FatorJanelaMin = 0.1
    #         JanelaMinFixacao = max(round(Polpa*FatorJanelaMin,0),2)
    #         JanelaMinFixacaoOrg = JanelaMinFixacao

    #         Fixada = np.zeros(len(produtos_conc))
    #         FixadaT = 0

    #         limite_inf_org = limite_inf

    #         ORIGINAL_VALUE = Gap_Relax_Fix

    #         # for option, value in gurobi_options:
    #         #     if option == "MIPgap":
    #         #         gurobi_options.remove((option, value))
    #         # gurobi_options.append(("MIPgap", ORIGINAL_VALUE))

    #         cont_horas = 0
    #         DataMin = 0
    #         FixIni = 0
    #         #FixIniOld = 0

    #         while cont_horas < len(horas_D14):

    #             hora = horas_D14[cont_horas]

    #             if cont_horas > DataMin:

    #                 prod = None
    #                 cont_conc = 0
    #                 maior = 0
    #                 for produto in produtos_conc:

    #                     maxValue = max(varBombeamentoPolpaEB06[produto][hora].varValue for hora in horas_D14[cont_horas:cont_horas+Polpa])

    #                     if resultados_variavel_ac[produto][hora] >= Fixada[cont_conc] and varBombeamentoPolpaEB06[produto][hora].varValue >=limite_inf and maxValue > maior:
    #                         prod = produto
    #                         prodN = cont_conc
    #                         maior = maxValue
    #                     cont_conc +=1

    #                 if prod != None:

    #                     # for option, value in gurobi_options:
    #                     #     if option == "MIPgap":
    #                     #         gurobi_options.remove((option, value))
    #                     #     if option == "SolutionLimit ":
    #                     #         gurobi_options.remove((option, value))
    #                     # gurobi_options.append(("MIPgap", ORIGINAL_VALUE))
    #                     # gurobi_options.append(("SolutionLimit", 1000))

    #                     for hora_p in range(cont_horas, min(cont_horas+Polpa, 336)):

    #                         if resultados_variavel_ac[prod][horas_D14[hora_p]] >= Fixada[prodN] and varBombeamentoPolpaEB06[prod][horas_D14[hora_p]].varValue >= limite_inf:

    #                             modelo += (varBombeamentoPolpaEB06[prod][horas_D14[hora_p]] >= 1, f"rest_fixado_{prod}_{horas_D14[hora_p]}")
    #                             DataMin = min(hora_p + Agua,335)
    #                             FixadaT +=1
    #                             Fixada[prodN] +=1

    #                     for produto in produtos_conc:
    #                         for horas in horas_D14[FixIni:DataMin]:
    #                             modelo += (varBombeamentoPolpaEB06[produto][horas] <= 0 + parametros['BIG_M']*parametros[f'w_teste[{produto}][{horas}]'], f"rest_teste3_{produto}_{horas}")
    #                             modelo += (varBombeamentoPolpaEB06[produto][horas] >= 1 - parametros['BIG_M']*(1 -parametros[f'w_teste[{produto}][{horas}]']), f"rest_teste4_{produto}_{horas}")

    #                     for v in modelo.variables():
    #                         if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
    #                             v.setInitialValue(v.lowBound)
    #                         elif v.upBound is not None and v.varValue > v.upBound - 0.001:
    #                             v.setInitialValue(v.upBound)
    #                         else:
    #                             v.setInitialValue(v.varValue)


    #                     # Aproveitar valor da memória
    #                     solver.optionsDict['warmStart'] = True
    #                     solver.solve(modelo)


    #                     valor_fo_RaF, status_solucao_RaF, gap_RaF = self.verifica_status_solucao(nome_arquivo_log_solver)

    #                     Window_Inv = 12
    #                     contInv = 1

    #                     while not  status_solucao_RaF in ['Optimal', 'Feasible']:

    #                         Window_Inv = Window_Inv*contInv

    #                         for produto in produtos_conc:

    #                             valor_hist = FixIni-Window_Inv

    #                             for horas in horas_D14[valor_hist:DataMin]:
    #                                 if f"rest_fixado2_{produto}_{horas}" in modelo.constraints:
    #                                     del modelo.constraints[f"rest_fixado2_{produto}_{horas}"]
    #                                 # if f"rest_fixado_{produto}_{horas}" in modelo.constraints:
    #                                 #     del modelo.constraints[f"rest_fixado_{produto}_{horas}"]
    #                                 if f"rest_teste3_{produto}_{horas}" in modelo.constraints:
    #                                     del modelo.constraints[f"rest_teste3_{produto}_{horas}"]
    #                                 if f"rest_teste4_{produto}_{horas}" in modelo.constraints:
    #                                     del modelo.constraints[f"rest_teste4_{produto}_{horas}"]

    #                         # for option, value in gurobi_options:
    #                         #     if option == "MIPgap":
    #                         #         gurobi_options.remove((option, value))
    #                         #     if option == "SolutionLimit ":
    #                         #         gurobi_options.remove((option, value))
    #                         # gurobi_options.append(("SolutionLimit", 1))
    #                         # gurobi_options.append(("MIPgap", 2*ORIGINAL_VALUE))

    #                         solver.solve(modelo)

    #                         # for option, value in gurobi_options:
    #                         #     if option == "MIPgap":
    #                         #         gurobi_options.remove((option, value))
    #                         #     if option == "SolutionLimit ":
    #                         #         gurobi_options.remove((option, value))
    #                         # gurobi_options.append(("MIPgap", ORIGINAL_VALUE))
    #                         # gurobi_options.append(("SolutionLimit", 1000))

    #                         contInv +=1

    #                         valor_fo_RaF, status_solucao_RaF, gap_RaF = self.verifica_status_solucao(nome_arquivo_log_solver)

    #                         FixIni = valor_hist

    #                     for produto in produtos_conc:
    #                         for horas in horas_D14[FixIni:DataMin]:
    #                             # if varBombeamentoPolpaEB06[produto][horas].varValue == 0:
    #                             #     modelo += (varBombeamentoPolpaEB06[produto][horas] <=0, f"rest_fixado2_{produto}_{horas}")
    #                             if varBombeamentoPolpaEB06[produto][horas].varValue == 1:
    #                                 modelo += (varBombeamentoPolpaEB06[produto][horas] >= 1, f"rest_fixado2_{produto}_{horas}")

    #                     #FixIniOld = FixIni
    #                     FixIni = DataMin
    #                     limite_inf = limite_inf_org
    #                     JanelaMinFixacao = JanelaMinFixacaoOrg

    #                 if prod == None and cont_horas - DataMin > Agua + Polpa :
    #                     cont_horas = DataMin
    #                     limite_inf = limite_inf-0.05
    #                     JanelaMinFixacao = 1


    #             cont_horas += 1

    #         if FixIni < 335:
    #             for produto in produtos_conc:
    #                 for hora in horas_D14[FixIni:335]:
    #                     modelo += (varBombeamentoPolpaEB06[produto][hora] <= 0 + parametros['BIG_M']*parametros[f'w_teste[{produto}][{horas}]'], f"rest_teste3_{produto}_{hora}")
    #                     modelo += (varBombeamentoPolpaEB06[produto][hora] >= 1 - parametros['BIG_M']*(1 - parametros[f'w_teste[{produto}][{horas}]']), f"rest_teste4_{produto}_{hora}")

    #             # Aproveitar valor da memória
    #             solver.optionsDict['warmStart'] = True

    #             # for option, value in gurobi_options:
    #             #     if option == "MIPgap":
    #             #         gurobi_options.remove((option, value))
    #             #     if option == "SolutionLimit ":
    #             #         gurobi_options.remove((option, value))
    #             # gurobi_options.append(("MIPgap",  args.mipgap))
    #             # gurobi_options.append(("SolutionLimit", 1000))
    #             solver.solve(modelo)

    #         for v in modelo.variables():
    #             if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
    #                 v.setInitialValue(v.lowBound)
    #             elif v.upBound is not None and v.varValue > v.upBound - 0.001:
    #                 v.setInitialValue(v.upBound)
    #             else:
    #                 v.setInitialValue(v.varValue)

    #         modelo.setObjective(fo)
    #         # for option, value in gurobi_options:
    #         #     if option == "MIPgap":
    #         #         gurobi_options.remove((option, value))
    #         #     if option == "SolutionLimit ":
    #         #         gurobi_options.remove((option, value))
    #         # gurobi_options.append(("MIPgap", args.mipgap))
    #         # gurobi_options.append(("SolutionLimit", 1000))


    #         for produto in produtos_conc:
    #             for hora in horas_D14:
    #                 if f"rest_fixado_{produto}_{hora}" in modelo.constraints:
    #                     del modelo.constraints[f"rest_fixado_{produto}_{hora}"]
    #                 if f"rest_fixado2_{produto}_{hora}" in modelo.constraints:
    #                     del modelo.constraints[f"rest_fixado2_{produto}_{hora}"]

    #         for v in modelo.variables():
    #             if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
    #                 v.setInitialValue(v.lowBound)
    #             elif v.upBound is not None and v.varValue > v.upBound - 0.001:
    #                 v.setInitialValue(v.upBound)
    #             else:
    #                 v.setInitialValue(v.varValue)


    #         solver.optionsDict['warmStart'] = True
    #         nome_arquivo_log_solver = self.gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_solver_completo', 'log', not args.nao_sobrescrever_arquivos)
    #         solver.optionsDict['logPath'] = nome_arquivo_log_solver
    #         solver.solve(modelo)

    #         tempo_modelo_completo = modelo.solutionTime
    #         valor_fo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo = self.verifica_status_solucao(nome_arquivo_log_solver)

    #     return valor_fo_modelo_relaxado, tempo_modelo_relaxado, gap_modelo_relaxado, valor_fo_modelo_completo, tempo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo, nome_arquivo_log_solver


    # def heuristica_otim_por_partes(self, modelo, nome_instancia, varBombeamentoPolpaEB06, produtos_conc, horas_D14, solver, args, fo, parametros):

    #     foRelax = lpSum([varBombeamentoPolpaEB06[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
    #     modelo.setObjective(foRelax)
    #     nome_arquivo_log_solver = self.gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_solver_relaxado', 'log', not args.nao_sobrescrever_arquivos)
    #     solver.optionsDict['logPath'] = nome_arquivo_log_solver
    #     # The problem is solved using PuLP's choice of Solver
    #     solver.solve(modelo)
    #     tempo_modelo_relaxado = modelo.solutionTime
    #     valor_fo_modelo_relaxado, status_solucao_modelo_relaxado, gap_modelo_relaxado = self.verifica_status_solucao(nome_arquivo_log_solver)

    #     ############################  Heuristica ###################################

    #     if status_solucao_modelo_relaxado in ['Optimal', 'Feasible']:
    #         gap_heuristica = 0.25
    #         FindSolutionsCount = 5
    #         Janelas = 5

    #         if args.param_adicionais:
    #             # Lê o arquivo JSON com os parâmetros do solver
    #             with open(args.param_adicionais, 'r') as arquivo:
    #                 arq_param_adicionais = json.load(arquivo)
    #                 if "heuristica_otim_por_partes" in arq_param_adicionais:
    #                     if "gap_heuristica" in arq_param_adicionais["heuristica_otim_por_partes"]:
    #                         gap_heuristica = arq_param_adicionais["heuristica_otim_por_partes"]["gap_heuristica"]
    #                     if "FindSolutionsCount" in arq_param_adicionais["heuristica_otim_por_partes"]:
    #                         FindSolutionsCount = arq_param_adicionais["heuristica_otim_por_partes"]["FindSolutionsCount"]
    #                     if "Janelas" in arq_param_adicionais["heuristica_otim_por_partes"]:
    #                         Janelas = arq_param_adicionais["heuristica_otim_por_partes"]["Janelas"]

    #         DataMin = 0
    #         cont_horas = 0
    #         ORIGINAL_VALUE = gap_heuristica

    #         # for option, value in gurobi_options:
    #         #     if option == "MIPgap":
    #         #         gurobi_options.remove((option, value))
    #         # gurobi_options.append(("MIPgap", ORIGINAL_VALUE))
    #         # gurobi_options.append(("SolutionLimit", FindSolutionsCount))

    #         total_Horas = len(horas_D14)
    #         Window = round(total_Horas/Janelas)

    #         for hora in horas_D14:

    #             if cont_horas >= DataMin and cont_horas + Window < 335:

    #                 DataMin = min(cont_horas + Window,335)

    #                 for produto in produtos_conc:
    #                     for horas in horas_D14[cont_horas:DataMin]:
    #                         modelo += (varBombeamentoPolpaEB06[produto][horas] <= 0 + parametros['BIG_M']*parametros[f'w_teste[{produto}][{horas}]'], f"rest_teste3_{produto}_{horas}")
    #                         modelo += (varBombeamentoPolpaEB06[produto][horas] >= 1 - parametros['BIG_M']*(1 - parametros[f'w_teste[{produto}][{horas}]']), f"rest_teste4_{produto}_{horas}")

    #                 for v in modelo.variables():
    #                     if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
    #                         v.setInitialValue(v.lowBound)
    #                     elif v.upBound is not None and v.varValue > v.upBound - 0.001:
    #                         v.setInitialValue(v.upBound)
    #                     else:
    #                         v.setInitialValue(v.varValue)

    #                 # Aproveitar valor da memória
    #                 solver.optionsDict['warmStart'] = True
    #                 solver.solve(modelo)

    #                 valor_fo_RaF, status_solucao_RaF, gap_RaF = self.verifica_status_solucao(nome_arquivo_log_solver)

    #                 Window_Inv = 24
    #                 contInv = 1

    #                 while not  status_solucao_RaF in ['Optimal', 'Feasible']:

    #                     Window_Inv = Window_Inv*contInv
    #                     for produto in produtos_conc:
    #                         valor_hist = cont_horas-Window_Inv
    #                         for horas in horas_D14[valor_hist:cont_horas]:
    #                             if f"rest_fixado2_{produto}_{horas}" in modelo.constraints:
    #                                 del modelo.constraints[f"rest_fixado2_{produto}_{horas}"]

    #                     # for option, value in gurobi_options:
    #                     #     if option == "MIPgap":
    #                     #         gurobi_options.remove((option, value))
    #                     #     if option == "SolutionLimit ":
    #                     #         gurobi_options.remove((option, value))
    #                     # gurobi_options.append(("SolutionLimit", 1))
    #                     # gurobi_options.append(("MIPgap", 2*ORIGINAL_VALUE))

    #                     solver.solve(modelo)

    #                     # for option, value in gurobi_options:
    #                     #     if option == "MIPgap":
    #                     #         gurobi_options.remove((option, value))
    #                     #     if option == "SolutionLimit ":
    #                     #         gurobi_options.remove((option, value))
    #                     # gurobi_options.append(("MIPgap", ORIGINAL_VALUE))
    #                     # gurobi_options.append(("SolutionLimit", FindSolutionsCount))


    #                     contInv +=1

    #                     valor_fo_RaF, status_solucao_RaF, gap_RaF = self.verifica_status_solucao(nome_arquivo_log_solver)


    #                 for produto in produtos_conc:
    #                     for horas in horas_D14[0:DataMin]:
    #                         if varBombeamentoPolpaEB06[produto][horas].varValue == 0 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
    #                             modelo += (varBombeamentoPolpaEB06[produto][horas] <=0, f"rest_fixado2_{produto}_{horas}")
    #                         if varBombeamentoPolpaEB06[produto][horas].varValue == 1 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
    #                             modelo += (varBombeamentoPolpaEB06[produto][horas] >= 1, f"rest_fixado2_{produto}_{horas}")


    #             cont_horas += 1

    #         modelo.setObjective(fo)
    #         # for option, value in gurobi_options:
    #         #     if option == "MIPgap":
    #         #         gurobi_options.remove((option, value))
    #         #     if option == "SolutionLimit ":
    #         #         gurobi_options.remove((option, value))
    #         # gurobi_options.append(("MIPgap", args.mipgap))
    #         # gurobi_options.append(("SolutionLimit", 1000))

    #         for produto in produtos_conc:
    #             for hora in horas_D14:
    #                 if f"rest_fixado_{produto}_{hora}" in modelo.constraints:
    #                     del modelo.constraints[f"rest_fixado_{produto}_{hora}"]
    #                 if f"rest_fixado2_{produto}_{hora}" in modelo.constraints:
    #                     del modelo.constraints[f"rest_fixado2_{produto}_{hora}"]

    #         for v in modelo.variables():
    #             if v.lowBound is not None and v.varValue < v.lowBound + 0.001:
    #                 v.setInitialValue(v.lowBound)
    #             elif v.upBound is not None and v.varValue > v.upBound - 0.001:
    #                 v.setInitialValue(v.upBound)
    #             else:
    #                 v.setInitialValue(v.varValue)

    #         # Aproveitar valor da memória
    #         # solver.optionsDict['warmStart'] = True
    #         nome_arquivo_log_solver = self.gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{nome_instancia}_solver_completo', 'log', not args.nao_sobrescrever_arquivos)
    #         solver.optionsDict['logPath'] = nome_arquivo_log_solver
    #         # print("RODANDO NOVAMENTE O MODELO")
    #         solver.solve(modelo)

    #         tempo_modelo_completo = modelo.solutionTime
    #         valor_fo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo = self.verifica_status_solucao(nome_arquivo_log_solver)

    #     return valor_fo_modelo_relaxado, tempo_modelo_relaxado, gap_modelo_relaxado, valor_fo_modelo_completo, tempo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo, nome_arquivo_log_solver

    def modelo(self, cenario, solver, data, varBombeamentoPolpaPPO=None):

        # variaveis utilizadas pelo modelo
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
        lim_min_campanha = data['lim_min_campanha']
        lim_max_campanha = data['lim_max_campanha']
        lim_acum_campanha = data['lim_acum_campanha']
        lim_min_janela = data['lim_min_janela']
        lim_max_janela = data['lim_max_janela']
        lim_acum_janela = data['lim_acum_janela']
        AguaLi = data['AguaLi']
        AguaLs = data['AguaLs']
        PolpaLi = data['PolpaLi']
        PolpaLs = data['PolpaLs']
        navios = data['navios']
        navios_ate_d14 = data['navios_ate_d14']
        taxa_carreg_navios = data['taxa_carreg_navios']
        carga_navios = data['carga_navios']
        estoque_produto_patio = data['estoque_produto_patio']
        capacidade_carreg_porto_por_dia = data['capacidade_carreg_porto_por_dia']
        produtos_navio = data['produtos_navio']
        capacidade_patio_porto_min = data['capacidade_patio_porto_min']
        capacidade_patio_porto_max = data['capacidade_patio_porto_max']
        data_chegada_navio = data['data_chegada_navio']
        perc_solidos = data['perc_solidos']
        densidade = data['densidade']
        DF = data['DF']
        UD = data['UD']
        umidade = data['umidade']
        dif_balanco = data['dif_balanco']

        dias = data['dias']
        args = data['args']

        BIG_M = 10e6
        BIG_M_MINERODUTO = 10e3
        modelo = LpProblem("Plano Semanal", LpMaximize)

        varTaxaBritagem = LpVariable.dicts("Britagem_Taxa_Producao", (produtos_mina, horas_D14), 0, None, LpContinuous)

        # Variável para definir o estoque pulmão pré-concentrador, por produto da mina, por hora
        varEstoquePulmaoConcentrador = LpVariable.dicts("Concentrador_Estoque_Pulmao", (produtos_mina, horas_D14),
                                                        min_estoque_pulmao_concentrador, max_estoque_pulmao_concentrador,
                                                        LpContinuous)

        # Variável que indica o produto que está sendo entregue pelo concentrador, por hora
        varProdutoConcentrador = LpVariable.dicts("Concentrador_ConversaoProduto", (produtos_mina, produtos_conc, horas_D14),  0, 1, LpInteger)

        # Variável que indica o início da campanha de um produto no concentrador, por hora
        # varInicioCampanhaConcentrador = LpVariable.dicts("Concentrador_InicioCampanha", (produtos_conc, horas_D14),  0, 1, LpInteger)

        # Variável que indica o final da campanha de um produto no concentrador, por hora
        varFimCampanhaConcentrador = LpVariable.dicts("Concentrador_FimCampanha", (produtos_conc, horas_D14),  0, 1, LpInteger)

        # Variável para definir da taxa de alimentação, por produto mina, e por produto do concentrador, por hora
        varTaxaAlimProdMinaConc = LpVariable.dicts("Concentrador_Taxa_Alimentacao_ConversaoProdutos", (produtos_mina, produtos_conc, horas_D14),
                                                0, max_taxa_alimentacao,
                                                LpContinuous)

        # Variável para definir da taxa de alimentação, por produto do concentrador, por hora
        varTaxaAlim = LpVariable.dicts("Concentrador_Taxa_Alimentacao", (produtos_conc, horas_D14),
                                        0, max_taxa_alimentacao,
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
                dados[produto].append(int(taxa_producao_britagem[self.extrair_dia(hora)]*produtos_britagem[produto][hora]))
                modelo += (
                    varTaxaBritagem[produto][hora] <= int(taxa_producao_britagem[self.extrair_dia(hora)]*produtos_britagem[produto][hora]),
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
            elif lim_acum_campanha[produto_conc] > 0:
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
                return lim_acum_campanha[produto_conc]

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
                        lim_min_campanha[produto_conc]-
                        (1 - varFimCampanhaConcentrador[produto_conc][hora])*BIG_M,
                        f"rest_limiteMinCampanhaConcentrador_{produto_conc}_{hora}",
                )
                modelo += (
                    varTaxaAlimAcumulada[produto_conc][hora] <=
                        lim_max_campanha[produto_conc],
                        f"rest_limiteMaxCampanhaConcentrador_{produto_conc}_{hora}",
                )

        # Restrições para calcular a janela da taxa de alimentação acumulada no concentrador, por produto, por hora

        def janela_concentrador_anterior(produto_conc, idx_hora):
            if idx_hora > 0:
                return varJanelaAlimAcumulada[produto_conc][horas_D14[idx_hora-1]]
            else:
                return lim_acum_janela[produto_conc]

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
                        lim_min_campanha[produto_conc] -
                        (1 - varFimCampanhaConcentrador[produto_conc][hora])*BIG_M,
                        f"rest_limiteMinJanelaCampanhaConcentrador_{produto_conc}_{hora}",
                )
                modelo += (
                    varJanelaAlimAcumulada[produto_conc][hora] <=
                        lim_max_campanha[produto_conc],
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
                    == estoque_pulmao_inicial_concentrador[produto]
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
                #TODO: olha aqui
                varPuxada[hora] == lpSum([varTaxaAlim[produto][hora] for produto in produtos_conc]) *
                                DF[self.extrair_dia(hora)] *
                                UD[self.extrair_dia(hora)] *
                                (1-umidade[self.extrair_dia(hora)]),
                f"rest_define_Puxada_{hora}",
            )

        # Produção, por produto do concentrador é calculada a partir da taxa de alimentação e demais parâmetros
        varProducao = LpVariable.dicts("Concentrador_Producao", (produtos_conc, horas_D14), 0, None, LpContinuous)
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varProducao[produto][hora]
                        == varTaxaAlim[produto][hora] *
                            (1-umidade[self.extrair_dia(hora)]) *
                            (parametros_calculados['RP (Recuperação Mássica) - C3'][self.extrair_dia(hora)] / 100) *
                            DF[self.extrair_dia(hora)] *
                            (1 - dif_balanco[self.extrair_dia(hora)]),
                    f"rest_define_Producao_{produto}_{hora}",
                )

        # Produção Volume, por hora, é calculada a partir produção volume
        varProducaoVolume = LpVariable.dicts("Concentrador_Volume", (produtos_conc, horas_D14), 0, None, LpContinuous)
        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (
                    varProducaoVolume[produto][hora]
                        == varProducao[produto][hora] * (1/perc_solidos[self.extrair_dia(hora)])
                                                    * (1/densidade[self.extrair_dia(hora)]),
                    f"rest_define_ProducaoVolume_{produto}_{hora}",
                )

        # Geração de Lama, por dia, é calculada a partir da puxada
        varGeracaoLama = LpVariable.dicts("Concentrador_Lama", (horas_D14), 0, None, LpContinuous)
        for hora in horas_D14:
            modelo += (
                varGeracaoLama[hora] == varPuxada[hora]*(1-fatorGeracaoLama),
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

        if varBombeamentoPolpaPPO:
            for produto in produtos_conc:
                for horas in horas_D14[0:24]:
                    if varBombeamentoPolpaPPO[produto][horas] == 0 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
                        modelo += (varBombeamentoPolpa[produto][horas] <=0, f"rest_fixado2_{produto}_{horas}")
                    if varBombeamentoPolpaPPO[produto][horas] == 1 and f"rest_fixado2_{produto}_{horas}" not in modelo.constraints:
                        modelo += (varBombeamentoPolpa[produto][horas] >=1, f"rest_fixado2_{produto}_{horas}")

        elif not (args.relax_and_fix or args.opt_partes):
            varBombeamentoPolpa = LpVariable.dicts("Mineroduto_Bombeamento_Polpa_EB06", (produtos_conc, horas_D14), 0, 1, LpInteger)
        else: # Se for rodar a heurística, a variável é relaxada
            varBombeamentoPolpa = LpVariable.dicts("Mineroduto_Bombeamento_Polpa_EB06", (produtos_conc, horas_D14), 0, 1, LpContinuous)


        # Restrição de capacidade do estoque EB06
        for hora in horas_D14:
            modelo += (
                lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc)
                    <= parametros_mineroduto_ubu['Capacidade EB06'][hora],
                f"rest_capacidade_EstoqueEB06_{hora}",
            )


        # Define o valor de estoque de EB06, por produto, da segunda hora em diante
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
        
        # Carrega os dados de D-3
        # for hora in horas_Dm3:
        #     for produto in produtos_conc:
        #         if produto == parametros['bombEB06_dm3']['Bombeamento Polpa -D3'][hora]:
        #             modelo += (
        #                 varBombeamentoPolpa[produto][hora] == 1,
        #                 f"rest_define_Bombeamento_inicial_{produto}_{hora}",
        #             )
        #         else:
        #             modelo += (
        #                 varBombeamentoPolpa[produto][hora] == 0,
        #                 f"rest_define_Bombeamento_inicial_{produto}_{hora}",
        #             )

        # Carrega os dados de D-3
        # for hora in horas_Dm3:
        #     for produto in produtos_conc:
        #         if produto == parametros['bombEB07_dm3']['Bombeamento Polpa -D3'][hora]:
        #             modelo += (
        #                 varBombeadoEB07[produto][hora] == parametros['bombEB07_dm3']['bombeado'][hora],
        #                 f"rest_define_Bombeado_inicial_{produto}_{hora}",
        #             )
        #         else:
        #             modelo += (
        #                 varBombeadoEB07[produto][hora] == 0,
        #                 f"rest_define_Bombeado_inicial_{produto}_{hora}",
        #             )

        # Restrição para garantir que apenas um produto é bombeado por vez
        for hora in horas_D14:
            modelo += (
                lpSum(varBombeamentoPolpa[produto][hora] for produto in produtos_conc) <= 1,
                f"rest_bombeamento_unico_produto_{hora}",
            )

        # def bombeamento_hora_anterior(produto, idx_hora):
        #     if idx_hora == 0:
        #         return varBombeamentoPolpa[produto][horas_Dm3[-1]]
        #     else:
        #         return varBombeamentoPolpa[produto][horas_D14[idx_hora-1]]

        # Define o bombeamento de polpa para as horas de d01 a d14, respeitando as janelas mínimas de polpa e de água respectivamente
        for produto in produtos_conc:
            for i, hora in enumerate(horas_D14[0:-PolpaLi+1]):
                modelo += (
                    varBombeamentoPolpa[produto][horas_D14[i]] +
                        lpSum([varBombeamentoPolpa[produto][horas_D14[j]] for j in range(i+1, i+PolpaLi)]) >=
                            PolpaLi
                            - PolpaLi*(1 - varBombeamentoPolpa[produto][horas_D14[i]]),
                    f"rest_janela_bombeamento_polpa_{produto}_{hora}",
            )

        # Para a primeira hora é necessário considerar o bombeamento de polpa que já pode ter acontecido no dia anterior ao do planejamento
        # if parametros['calculados']['Bombeamento Acumulado Polpa final semana anterior'] > 0:
        #     tamanho_primeira_janela = parametros['config']['bombeamento_restante_janela_anterior_polpa']
        #     produto_polpa_semana_anterior = parametros['bombEB06_dm3']['Bombeamento Polpa -D3'][horas_Dm3[-1]]
        #     modelo += (
        #         lpSum([varBombeamentoPolpa[produto_polpa_semana_anterior][horas_D14[j]] for j in range(0, tamanho_primeira_janela)]) >= tamanho_primeira_janela,
        #         f"rest_primeira_janela_bombeamento_polpa_{produto_polpa_semana_anterior}_{horas_D14[0]}",
        #     )

        # Para a primeira hora é necessário considerar o bombeamento de água que já pode ter acontecido no dia anterior ao do planejamento

        # for produto in produtos_conc:
        #     if parametros['calculados']['Bombeamento Acumulado Agua final semana anterior'] > 0:
        #         tamanho_primeira_janela = parametros['config']['bombeamento_restante_janela_anterior_agua']
        #         modelo += (
        #             lpSum([varBombeamentoPolpa[produto][horas_D14[j]] for j in range(0, tamanho_primeira_janela)]) == 0,
        #             f"rest_primeira_janela_bombeamento_polpa_{produto}_{horas_D14[0]}",
        #         )

        # if parametros['config']['config_janela_final']:
        #     # Trata os últimos horários (tempo menor que a janela mínima de bombeamento de polpa) para que os bombeamentos de polpa,
        #     # se houverem sejam consecutivos até o final
        #     for produto in produtos_conc:
        #         # subject to Prod{i in 2..H-1}: #maximo de 1s
        #         #     sum{t in i..H-1}X[t] >= H - i - (1 - X[i])*M - X[i-1]*M;
        #         for i in range(len(horas_D14)-parametros['config']['janela_min_bombeamento_polpa']+1, len(horas_D14)):
        #             modelo += (
        #                 lpSum(varBombeamentoPolpa[produto][horas_D14[j]] for j in range(i,len(horas_D14)))
        #                     >= len(horas_D14) - i
        #                        - (1 - varBombeamentoPolpa[produto][horas_D14[i]]) * BIG_M_MINERODUTO
        #                        - (varBombeamentoPolpa[produto][horas_D14[i-1]] * BIG_M_MINERODUTO),
        #                 f"rest_janela_bombeamento_polpa_{produto}_{horas_D14[i]}",
        #             )

        #for produto in produtos_conc:
        for i, hora in enumerate(horas_D14[0:-AguaLi+1]):
            modelo += (
                lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc)+
                lpSum([varBombeamentoPolpa[produto][horas_D14[j]]
                        for produto in produtos_conc for j in range(i+1, i+AguaLi)]) <=
                    BIG_M_MINERODUTO*(1 + lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc)),
                f"rest_janela_bombeamento_agua_{produto}_{hora}",
            )

        # Define a quantidade bombeada de polpa por hora
        # for produto in produtos_conc:
        #     for idx_hora in range(len(horas_Dm3), len(horas_Dm3_D14)):
                # modelo += (
                #     varBombeadoEB07[produto][horas_Dm3_D14[idx_hora]] ==
                #         varBombeamentoPolpaEB06[produto][horas_Dm3_D14[idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo']]] *
                #         parametros['gerais']['Vazao_EB7'][extrair_dia(horas_Dm3_D14[idx_hora])],
                #     f"rest_definie_bombeado_{produto}_{horas_Dm3_D14[idx_hora]}",
                # )

                # if (idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo'] < len(horas_Dm3)):
                #     vazaoEB06 = parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo']]]
                # else:
                #     vazaoEB06 = parametros['gerais']['Vazao_EB6'][extrair_dia(horas_Dm3_D14[idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo']])]
                # modelo += (
                #     varBombeadoEB07[produto][horas_Dm3_D14[idx_hora]] ==
                #         varBombeamentoPolpa[produto][horas_Dm3_D14[idx_hora-parametros['config']['tempo_mineroduto_Germano_Matipo']]] *
                #         vazaoEB06,
                #     f"rest_definie_bombeado_{produto}_{horas_Dm3_D14[idx_hora]}",
                # )

        # # Define a conservação de fluxo em matipo
        # varEstoque_eb07 = LpVariable.dicts("EB07_Estoque", (produtos_conc, horas_D14), 0, None, LpContinuous)

        # # Variável que indica o produto que está armazenado no EB07 (ele armazena um único produto por vez)
        # varProdutoEB07 = LpVariable.dicts("EB07_Produto", (produtos_conc, horas_D14),  0, 1, LpInteger)

        # # Define que o estoque EB07 tem apenas um produto por vez
        # for hora in horas_D14:
        #     modelo += (
        #         lpSum(varProdutoEB07[produto][hora] for produto in produtos_conc) <= 1,
        #         f"rest_define_produto_eb07_{hora}",
        #    )

        # for produto in produtos_conc:
        #     for i in range(len(horas_Dm3)+1, len(horas_Dm3_D14)):
        #         if (i-parametros['config']['tempo_mineroduto_Germano_Matipo'] < len(horas_Dm3)):
        #             vazaoEB06 = parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[i-parametros['config']['tempo_mineroduto_Germano_Matipo']]]
        #         else:
        #             vazaoEB06 = parametros['gerais']['Vazao_EB6'][extrair_dia(horas_Dm3_D14[i-parametros['config']['tempo_mineroduto_Germano_Matipo']])]
        #         modelo += (
        #             varEstoque_eb07[produto][horas_Dm3_D14[i]] == varEstoque_eb07[produto][horas_Dm3_D14[i-1]] +
        #                 varBombeamentoPolpa[produto][horas_Dm3_D14[i-parametros['config']['tempo_mineroduto_Germano_Matipo']]]*
        #                 #(vazaoEB06 - parametros['gerais']['Vazao_EB7'][extrair_dia(horas_Dm3_D14[i])]),
        #                 (vazaoEB06 - vazaoEB06),
        #             f"rest_define_estoque_eb07_{produto}_{i}",
        #         )

            # modelo += (
            #     varEstoque_eb07[produto][horas_D14[0]] == parametros['estoque_inicial']['EB7'][produto] +
            #         varBombeamentoPolpa[produto][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]]*
            #         # (parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]] -
            #         # parametros['gerais']['Vazao_EB7'][extrair_dia(horas_D14[0])]),
            #         (parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]] -
            #          parametros['bombEB06_dm3']['bombeado'][horas_Dm3_D14[len(horas_Dm3)-parametros['config']['tempo_mineroduto_Germano_Matipo']]]),
            #     f"rest_define_estoque_eb07_hora0_{produto}_{hora}",
            # )

        # # Limita as quantidades de produtos no tanque eb07
        # for produto in produtos_conc:
        #     for hora in horas_D14:
        #         modelo += (
        #             varEstoque_eb07[produto][hora] <= varProdutoEB07[produto][hora]*parametros['capacidades']['EB7']['max'],
        #             f"rest_limita_max_estoque_eb07_{produto}_{hora}",
        #         )
        #         modelo += (
        #             varEstoque_eb07[produto][hora] >= varProdutoEB07[produto][hora]*parametros['capacidades']['EB7']['min'],
        #             f"rest_limita_min_estoque_eb07_{produto}_{hora}",
        #         )

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

        # def bombeamento_acumulado_polpa_hora_anterior(idx_hora):
        #     if idx_hora == 0:
        #         # subject to Producao2f{t in 1..H}: #maximo de 1s
        #         #    Xac[1] = 0;
        #         return parametros['calculados']['Bombeamento Acumulado Polpa final semana anterior']
        #     else:
        #         return varBombeamentoPolpaAcumulado[horas_D14[idx_hora-1]]

        # # subject to Producao1a{t in 2..H}: #maximo de 1s
        # #    Xac[t] <= Xac[t-1] + 1 + (1- X[t])*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <=
        #             bombeamento_acumulado_polpa_hora_anterior(idx_hora) + 1 +
        #             (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_1a_{horas_D14[idx_hora]}",
        #     )

        # # subject to Producao1b{t in 2..H}: #maximo de 1s
        # #    Xac[t] >= Xac[t-1] + 1 - (1- X[t])*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] >=
        #             bombeamento_acumulado_polpa_hora_anterior(idx_hora) + 1 -
        #             (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_1b_{horas_D14[idx_hora]}",
        #     )

        # subject to Producao1c{t in 2..H}: #maximo de 1s
        #    Xac[t] <= X[t]*M;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <= lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)*BIG_M_MINERODUTO,
                f"rest_seq_bomb_1c_{horas_D14[idx_hora]}",
            )

        # subject to Producao2a{t in 2..H}: #maximo de 1s
        #    Xf[t] <= Xac[t-1] + (1 - X[t-1] + X[t])*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoPolpaFinal[horas_D14[idx_hora]] <=
        #             bombeamento_acumulado_polpa_hora_anterior(idx_hora) +
        #             (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)
        #             + lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_2a_{horas_D14[idx_hora]}",
        #     )

        # subject to Producao2b{t in 2..H}: #maximo de 1s
        #    Xf[t] >= Xac[t-1] - (1 - X[t-1] + X[t])*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoPolpaFinal[horas_D14[idx_hora]] >=
        #             bombeamento_acumulado_polpa_hora_anterior(idx_hora) -
        #             (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)
        #             + lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_2b_{horas_D14[idx_hora]}",
        #     )

        # subject to Producao2c{t in 2..H}: #maximo de 1s
        #    Xf[t] <= X[t-1]*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_2c_{horas_D14[idx_hora]}",
        #     )

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



        # Restrições de SEQUENCIAMENTO FÁBRICA - CLIENTE para Bombeamento de Água

        # Contabiliza o bombeamento acumulado de água - Xac
        varBombeamentoAguaAcumulado = LpVariable.dicts("Mineroduto_Bombeamento_Agua_Acumulado", (horas_D14), 0, len(horas_D14), LpInteger)

        # Indica o bombeamento final de água
        varBombeamentoAguaFinal = LpVariable.dicts("Mineroduto_Bombeamento_Agua_Final", (horas_D14), 0, len(horas_D14), LpInteger)

        # def bombeamento_acumulado_agua_hora_anterior(idx_hora):
        #     if idx_hora == 0:
        #         # subject to Producao2f{t in 1..H}: #maximo de 1s
        #         #    Xac[1] = 0;
        #         return parametros['calculados']['Bombeamento Acumulado Agua final semana anterior']
        #     else:
        #         return varBombeamentoAguaAcumulado[horas_D14[idx_hora-1]]

        # subject to Producao1a{t in 2..H}: #maximo de 1s
        #    Xac[t] <= Xac[t-1] + 1 + (1- X[t])*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <=
        #             bombeamento_acumulado_agua_hora_anterior(idx_hora) + 1 +
        #             (1 - (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_agua_1a_{horas_D14[idx_hora]}",
        #     )

        # # subject to Producao1b{t in 2..H}: #maximo de 1s
        # #    Xac[t] >= Xac[t-1] + 1 - (1- X[t])*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoAguaAcumulado[horas_D14[idx_hora]] >=
        #             bombeamento_acumulado_agua_hora_anterior(idx_hora) + 1 -
        #             (1 - (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_agua_1b_{horas_D14[idx_hora]}",
        #     )

        # # subject to Producao1c{t in 2..H}: #maximo de 1s
        # #    Xac[t] <= X[t]*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <=
        #             (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_agua_1c_{horas_D14[idx_hora]}",
        #     )

        # # subject to Producao2a{t in 2..H}: #maximo de 1s
        # #    Xf[t] <= Xac[t-1] + (1 - X[t-1] + X[t])*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoAguaFinal[horas_D14[idx_hora]] <=
        #             bombeamento_acumulado_agua_hora_anterior(idx_hora) +
        #             (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
        #             + (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_agua_2a_{horas_D14[idx_hora]}",
        #     )

        # # subject to Producao2b{t in 2..H}: #maximo de 1s
        # #    Xf[t] >= Xac[t-1] - (1 - X[t-1] + X[t])*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoAguaFinal[horas_D14[idx_hora]] >=
        #             bombeamento_acumulado_agua_hora_anterior(idx_hora) -
        #             (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
        #             + (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_agua_2b_{horas_D14[idx_hora]}",
            # )

        # subject to Producao2c{t in 2..H}: #maximo de 1s
        #    Xf[t] <= X[t-1]*M;

        # for idx_hora in range(len(horas_D14)):
        #     modelo += (
        #         varBombeamentoAguaFinal[horas_D14[idx_hora]] <=
        #             (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))*BIG_M_MINERODUTO,
        #         f"rest_seq_bomb_agua_2c_{horas_D14[idx_hora]}",
        #     )

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
                varBombeamentoAguaFinal[horas_D14[idx_hora]] <= PolpaLs,
                f"rest_seq_bomb_agua_2e_{horas_D14[idx_hora]}",
            )

        # subject to Producao2ee{t in 1..H}: #maximo de 1s
        #    Xac[t] <= dmax;

        for idx_hora in range(len(horas_D14)):
            modelo += (
                varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <= PolpaLs,
                f"rest_seq_bomb_agua_2ee_{horas_D14[idx_hora]}",
            )

        # Indica chegada de polpa em Ubu, por produto, por hora
        varPolpaUbu = LpVariable.dicts("Ubu_Chegada_Polpa", (produtos_conc, horas_D14), 0, None, LpContinuous)

        # Define a chegada de polpa em Ubu
        for produto in produtos_conc:
            for i in range(3*24,len(horas_Dm3_D14)):
                modelo += (
                    varPolpaUbu[produto][horas_Dm3_D14[i]]
                        == varBombeamentoPolpa[produto],
                    f"rest_define_PolpaUbu_{produto}_{horas_Dm3_D14[i]}",
                )

        # Indica a produção sem incorporação em Ubu, por dia
        varProducaoSemIncorporacao = LpVariable.dicts("Pelot_Producao_sem_Incorporacao", (produtos_usina, horas_D14), 0, max_producao_sem_incorporacao, LpContinuous)

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
                                varProducaoSemIncorporacao[produto_u][hora]*(1+0.65),
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
            elif lim_acum_campanha[produto_usina] > 0:
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
                return lim_acum_campanha[produto_usina]

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
                        lim_min_campanha[produto_usina] -
                        (1 - varFimCampanhaPelot[produto_usina][hora])*BIG_M,
                        f"rest_limiteMinCampanhaPelot_{produto_usina}_{hora}",
                )
                modelo += (
                    varProdSemIncorpAcumulada[produto_usina][hora] <=
                        lim_max_campanha[produto_usina],
                        f"rest_limiteMaxCampanhaPelot_{produto_usina}_{hora}",
                )

        # Restrições para calcular a janela da produção sem incorporação acumulada na pelotização, por produto, por hora

        def janela_pelot_anterior(produto_usina, idx_hora):
            if idx_hora > 0:
                return varJanelaProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora-1]]
            else:
                return lim_acum_janela[produto_usina]

        for produto_usina in produtos_usina:

            for idx_hora in range(len(horas_D14)):
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][horas_D14[idx_hora]] <=
                        janela_pelot_anterior(produto_usina, idx_hora)
                        + 1
                        + (1 - lpSum([varProdutoPelot[produto_conc][produto_usina][horas_D14[idx_hora]] for produto_conc in produtos_conc]))*BIG_M,
                    f"rest_1a_janelaProdSemIncorpAcum_{produto_usina}_{horas_D14[idx_hora]}",
                )

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
                        lim_min_janela[produto_usina] -
                        (1 - varFimCampanhaPelot[produto_usina][hora])*BIG_M,
                        f"rest_limiteMinJanelaCampanhaPelot_{produto_usina}_{hora}",
                )
                modelo += (
                    varJanelaProdSemIncorpAcumulada[produto_usina][hora] <=
                        lim_max_janela[produto_usina],
                        f"rest_limiteMaxJanelaCampanhaPelot_{produto_usina}_{hora}",
                )

        # Indica o estoque de polpa em Ubu, por hora
        varEstoquePolpaUbu = LpVariable.dicts("Ubu_Estoque_Polpa", (produtos_conc, horas_D14),
                                            min_estoque_polpa_ubu, max_estoque_polpa_ubu,
                                            LpContinuous)

        varVolumePraca  = LpVariable.dicts("Praca_Ubu_Filtragem", (produtos_conc, horas_D14), 0, max_taxa_envio_patio, LpContinuous)
        varEstoquePraca = LpVariable.dicts("Praca_Ubu_Estoque_Acumul_(ignorado)", (produtos_conc, horas_D14),
                                        0, max_taxa_envio_patio,
                                        LpContinuous)

        varRetornoPraca = LpVariable.dicts("Praca_Ubu_Retorno", (produtos_conc, horas_D14),
                                        0,
                                        max_taxa_retorno_patio_usina,
                                        LpContinuous)
        varEstoqueRetornoPraca = LpVariable.dicts("Praca_Ubu_Estoque_Acumul_Previamente_(pode_usar)",
                                                (produtos_conc, horas_D14), min_estoque_patio_usina, max_estoque_patio_usina, LpContinuous)

        varLiberaVolumePraca = LpVariable.dicts("Praca_Ubu_Libera_Transf_Estoque", (horas_D14), 0, 1, LpInteger)

        # Define o estoque de polpa em Ubu da segunda hora em diante
        for produto in produtos_conc:
            for i in range(1, len(horas_D14)):
                modelo += (
                    varEstoquePolpaUbu[produto][horas_D14[i]] == varEstoquePolpaUbu[produto][horas_D14[i-1]]
                                                                + varPolpaUbu[produto][horas_D14[i]] *
                                                                    perc_solidos[self.extrair_dia(hora)] *
                                                                    densidade[self.extrair_dia(hora)]
                                                                - lpSum(varProducaoUbu[produto][produto_u][horas_D14[i]]
                                                                        for produto_u in produtos_usina)
                                                                - varVolumePraca[produto][horas_D14[i]]
                                                                + varRetornoPraca[produto][horas_D14[i]],
                    f"rest_define_EstoquePolpaUbu_{produto}_{horas_D14[i]}",
                )
            # Define o estoque de polpa em Ubu da primeira hora
            modelo += (
                varEstoquePolpaUbu[produto][horas_D14[0]] == estoque_polpa_ubu[produto]  +
                                                    varPolpaUbu[produto][horas_D14[0]] *
                                                        perc_solidos[self.extrair_dia(hora)] *
                                                        densidade[self.extrair_dia(hora)] 
                                                    - lpSum(varProducaoUbu[produto][produto_u][horas_D14[0]]
                                                            for produto_u in produtos_usina)
                                                    - varVolumePraca[produto][horas_D14[0]]
                                                    + varRetornoPraca[produto][horas_D14[0]],
                f"rest_define_EstoquePolpaUbu_{produto}_{horas_D14[0]}",
            )

        # Trata a taxa máxima de transferência (retorno) de material do pátio para a usina
        for hora in horas_D14:
            modelo += (
                lpSum(varRetornoPraca[produto][hora] for produto in produtos_conc) <= max_taxa_retorno_patio_usina,
                f"rest_define_taxa_retorno_praca_Pelot_{hora}",
            )

        #limita o estoque total dos produtos
        for hora in horas_D14:
            modelo += (
                lpSum(varEstoquePolpaUbu[produto][hora]
                    for produto in produtos_conc) <= max_estoque_polpa_ubu,
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
                varEstoqueRetornoPraca[produto][horas_D14[0]] == estoque_inicial_patio_usina[produto]
                                                        - varRetornoPraca[produto][horas_D14[0]],
                f"rest_define_EstoqueRetornoPatio_{produto}_{horas_D14[0]}",
            )

        #
        for i in range(1, len(horas_D14)):
            modelo += (
                lpSum(varVolumePraca[produto][horas_D14[i]]
                    for produto in produtos_conc)
                <=  max_taxa_envio_patio * varLiberaVolumePraca[horas_D14[i]],
                f"rest_define_taxa_tranferencia_para_patio_{horas_D14[i]}",
            )

        # Restricao de controle de transferencia para estoque de patio
        for i in range(1, len(horas_D14)):
            modelo += (
                lpSum(varEstoquePolpaUbu[produto][horas_D14[i]]
                    for produto in produtos_conc)
                - fator_limite_excesso_patio*max_estoque_polpa_ubu
                <= BIG_M * varLiberaVolumePraca[horas_D14[i]],
                f"rest_define_liberacao_tranferencia_para_pataio_{horas_D14[i]}",
            )

        for i in range(1, len(horas_D14)):
            modelo += (
                fator_limite_excesso_patio*max_estoque_polpa_ubu
                - lpSum(varEstoquePolpaUbu[produto][horas_D14[i]]
                        for produto in produtos_conc)
                <= BIG_M * (1-varLiberaVolumePraca[horas_D14[i]]),
                f"rest_define_tranferencia_para_patio_{horas_D14[i]}",
            )

        # Indica, para cada navio, se é a hora que inicia o carregamento
        varInicioCarregNavio = LpVariable.dicts("Porto_Inicio_Carregamento", (navios, horas_D14), 0, 1, LpInteger)

        # Indica, para cada navio, em que data começa o carregamento
        varDataInicioCarregNavio = LpVariable.dicts("Porto_Data_Carregamento", (navios), 0, None, LpContinuous)

        # Indica o estoque de produto no pátio de Ubu, por hora
        varEstoqueProdutoPatio = LpVariable.dicts("Porto_Estoque_Patio", (produtos_usina, horas_D14),
                                                capacidade_patio_porto_min, capacidade_patio_porto_max,
                                                LpContinuous)

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
            lpSum([idx_hora*varInicioCarregNavio[navio][horas_D14[idx_hora]] for idx_hora in range(len(horas_D14))]) >= data_chegada_navio[navio],
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
                                taxa_carreg_navios[navio] *
                                produtos_navio[navio][produto]
                                    for navio in navios
                                        for idx_hora_s in range(max(idx_hora-math.ceil(carga_navios[navio]/taxa_carreg_navios[navio])+1,1), idx_hora+1)]),
                    f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[idx_hora]}",
                )
            # Define o estoque de produto no pátio de Ubu do primeiro dia
            modelo += (
                varEstoqueProdutoPatio[produto][horas_D14[0]]
                    == estoque_produto_patio[produto] +
                    varProducaoSemIncorporacao[produto][horas_D14[0]] -
                    lpSum([varInicioCarregNavio[navio][horas_D14[0]] *
                            taxa_carreg_navios[navio] *
                            produtos_navio[navio][produto]
                            for navio in navios]),
                f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[0]}",
            )

        varVolumeAtrasadoNavio = LpVariable.dicts("Porto_Volume_Atrasado_Navios", (navios_ate_d14), 0, None, LpContinuous)

        for navio in navios_ate_d14:
            modelo += (
                varVolumeAtrasadoNavio[navio] ==
                    (varDataInicioCarregNavio[navio] - data_chegada_navio[navio]) *
                    taxa_carreg_navios[navio],
                f"rest_define_VolumeAtrasadoNavio_{navio}",
            )

        w_teste = LpVariable.dicts("w_teste", (produtos_conc, horas_D14), 0, 1, LpInteger)
        Fixadas = LpVariable.dicts("fixadas", (produtos_conc, horas_D14), 0, 1, LpInteger)

        for produto in produtos_conc:
            for hora in horas_D14:
                modelo += (w_teste[produto][hora] >= 0,  f"teste7_{produto}_{hora}")
                modelo += (Fixadas[produto][hora] >= 0,  f"teste8_{produto}_{hora}")

        # -----------------------------------------------------------------------------

        # funcao_objetivo = [fo.strip() for fo in args.funcao_objetivo[1:-1].split(',')]

        # for fo in funcao_objetivo:
        #     if not fo in ['max_brit', 'min_atr_nav', 'max_conc', 'max_pelot', 'max_bombEB07']:
        #         raise Exception(f"Função objetivo {fo} não implementada!")

        # Definindo a função objetivo
        fo = 0
        # if 'min_atr_nav' in funcao_objetivo:
        # fo += - (lpSum([varVolumeAtrasadoNavio[navio] for navio in navios_ate_d14]))
        # if 'max_brit' in funcao_objetivo:
        #     fo += lpSum([varTaxaBritagem[produto_mina][hora] for produto_mina in produtos_mina for hora in horas_D14])
        # if 'max_conc' in funcao_objetivo:
        #     fo += lpSum([varTaxaAlim[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
        # if 'max_pelot' in funcao_objetivo:
        fo += lpSum([varProducaoSemIncorporacao[produto_usina][hora] for produto_usina in produtos_usina for hora in horas_D14])
        # if 'max_bombEB07' in funcao_objetivo:
        #     fo += lpSum([varBombeadoEB07[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])

        params_heu = {
            'BIG_M' :BIG_M,
            'AguaLi': cenario['mineroduto']['janela_min_bombeamento_agua'],
            'AguaLs': cenario['mineroduto']['janela_max_bombeamento_agua'],
            'PolpaLi': cenario['mineroduto']['janela_min_bombeamento_polpa'],
            'PolpaLs': cenario['mineroduto']['janela_max_bombeamento_polpa'],
            'w_test': w_teste,
            }


        # if not (args.relax_and_fix or args.opt_partes):
            # nome_arquivo_log_solver = self.gerar_nome_arquivo_saida(f'{args.pasta_saida}/{args.nome}_{f"{cenario['geral']['nome']}_resultados_1_solver_completo"}, 'log', not args.nao_sobrescrever_arquivos)
            # solver.optionsDict['logPath'] = nome_arquivo_log_solver
            # The problem is solved using PuLP's choice of Solver
        solver.solve(modelo)
            # tempo_modelo_completo = modelo.solutionTime
        #     # valor_fo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo = self.verifica_status_solucao(nome_arquivo_log_solver)
        # elif args.relax_and_fix:
        #     valor_fo_modelo_relaxado, tempo_modelo_relaxado, gap_modelo_relaxado, valor_fo_modelo_completo, tempo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo, nome_arquivo_log_solver = self.heuristica_otim_por_partes(modelo, f"{cenario['geral']['nome']}_resultados_1", varBombeamentoPolpa, produtos_conc, horas_D14, solver, args, fo, params_heu)
        # elif args.opt_partes:
        #     valor_fo_modelo_relaxado, tempo_modelo_relaxado, gap_modelo_relaxado, valor_fo_modelo_completo, tempo_modelo_completo, status_solucao_modelo_completo, gap_modelo_completo, nome_arquivo_log_solver = self.heuristica_relax_and_fix(modelo, f"{cenario['geral']['nome']}_resultados_1", params_heu, varBombeamentoPolpa, produtos_conc, horas_D14, solver, args, fo)


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

        if not os.path.exists(args.pasta_saida):
            os.makedirs(args.pasta_saida)

        nome_arquivo_saida = self.gerar_nome_arquivo_saida(f"{cenario['geral']['nome']}_resultados_1")
        with open(f'{args.pasta_saida}/{nome_arquivo_saida}', "w", encoding="utf8") as f:
            json.dump(resultados, f)

        return modelo.status, resultados

