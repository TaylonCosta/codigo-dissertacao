print(f'Inicializando otimizador...   ', end='')

from model_p1 import Model_p1
from model_p2 import Model_p2

import json
from openpyxl import load_workbook # usado para ler a planilha
from pulp import *                 # usado para resolver o problema de otimização
import math
import pandas                      # usado para ler a aba TAXA da planilha
import pickle                      # usado para salvar os resultados
import argparse                    # usado para tratar os argumentos do script
import yaml                        # usado para obter os parâmetros do cenário a ser experimentado

def ler_cenario(nome_arquivo):
    "Abre o arquivo YAML com parâmetros do cenário"
    with open(nome_arquivo, 'r') as arquivo:
        cenario = yaml.safe_load(arquivo)
    return cenario

def gerar_nome_arquivo_saida(nome_base_arquivo):
    """ Gera o nome padronizado do arquivo de saída """
    if not os.path.exists(nome_base_arquivo + ".json"):
        return nome_base_arquivo + ".json"
    
    contador = 1
    while os.path.exists(f"{nome_base_arquivo}_{contador}.json"):
        contador += 1
    return f"{nome_base_arquivo}_{contador}.json"

parser = argparse.ArgumentParser(description='Otimizador Plano Semanal')
parser.add_argument('-s', '--solver', default='GUROBI', type=str, help='Nome do otimizador a ser usado')
parser.add_argument('-c', '--cenario', default='cenarios/ws0.yaml', type=str, help='Caminho para o arquivo do cenário a ser experimentado')
parser.add_argument('-o', '--pasta-saida', default='experimentos', type=str, help='Pasta onde serão salvos os arquivos de resultados')
args = parser.parse_args()

print(f'[OK]\nLendo arquivo {args.cenario}...   ', end='')
# Abre o arquivo YAML com dados do cenário (parâmetros do problema)
cenario = ler_cenario(args.cenario)

# -----------------------------------------------------------------------------
# Solver
print(f'[OK]\nInstanciando solver {args.solver}...   ', end='')
solver = getSolver(args.solver, timeLimit=cenario['geral']['timeLimit'], options=[("MIPgap", cenario['geral']['mipgap'])])

#------------------------------------------------------------------------------

print(f'[OK]\nAbrindo planilha {cenario["geral"]["planilha"]}...   ', end='')
# Abre a planilha e força o cálculo das fórmulas
wb = load_workbook(cenario['geral']['planilha'], data_only=True)
wb.calculation.calcMode = "auto"

# -----------------------------------------------------------------------------
# Índices usados pelas variáveis e parâmetros

print(f'[OK]\nCriando índices...   ', end='')
dias =      [f'd{dia+1:02d}' for dia in range(14)]    # d01, d02, ...   , d14
horas =     [f'h{hora+1:02d}' for hora in range(24)]  # h01, h02, ...   , h24
horas_D14 = [f'{dia}_{hora}' for dia in dias for hora in horas] # d01_h01, d01_h02, ...   , d14_h24
horas_Dm3 = [f'dm{dia+1:02d}_h{hora+1:02d}' for dia in range(-4,-1) for hora in range(len(horas))] # dm-3_h01, dm-3_h02, ...   , dm-1_h24
horas_Dm3_D14 = horas_Dm3 + horas_D14
produtos_conc = cenario['concentrador']['produtos_conc']
produtos_usina = cenario['usina']['produtos_usina']

# TODO: vir do cenário
de_para_produtos_mina_conc = {'PRDT': {'PRDT_C': 1}}

# CLS → PDR/MX
# CNS → PDR/STD e PBF/HB
# CHS → PBF/MB45 e PBF/STD
de_para_produtos_conc_usina = {'PRDT_C': {'PRDT_U': 1}}

# Obs.: índices dos navios são definidos ao ler os dados da aba NAVIOS

BIG_M = 10e6 # Big M

opcoes_restricoes = ['fixado_pelo_usuario', 'fixado_pelo_modelo', 'livre']

print(f'[OK]\nObtendo parâmetros do cenário...   ', end='')

janela_planejamento = cenario['geral']['janela_planejamento']

#verificar se não vai mesmo britagem 

taxa_alimentacao_britagem = cenario['mina']['taxa_alimentacao_britagem']
disponibilidade_britagem = cenario['mina']['disponibilidade_britagem']
utilizacao_britagem = cenario['mina']['utilizacao_britagem']

taxa_producao_britagem = {dias[d]: taxa_alimentacao_britagem[d] * 
                                   disponibilidade_britagem[d]/100 * 
                                   utilizacao_britagem[d]/100 
                          for d in range(len(dias))}

# Mina
campanha_c3 = cenario['mina']['campanha']
produtos_mina = set()
for campanha in campanha_c3:
    produtos_mina.add(campanha[0])
produtos_mina = list(produtos_mina)

produtos_britagem = {produto: {hora: 0 for hora in horas_D14} for produto in produtos_mina}
campanha_atual = 0
for hora in horas_D14:
    if campanha_atual < len(campanha_c3) and hora == campanha_c3[campanha_atual][1]:
        produto_atual = campanha_c3[campanha_atual][0]
        campanha_atual += 1
    produtos_britagem[produto_atual][hora] = 1

# Concentrador
estoque_pulmao_inicial_concentrador = {}
for produto, estoque in cenario['concentrador']['estoque_pulmao_inicial_concentrador']:
    estoque_pulmao_inicial_concentrador[produto] = estoque
min_estoque_pulmao_concentrador = cenario['concentrador']['min_estoque_pulmao_concentrador']
max_estoque_pulmao_concentrador = cenario['concentrador']['max_estoque_pulmao_concentrador']
faixas_producao_concentrador = cenario['concentrador']['faixas_producao_concentrador']
max_taxa_alimentacao = cenario['concentrador']['max_taxa_alimentacao']
min_taxa_alimentacao = cenario['concentrador']['min_taxa_alimentacao']
taxa_alimentacao_fixa = cenario['concentrador']['taxa_alimentacao_fixa']
fixar_taxa_alimentacao = cenario['concentrador']['fixar_taxa_alimentacao']
numero_faixas_producao = cenario['concentrador']['numero_faixas_producao']

# Mineroduto

estoque_eb06_d0 = {}
for produto, estoque in cenario['mineroduto']['estoque_inicial_eb06']:
    estoque_eb06_d0[produto] = estoque

estoque_eb07_d0 = {}
for produto, estoque in cenario['mineroduto']['estoque_inicial_eb07']:
    estoque_eb07_d0[produto] = estoque

bombeamento_matipo = cenario['mineroduto']['bombeamento_matipo']

min_capacidade_eb_07 = cenario['mineroduto']['min_capacidade_eb07']
max_capacidade_eb_07 = cenario['mineroduto']['max_capacidade_eb07']

# Usina
max_producao_sem_incorporacao = cenario['usina']['max_producao_sem_incorporacao']
min_producao_sem_incorporacao = cenario['usina']['min_producao_sem_incorporacao']
producao_sem_incorporacao_fixa = cenario['usina']['producao_sem_incorporacao_fixa']
fixar_producao_sem_incorporacao = cenario['usina']['fixar_producao_sem_incorporacao']
min_estoque_polpa_ubu = cenario['usina']['min_estoque_polpa_ubu']
max_estoque_polpa_ubu = cenario['usina']['max_estoque_polpa_ubu']
max_taxa_retorno_patio_usina = cenario['usina']['max_taxa_retorno_patio_usina']
min_estoque_patio_usina = cenario['usina']['min_estoque_patio_usina']
max_estoque_patio_usina = cenario['usina']['max_estoque_patio_usina']
estoque_inicial_patio_usina = cenario['usina']['estoque_inicial_patio_usina']

capacidade_carreg_porto_por_dia = cenario['porto']['capacidade_carreg_porto_por_dia']  # número de navios

janela_min_bombeamento_polpa = cenario['mineroduto']['janela_min_bombeamento_polpa'] # Mínimo de 1's consecutivos no bombeamento de polpa
janela_max_bombeamento_polpa = cenario['mineroduto']['janela_max_bombeamento_polpa']
fixar_janela_bombeamento = cenario['mineroduto']['fixar_janela_bombeamento']
janela_fixa_bombeamento_polpa = cenario['mineroduto']['janela_fixa_bombeamento_polpa']
bombeamento_restante_janela_anterior_polpa = cenario['mineroduto']['bombeamento_restante_janela_anterior_polpa']
bombeamento_restante_janela_anterior_agua = cenario['mineroduto']['bombeamento_restante_janela_anterior_agua']

janela_min_bombeamento_agua = cenario['mineroduto']['janela_min_bombeamento_agua'] # Mínimo de 1's consecutivos no bombeamento de agua
janela_max_bombeamento_agua = cenario['mineroduto']['janela_max_bombeamento_agua']
fixar_janela_bombeamento_agua = cenario['mineroduto']['fixar_janela_bombeamento_agua']
janela_fixa_bombeamento_agua = cenario['mineroduto']['janela_fixa_bombeamento_agua']
janela_para_fixar_bombeamento_agua = cenario['mineroduto']['janela_para_fixar_bombeamento_agua']
nro_janelas_livres_agua = cenario['mineroduto']['nro_janelas_livres_agua']
janela_livre_min_bombeamento_agua = cenario['mineroduto']['janela_livre_min_bombeamento_agua']
janela_livre_max_bombeamento_agua = cenario['mineroduto']['janela_livre_max_bombeamento_agua']

utilizacao_minima_mineroduto = cenario['mineroduto']['utilizacao_minima_mineroduto'] # A quantidade de água bombeada (%) não pode ser maior que 1-param
janela_da_utilizacao_minima_mineroduto_horas = cenario['mineroduto']['janela_da_utilizacao_minima_mineroduto_horas']

tempo_mineroduto = cenario['mineroduto']['tempo_mineroduto']

max_taxa_envio_patio = cenario['mineroduto']['max_taxa_envio_patio']

fator_limite_excesso_patio = cenario['mineroduto']['fator_limite_excesso_patio']

# Paradas de manutenção
inicio_manutencoes_britagem = cenario['mina']['inicio_manutencoes_britagem']
duracao_manutencoes_britagem = cenario['mina']['duracao_manutencoes_britagem']

inicio_manutencoes_concentrador = cenario['concentrador']['inicio_manutencoes_concentrador']
duracao_manutencoes_concentrador = cenario['concentrador']['duracao_manutencoes_concentrador']

inicio_manutencoes_mineroduto = cenario['mineroduto']['inicio_manutencoes_mineroduto']
duracao_manutencoes_mineroduto = cenario['mineroduto']['duracao_manutencoes_mineroduto']

inicio_manutencoes_usina = cenario['usina']['inicio_manutencoes_usina']
duracao_manutencoes_usina = cenario['usina']['duracao_manutencoes_usina']

def extrair_dia(hora):
    ''' Retorna o dia de uma hora no formato dXX_hYY '''
    return hora.split('_')[0]

def extrair_hora(dia):
    return (int(dia[1:])-1)*24

def indice_da_hora(hora):
    return (int(hora[1:3])-1)*24+int(hora[-2:])-1

resultados_planilha = {}

# -----------------------------------------------------------------------------

print(f'[OK]\nObtendo parâmetros da planilha...   ', end='')

# Lê os dados da aba MINA
ws = wb["MINA"]

# configuração das linhas onde se encontram os parâmetros
conf_parametros_mina = {
    'Campanha - C3': 2,
    'PPCa - C3': 3,
    'PPCc - C3': 4,
    'Pc - C3': 5,
    'Al2O3a - C3': 6,
    'Al2O3c - C3': 7,
    'Hea - C3': 8,
    'Fe_a - C3': 9,
    'Hec - C3': 10,
    'Umidade - C3': 14,
    'Dif. de Balanço - C3': 15,
    'Sól - C3': 16,
    'DF - C3': 17,
    'UD - C3': 18,
    'Número de Tanque - EB06': 33,
    'Utilização - M3': 35,
    'Disponibilidade - M3': 36,
    'Vazão bombas - M3': 37,
    'Utilização - EB07': 41,
    'Disponibilidade - EB07': 42,
    'Vazão bombas - EB07': 43,
}

# colunas onde se encontram os dados da aba mina
coluna_dia_inicial = 'E'
coluna_dia_final = 'R'
coluna_min = 'S'
coluna_max = 'T'

# guarda os parâmetros da aba mina
parametros_mina = {}
# guarda os limites mínimo e máximo de cada parâmetro
min_parametros_mina = {}
max_parametros_mina = {}

# Lê a aba mina guardando os valores dos parâmetros e os valores mínimos e máximos
for parametro in conf_parametros_mina:
    linha = conf_parametros_mina[parametro]
    parametros_mina[parametro] = {}
    for idx, cell in enumerate(ws[coluna_dia_inicial+str(linha)+':'+coluna_dia_final+str(linha)][0]):
        parametros_mina[parametro][dias[idx]] = cell.value
    min_parametros_mina[parametro] = ws[coluna_min+str(linha)].value if ws[coluna_min+str(linha)].value is not None else 0
    max_parametros_mina[parametro] = ws[coluna_max+str(linha)].value if ws[coluna_max+str(linha)].value is not None  else BIG_M

# Lê o parâmetro de geração de lama
fatorGeracaoLama = ws["D26"].value

# print('\n CONFERINDO parâmetros da MINA')
# print(f'{parametros_mina=}')
# print(f'{min_parametros_mina=}')
# print(f'{max_parametros_mina=}')
# print(f'{fatorGeracaoLama=}')

# Validando se os valores dos parâmetros se encontram dentro dos valores mínimos e máximos

for parametro in parametros_mina:
    if parametro != 'Campanha - C3':
        if (min(parametros_mina[parametro].values()) < min_parametros_mina[parametro]):
            print('ATENÇÃO: O valor mínimo de ' + parametro + ' está abaixo do permitido')
        elif (max(parametros_mina[parametro].values()) > max_parametros_mina[parametro]):
            print('ATENÇÃO: O valor máximo de ' + parametro + ' está acima do permitido')

# -----------------------------------------------------------------------------

# Lendo dados da aba MINERODUTO(-D3)

ws = wb["MINERODUTO(-D3)"]

# configuração das linhas onde se encontram os parâmetros
conf_parametros_mineroduto_md3 = {
    'Estoque EB06 -D3': 5,
    'Bombeamento Polpa -D3': 6,
    'Bombeado -D3': 7,
}

def get_column_name(column_number):
    ''' Retorna o nome de uma coluna de excel correspondente ao índice passado'''
    column_name = ""
    while column_number > 0:
        column_number, remainder = divmod(column_number - 1, 26)
        column_name = chr(65 + remainder) + column_name
    return column_name

coluna_hora_inicial_mD3 = 3
coluna_hora_final_mD3 = coluna_hora_inicial_mD3 + len(horas)*3 - 1

# guarda os parâmetros da aba MINERODUTO(-D3)
parametros_mineroduto_md3 = {}

# Lendo os parâmetros da planilha
for parametro in conf_parametros_mineroduto_md3:
    linha = conf_parametros_mineroduto_md3[parametro]    
    parametros_mineroduto_md3[parametro] = {}
    for idx, cell in enumerate(ws[f'{get_column_name(coluna_hora_inicial_mD3)}{linha}:{get_column_name(coluna_hora_final_mD3)}{linha}'][0]):
        parametros_mineroduto_md3[parametro][horas_Dm3[idx]] = cell.value

# Sobrescreve o bombeamento polpa -D3 com a informação do cenário, porque agora é multiproduto
parametros_mineroduto_md3['Bombeamento Polpa -D3'] = cenario['mineroduto']['bombeamento_polpa_dm3']

# print('\n CONFERINDO parâmetros da MINERODUTO(-D3)')
# print(f'{parametros_mineroduto_md3=}')

# -----------------------------------------------------------------------------

# Lendo dados da aba MINERODUTO-UBU

ws = wb["MINERODUTO-UBU"]

# Lendo parâmetros de uma única célula
# estoque_eb6_d0 = ws["C5"].value
estoque_polpa_ubu = ws["C11"].value

# configuração das linhas onde se encontram os parâmetros da aba MINERODUTO-UBU
conf_parametros_mineroduto_ubu = {
    'Capacidade EB06': 7,
    'Polpa Ubu (65Hs) - AJUSTE': 9,
}

# colunas onde se encontram os dados da aba MINERODUTO-UBU
coluna_hora_inicial_d14 = 4
coluna_hora_final_d14 = coluna_hora_inicial_d14 + len(horas)*len(dias) - 1

# guarda os parâmetros da aba MINERODUTO-UBU
parametros_mineroduto_ubu = {}

# Lendo os parâmetros da planilha
for parametro in conf_parametros_mineroduto_ubu:
    linha = conf_parametros_mineroduto_ubu[parametro]
    parametros_mineroduto_ubu[parametro] = {}
    for idx, cell in enumerate(ws[f'{get_column_name(coluna_hora_inicial_d14)}{linha}:{get_column_name(coluna_hora_final_d14)}{linha}'][0]):
        parametros_mineroduto_ubu[parametro][horas_D14[idx]] = cell.value

# print('\n CONFERINDO parâmetros da MINERODUTO-UBU')
# print(f'{estoque_eb6_d0=}')
# print(f'{estoque_polpa_ubu=}')
#print(f'{parametros_mineroduto_ubu=}')

# -----------------------------------------------------------------------------

# Lendo dados da aba UBU

ws = wb["UBU"]

# configuração das linhas onde se encontram os parâmetros da aba UBU
conf_parametros_mineroduto_ubu = {
    'SE': 3,
    'PPC': 4,
    '- 325#': 5,
    'Si02': 6,
    'CaO': 7,
    'pH': 8,
    'Densid.': 9,
    # 'H20': 10,
    'UD': 11,
    'DF': 12,
    'Conv.': 13,
}

# colunas onde se encontram os dados da aba UBU
coluna_dia_inicial = 'D'
coluna_dia_final = 'Q'

# guarda os parâmetros da aba UBU
parametros_ubu = {}

# Lendo os parâmetros da planilha
for parametro in conf_parametros_mineroduto_ubu:
    linha = conf_parametros_mineroduto_ubu[parametro]
    parametros_ubu[parametro] = {}
    for idx, cell in enumerate(ws[coluna_dia_inicial+str(linha)+':'+coluna_dia_final+str(linha)][0]):
        parametros_ubu[parametro][dias[idx]] = cell.value

# print('\n CONFERINDO parâmetros da aba UBU')
# print(f'{parametros_ubu}')

# -----------------------------------------------------------------------------

# Lendo dados da aba PÁTIO-PORTO

ws = wb["PÁTIO-PORTO"]

# estoque_produto_patio_d0 = ws["D10"].value
estoque_produto_patio_d0 = cenario['porto']['estoque_produto_patio']

# -----------------------------------------------------------------------------

# Lendo dados da aba NAVIOS

ws = wb["NAVIOS"]

# configuração das linhas onde se encontram os parâmetros da aba NAVIOS
conf_parametros_navios = {
    'NAVIOS':'A',
    'DATA-PLANEJADA':'B',
    'DATA-REAL':'C',
    'VOLUME':'D',
}

# guarda os parâmetros da aba NAVIOS
parametros_navios = {}

# Lendo os parâmetros da planilha
# Obs.: aqui os navios são indexados por índice, mas isso será alterado mais adiante
#       porque o mesmo nome de navio pode aparecer mais de uma vez
for parametro in conf_parametros_navios:
    coluna = conf_parametros_navios[parametro]
    parametros_navios[parametro] = {}
    linha = 2
    cell = ws[coluna+str(linha)]
    while cell.value is not None:
        parametros_navios[parametro][linha-2] = cell.value
        linha += 1
        cell = ws[coluna+str(linha)]

# -----------------------------------------------------------------------------

# Lendo dados da aba TAXA

# Usa Pandas porque é mais fácil para fazer agrupamento e cálculo de média de taxa de carregamento
excel_data_df = pandas.read_excel(cenario['geral']['planilha'], sheet_name='TAXA')
taxa_carreg_por_navio = excel_data_df.groupby('CUSTOMER')['Taxa de Carreg.'].mean()

# Guarda os índices dos navios
navios = []

# Esse trecho guarda as taxas de carregamento por navio e, além disso, altera os nomes dos navios
# pois eles podem se repetir, então é necessário adicionar um sufixo para diferenciá-los
parametros_navios['Taxa de Carreg.'] = {}
for idx in range(len(parametros_navios['NAVIOS'])):
    navio = parametros_navios['NAVIOS'][idx] + '-L' + str(idx+2)
    navios.append(navio)
    parametros_navios['Taxa de Carreg.'][navio] = taxa_carreg_por_navio[parametros_navios['NAVIOS'][idx]]
    for parametro in conf_parametros_navios:
        parametros_navios[parametro][navio] = parametros_navios[parametro][idx]
        del parametros_navios[parametro][idx]

# Guarda os índices dos navios com data-real até D14 (ou seja não inclui os navios D+14)
navios_ate_d14 = []
for parametro in ['DATA-PLANEJADA','DATA-REAL']:
    for navio in navios:
        if parametros_navios[parametro][navio] != 'D+14':
            # Usa o mesmo formato dos índices encontrados em `dias`
            parametros_navios[parametro][navio] = f'd{int(parametros_navios[parametro][navio][1:]):02d}'
            if parametro == 'DATA-PLANEJADA':
                navios_ate_d14.append(navio)
        else:
            parametros_navios[parametro][navio] = 'd15' # Para facilitar D+14 é tratado como d15

# -----------------------------------------------------------------------------

# PORTO

produtos_de_cada_navio = {navio:{produto_usina:0 for produto_usina in produtos_usina} for navio in navios}
for navio, produto_usina in cenario['porto']['produtos_de_cada_navio']:
    produtos_de_cada_navio[navio][produto_usina] = 1

print(f'[OK]\nDefinindo parâmetros calculados...   ', end='')

# Guarda os parâmetros calculados
parametros_calculados = {}


parametros_calculados['RP (Recuperação Mássica) - C3'] = {}
for dia in dias:
    if parametros_mina['Campanha - C3'][dia] == 'RNS':
        valor = -10.72 + (1.6346*parametros_mina['Fe_a - C3'][dia]) \
                -(3.815*parametros_mina['Al2O3a - C3'][dia])        \
                -(0.0984*parametros_mina['Hec - C3'][dia])
    elif parametros_mina['Campanha - C3'][dia] == 'RLS':
        valor = -13.18 + (1.614*parametros_mina['Fe_a - C3'][dia]) \
                -(3.92*parametros_mina['Al2O3a - C3'][dia])        \
                -(0.0187*parametros_mina['Hec - C3'][dia])
    parametros_calculados['RP (Recuperação Mássica) - C3'][dia] = valor

parametros_calculados['Rendimento Operacional - C3'] = {}
for dia in dias:
    parametros_calculados['Rendimento Operacional - C3'][dia] = parametros_mina['UD - C3'][dia] * parametros_mina['DF - C3'][dia] 

parametros_calculados['% Sólidos - EB06'] = {}
parametros_calculados['Densidade Polpa - EB06'] = {}
parametros_calculados['Relação: tms - EB06'] = {}
parametros_calculados['Densidade Polpa - EB07'] = {}
for dia in dias:
    parametros_calculados['% Sólidos - EB06'][dia] = parametros_mina['Sól - C3'][dia] - 0.012
    parametros_calculados['Densidade Polpa - EB06'][dia] = 1/((parametros_calculados['% Sólidos - EB06'][dia]/4.75)+(1-parametros_calculados['% Sólidos - EB06'][dia]))
    parametros_calculados['Relação: tms - EB06'][dia] = 5395*parametros_calculados['% Sólidos - EB06'][dia]*parametros_calculados['Densidade Polpa - EB06'][dia]/100
    parametros_calculados['Densidade Polpa - EB07'][dia] = parametros_calculados['Densidade Polpa - EB06'][dia]

parametros_calculados['H20'] = {}
for dia in dias:
    parametros_calculados['H20'][dia] = 3.296 + (0.002986*parametros_ubu['SE'][dia]) + (0.615*parametros_ubu['PPC'][dia])
   
parametros_calculados['Bombeamento Acumulado Polpa final semana anterior'] = 0
for idx_hora in range(len(horas_Dm3)-1,-1,-1):
    if parametros_mineroduto_md3['Bombeamento Polpa -D3'][idx_hora] == 'H20':
        break;
    else:
        parametros_calculados['Bombeamento Acumulado Polpa final semana anterior'] += 1;

parametros_calculados['Bombeamento Acumulado Agua final semana anterior'] = 0
for idx_hora in range(len(horas_Dm3)-1,-1,-1):
    if parametros_mineroduto_md3['Bombeamento Polpa -D3'][idx_hora] == 'H20':
        parametros_calculados['Bombeamento Acumulado Agua final semana anterior'] += 1;
    else:
        break;
        

# print('\n CONFERINDO parâmetros CALCULADOS')
# print(f'{parametros_calculados=}')

# print(f"{parametros_calculados['Bombeamento Acumulado final semana anterior']=}")

# -----------------------------------------------------------------------------
'''
print(f'[OK]\nDefinindo o modelo de otimização...   ', end='')
# Definindo modelo de otimização


# A variável prob é criada para conter os dados do problema
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
        dados[produto].append(int(taxa_producao_britagem[extrair_dia(hora)]*produtos_britagem[produto][hora]))
        modelo += (            
            varTaxaBritagem[produto][hora] <= int(taxa_producao_britagem[extrair_dia(hora)]*produtos_britagem[produto][hora]),
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
'''
'''
# Indica a hora de início das manutenções da britagem
varInicioManutencoesBritagem = LpVariable.dicts("Início Manutenção Britagem", (range(len(duracao_manutencoes_britagem)), horas_Dm3_D14), 0, 1, LpInteger)

# Restrição para garantir que a manutenção da britagem se inicia uma única vez
for idx_manut in range(len(duracao_manutencoes_britagem)):
    modelo += (
        lpSum([varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]] 
               for idx_hora in range(0, janela_planejamento*24)]) == 1,
        f"rest_define_InicioManutencoesBritagem_{idx_manut}",
    )

# Restrição que impede que as manutenções ocorram na segunda semana
for idx_manut in range(len(duracao_manutencoes_britagem)):
    modelo += (
        lpSum([varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]] 
               for idx_hora in range(janela_planejamento*24, len(horas_D14))]) == 0,
        f"rest_evita_InicioManutencoesBritagem_{idx_manut}",
    )

# Restrições para evitar que manutenções ocorram ao mesmo tempo
for idx_hora in range(len(horas_D14)):
    for idx_manut in range(len(duracao_manutencoes_britagem)):
        modelo += (
            varInicioManutencoesBritagem[idx_manut][horas_D14[idx_hora]] +
            lpSum(varInicioManutencoesBritagem[s][horas_D14[j]] 
                  for j in range(idx_hora-duracao_manutencoes_britagem[idx_manut]+1,idx_hora)
                  for s in range(len(duracao_manutencoes_britagem))
                  if s != idx_manut
                  )
            <= 1,            
           f"rest_separa_manutencoesBritagem_{idx_manut}_{idx_hora}",
        )

# Fixa o horário de início da manutenção do britagem se foi escolhido pelo usuário
for idx_manut, inicio in enumerate(inicio_manutencoes_britagem):
    if inicio != 'livre':
        modelo += (
            varInicioManutencoesBritagem[idx_manut][inicio] == 1,
            f"rest_fixa_InicioManutencaoBritagem_{idx_manut}",
        )

# Restrição tratar manutenção, lower bound e valor fixo de taxa de produção da britagem

for idx_hora in range(len(horas_D14)):
    # se está em manutenção, zera a taxa de produção da britagem
    for idx_manut in range(len(duracao_manutencoes_britagem)):
        modelo += (
            lpSum([varTaxaBritagem[produto][horas_D14[idx_hora]] for produto in produtos_mina])
                  <= BIG_M*(1 - lpSum(varInicioManutencoesBritagem[idx_manut][horas_D14[j]] 
                                      for j in range(idx_hora - duracao_manutencoes_britagem[idx_manut] + 1, idx_hora))),
            f"rest_manutencao_britagem_{idx_manut}_{horas_D14[idx_hora]}",
    )
    
    # Define lower bound 
    # (não parece ser necessário, pois não há limite mínimo da britagem)
    # modelo += ( 
    #     varTaxaBritagem[horas_D14[idx_hora]] >= 0 # min_taxa_britagem
    #                                         - BIG_M*(lpSum(varInicioManutencoesBritagem[idx_manut][horas_D14[j]] 
    #                                                     for idx_manut in range(len(duracao_manutencoes_britagem))
    #                                                     for j in range(idx_hora - duracao_manutencoes_britagem[idx_manut] + 1, idx_hora))),
    #     f"rest_LB_taxa_alim1_{horas_D14[idx_hora]}",
    # )
    modelo += (
        lpSum([varTaxaBritagem[produto][horas_D14[idx_hora]] for produto in produtos_mina])
             <= BIG_M*(1 - lpSum(varInicioManutencoesBritagem[idx_manut][horas_D14[j]]
                                 for idx_manut in range(len(duracao_manutencoes_britagem)) 
                                 for j in range(idx_hora - duracao_manutencoes_britagem[idx_manut] + 1, idx_hora))),
        f"rest_UB_taxa_britagem_{horas_D14[idx_hora]}",
    )

# Indica a hora de início das manutenções do concentrador
varInicioManutencoesConcentrador = LpVariable.dicts("Início Manutenção Concentrador", (range(len(duracao_manutencoes_concentrador)), horas_Dm3_D14), 0, 1, LpInteger)

# Restrição para garantir que a manutenção do concentrador se inicia uma única vez
for idx_manut in range(len(duracao_manutencoes_concentrador)):
    modelo += (
        lpSum([varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]] 
               for idx_hora in range(0, janela_planejamento*24)]) == 1,
        f"rest_define_InicioManutencoesConcentrador_{idx_manut}",
    )

# Restrição que impede que as manutenções ocorram na segunda semana
for idx_manut in range(len(duracao_manutencoes_concentrador)):
    modelo += (
        lpSum([varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]] 
               for idx_hora in range(janela_planejamento*24, len(horas_D14))]) == 0,
        f"rest_evita_InicioManutencoesConcentrador_{idx_manut}",
    )

# Restrições para evitar que manutenções ocorram ao mesmo tempo
for idx_hora in range(len(horas_D14)):
    for idx_manut in range(len(duracao_manutencoes_concentrador)):
        modelo += (
            varInicioManutencoesConcentrador[idx_manut][horas_D14[idx_hora]] +
            lpSum(varInicioManutencoesConcentrador[s][horas_D14[j]] 
                  for j in range(idx_hora-duracao_manutencoes_concentrador[idx_manut]+1,idx_hora)
                  for s in range(len(duracao_manutencoes_concentrador))
                  if s != idx_manut
                  )
            <= 1,            
           f"rest_separa_manutencoesConcentrador_{idx_manut}_{idx_hora}",
        )

# Fixa o horário de início da manutenção do concentrador se foi escolhido pelo usuário
for idx_manut, inicio in enumerate(inicio_manutencoes_concentrador):
    if inicio != 'livre':
        modelo += (
            varInicioManutencoesConcentrador[idx_manut][inicio] == 1,
            f"rest_fixa_InicioManutencaoConcentrador_{idx_manut}",
        )

# Restrição tratar manutenção, lower bound e valor fixo de taxa de alimentação

for idx_hora in range(len(horas_D14)):
    # se está em manutenção, zera a taxa de alimentação
    for idx_manut in range(len(duracao_manutencoes_concentrador)):
        modelo += (
            lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
                <= BIG_M*(1 - lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]] 
                                    for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
            f"rest_manutencao_concentrador_{idx_manut}_{horas_D14[idx_hora]}",
    )
    
    # Define lower bound
    modelo += (
        lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc]) 
            >= min_taxa_alimentacao - BIG_M*(lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]] 
                                                   for idx_manut in range(len(duracao_manutencoes_concentrador))
                                                   for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
        f"rest_LB_taxa_alim1_{horas_D14[idx_hora]}",
    )
    modelo += (
        lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc]) 
            <= BIG_M*(1 - lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
                                for idx_manut in range(len(duracao_manutencoes_concentrador)) 
                                for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
        f"rest_LB_taxa_alim2_{horas_D14[idx_hora]}",
    )

    # se a taxa de alimentacao é fixada pelo modelo ou pelo usuário
    if fixar_taxa_alimentacao in ['fixado_pelo_modelo','fixado_pelo_usuario']:
        taxa_fixa = taxa_alimentacao_fixa
        if fixar_taxa_alimentacao == 'fixado_pelo_modelo':
            varTaxaAlimFixa = LpVariable("Taxa Alimentacao - C3 Fixa", 0, max_taxa_alimentacao, LpContinuous)
            taxa_fixa = varTaxaAlimFixa
        modelo += (
            lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
                >= taxa_fixa - BIG_M*(lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
                                      for idx_manut in range(len(duracao_manutencoes_concentrador))
                                      for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
            f"rest_taxa_alim_fixa1_{horas_D14[idx_hora]}",
        )
        modelo += (
            lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc])
                <= BIG_M*(1 - lpSum(varInicioManutencoesConcentrador[idx_manut][horas_D14[j]]
                                    for idx_manut in range(len(duracao_manutencoes_concentrador))
                                    for j in range(idx_hora - duracao_manutencoes_concentrador[idx_manut] + 1, idx_hora))),
            f"rest_taxa_alim_fixa2_{horas_D14[idx_hora]}",
        )
        modelo += (
            lpSum([varTaxaAlim[produto][horas_D14[idx_hora]] for produto in produtos_conc]) <= taxa_fixa,
            f"rest_taxa_alim_fixa3_{horas_D14[idx_hora]}",
        )
'''
'''
# Puxada, por dia, é calculada a partir da taxa de alimentação e demais parâmetros
varPuxada = LpVariable.dicts("Puxada - C3 - Prog", (horas_D14), 0, None, LpContinuous) 
for hora in horas_D14:
    modelo += (
        varPuxada[hora] == lpSum([varTaxaAlim[produto][hora] for produto in produtos_conc])*parametros_mina['DF - C3'][extrair_dia(hora)],
        f"rest_define_Puxada_{hora}",
    )

# Produção, por produto do concentrador, por dia, é calculada a partir da taxa de alimentação e demais parâmetros
varProducao = LpVariable.dicts("Producao - C3 - Prog", (produtos_conc, horas_D14), 0, None, LpContinuous) 
for produto in produtos_conc:
    for hora in horas_D14:
        modelo += (
            varProducao[produto][hora]
                == varTaxaAlim[produto][hora] * 
                    (1-parametros_mina['Umidade - C3'][extrair_dia(hora)]) * 
                    parametros_calculados['RP (Recuperação Mássica) - C3'][extrair_dia(hora)] / 
                    100 * parametros_mina['DF - C3'][extrair_dia(hora)] * 
                    (1 - parametros_mina['Dif. de Balanço - C3'][extrair_dia(hora)] / 100),
            f"rest_define_Producao_{produto}_{hora}",
        )

# Produção Volume, por hora, é calculada a partir produção volume
varProducaoVolume = LpVariable.dicts("Producao volume/hora - C3 - Prog", (produtos_conc, horas_D14), 0, None, LpContinuous) 
for produto in produtos_conc:
    for hora in horas_D14:
        modelo += (
            varProducaoVolume[produto][hora]
                == varProducao[produto][hora] * (1/parametros_calculados['% Sólidos - EB06'][extrair_dia(hora)])
                                              * (1/parametros_calculados['Densidade Polpa - EB06'][extrair_dia(hora)]),
            f"rest_define_ProducaoVolume_{produto}_{hora}",
        )

# Geração de Lama, por dia, é calculada a partir da puxada
varGeracaoLama = LpVariable.dicts("Geracao de lama - C3 - Prog", (horas_D14), 0, None, LpContinuous) 
for hora in horas_D14:
    modelo += (
        varGeracaoLama[hora] == (varPuxada[hora]*(1-parametros_mina['Umidade - C3'][extrair_dia(hora)]))*(1-fatorGeracaoLama),
        f"rest_define_GeracaoLama_{hora}",
    )

# Rejeito Arenoso, por dia, é calculado a partir da puxada, geração de lama e produção
varRejeitoArenoso = LpVariable.dicts("Geracao de rejeito arenoso - C3 - Prog", (horas_D14), 0, None, LpContinuous) 
for hora in horas_D14:
    modelo += (
        varRejeitoArenoso[hora] == ((varPuxada[hora] * (1-parametros_mina['Umidade - C3'][extrair_dia(hora)]))) 
                                   - varGeracaoLama[hora] - lpSum(varProducao[produto][hora] for produto in produtos_conc),
        f"rest_define_RejeitoArenoso_{hora}",
    )

# Indica o estoque EB06, por hora
varEstoqueEB06 = LpVariable.dicts("Estoque EB06", (produtos_conc, horas_D14), 0, None, LpContinuous)
#varEstoqueEB04 = LpVariable.dicts("Estoque EB04", (produtos_conc, horas_D14), 0, None, LpContinuous)

# Indica se há bombeamento de polpa em cada hora
varBombeamentoPolpa = LpVariable.dicts("Bombeamento Polpa", (horas_Dm3_D14), 0, 1, LpInteger)

# Restrição de capacidade do estoque EB06
for hora in horas_D14:
    modelo += (
        lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc) 
            <= parametros_mineroduto_ubu['Capacidade EB06'][hora],
        f"rest_capacidade_EstoqueEB06_{hora}",
    )
'''

'''
# Restrição de capacidade do estoque EB04
for hora in horas_D14:
    modelo += (
        lpSum(varEstoqueEB04[produto][hora] for produto in produtos_conc) 
            <= capacidade_eb04,
        f"rest_capacidade_EstoqueEB04_{hora}",
    )

# Define se ha transferencia entre os tanques
varEnvioEB04EB06 = LpVariable.dicts("Envio EB04 para EB06", (produtos_conc, horas_D14), 0, 1, LpInteger)
varEnvioEB06EB04 = LpVariable.dicts("Envio EB06 para EB04", (produtos_conc, horas_D14), 0, 1, LpInteger)
# Define a quantidade da transferência entre os tanques
varTaxaEnvioEB04EB06 = LpVariable.dicts("Taxa Envio EB04 para EB06", (produtos_conc, horas_D14), 0, taxa_transferencia_entre_eb, LpContinuous)
varTaxaEnvioEB06EB04 = LpVariable.dicts("Taxa Envio EB06 para EB04", (produtos_conc, horas_D14), 0, taxa_transferencia_entre_eb, LpContinuous)
'''
'''
# Indica se há bombeamento de polpa em cada hora
varBombeamentoPolpa = LpVariable.dicts("Bombeamento Polpa", (produtos_conc, horas_Dm3_D14), 0, 1, LpInteger)


for produto in produtos_conc:
    for hora in horas_D14:
        modelo += (
            varTaxaEnvioEB06EB04[produto][hora] <= taxa_transferencia_entre_eb*varEnvioEB06EB04[produto][hora],
            f"rest_define_TaxaEnvioEB06EB04_{produto}_{hora}",
        )
        modelo += (
            varTaxaEnvioEB04EB06[produto][hora] <= taxa_transferencia_entre_eb*varEnvioEB04EB06[produto][hora],
            f"rest_define_TaxaEnvioEB04EB06_{produto}_{hora}",
        )

# Define o valor de estoque de EB06, por produto, da segunda hora em diante
for produto in produtos_conc:
    for i in range(1, len(horas_D14)):
        modelo += (
            varEstoqueEB06[produto][horas_D14[i]] 
                == varEstoqueEB06[produto][horas_D14[i-1]] 
                + varProducaoVolume[produto][horas_D14[i]] 
                - varBombeamentoPolpa[produto][horas_D14[i]]*parametros_mina['Vazão bombas - M3'][extrair_dia(horas_D14[i])]
                #+ varTaxaEnvioEB04EB06[produto][horas_D14[i]] 
                #- varTaxaEnvioEB06EB04[produto][horas_D14[i]]
                ,
                # + (varEnvioEB04EB06[produto][horas_D14[i]]-varEnvioEB06EB04[produto][horas_D14[i]])*taxa_transferencia_entre_eb,
            f"rest_define_EstoqueEB06_{produto}_{horas_D14[i]}",
        )

# Define o valor de estoque de EB06, por produto, da primeira hora
for produto in produtos_conc:
    modelo += (
        varEstoqueEB06[produto][horas_D14[0]]
            == estoque_eb06_d0[produto] + 
               varProducaoVolume[produto][horas_D14[0]] - 
               varBombeamentoPolpa[produto][horas_D14[0]]*parametros_mina['Vazão bombas - M3'][extrair_dia(horas_D14[0])]
               #+ varTaxaEnvioEB04EB06[produto][horas_D14[0]] 
                #- varTaxaEnvioEB06EB04[produto][horas_D14[0]]
                ,
               # +(varEnvioEB04EB06[produto][horas_D14[0]] - varEnvioEB06EB04[produto][horas_D14[0]])*taxa_transferencia_entre_eb,
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
                   # + (varEnvioEB06EB04[produto][horas_D14[i]] - varEnvioEB04EB06[produto][horas_D14[i]])*taxa_transferencia_entre_eb,
            f"rest_define_EstoqueEB04_{produto}_{horas_D14[i]}",
        )

# Define o valor de estoque de EB04, por produto, da primeira hora
for produto in produtos_conc:
    modelo += (
        varEstoqueEB04[produto][horas_D14[0]] 
            == estoque_eb04_d0[produto] + 
                - varTaxaEnvioEB04EB06[produto][horas_D14[0]] 
                + varTaxaEnvioEB06EB04[produto][horas_D14[0]],
                # (varEnvioEB06EB04[produto][horas_D14[0]] - varEnvioEB04EB06[produto][horas_D14[0]])*taxa_transferencia_entre_eb,
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
        fator_limite_excesso_EB04*parametros_mineroduto_ubu['Capacidade EB06'][hora] 
            - lpSum(varEstoqueEB06[produto][hora] for produto in produtos_conc)
            <= BIG_M * (1 - lpSum(varEnvioEB06EB04[produto][hora] for produto in produtos_conc)),
        f"rest_define_tranferencia_por_enchimento_tanque_{hora}",
    )
'''
#------------------------------------------- INICIA AQUI O MINERODUTO E TERMINA A PARTE 1 DO MODELO

'''
 # Indica o quanto foi bombeado de polpa, por produto do concentrador, em cada hora
varBombeado = LpVariable.dicts("Bombeado", (produtos_conc, horas_Dm3_D14), 0, None, LpContinuous)

# Carrega os dados de D-3
for idx_hora in range(len(horas_Dm3)):
    for produto in produtos_conc:
        if produto == parametros_mineroduto_md3['Bombeamento Polpa -D3'][idx_hora]:
            modelo += (
                varBombeamentoPolpa[produto][horas_Dm3[idx_hora]] == 1,
                f"rest_define_Bombeamento_inicial_{produto}_{horas_Dm3[idx_hora]}",
            )
            modelo += (
                varBombeado[produto][horas_Dm3[idx_hora]] == parametros_mineroduto_md3['Bombeado -D3'][horas_Dm3[idx_hora]],
                f"rest_define_Bombeado_inicial_{produto}_{horas_Dm3[idx_hora]}",
            )
        else:
            modelo += (
                varBombeamentoPolpa[produto][horas_Dm3[idx_hora]] == 0,
                f"rest_define_Bombeamento_inicial_{produto}_{horas_Dm3[idx_hora]}",
            )
            modelo += (
                varBombeado[produto][horas_Dm3[idx_hora]] == 0,
                f"rest_define_Bombeado_inicial_{produto}_{horas_Dm3[idx_hora]}",
            )

# Restrição para garantir que apenas um produto é bombeado por vez
for hora in horas_D14:
    modelo += (
        lpSum(varBombeamentoPolpa[produto][hora] for produto in produtos_conc) <= 1,
        f"rest_bombeamento_unico_produto_{hora}",
    )

def bombeamento_hora_anterior(produto, idx_hora):
    if idx_hora == 0:
        return varBombeamentoPolpa[produto][horas_Dm3[-1]]
    else:
        return varBombeamentoPolpa[produto][horas_D14[idx_hora-1]]

# Define o bombeamento de polpa para as horas de d01 a d14, respeitando as janelas mínimas de polpa e de água respectivamente
for produto in produtos_conc:
    for i, hora in enumerate(horas_D14[0:-janela_min_bombeamento_polpa+1]):
        modelo += (
            varBombeamentoPolpa[produto][horas_D14[i]] + 
                lpSum([varBombeamentoPolpa[produto][horas_D14[j]] for j in range(i+1, i+janela_min_bombeamento_polpa)]) >=
                    janela_min_bombeamento_polpa 
                    - janela_min_bombeamento_polpa*(1 - varBombeamentoPolpa[produto][horas_D14[i]] + bombeamento_hora_anterior(produto, i)),
            f"rest_janela_bombeamento_polpa_{produto}_{hora}",
    )
        
# Para a primeira hora é necessário considerar o bombeamento de polpa que já pode ter acontecido no dia anterior ao do planejamento
if parametros_calculados['Bombeamento Acumulado Polpa final semana anterior'] > 0:
    tamanho_primeira_janela = bombeamento_restante_janela_anterior_polpa
    produto_produto_polpa_semana_anterior = parametros_mineroduto_md3['Bombeamento Polpa -D3'][-1]
    modelo += (
        lpSum([varBombeamentoPolpa[produto_produto_polpa_semana_anterior][horas_D14[j]] for j in range(0, tamanho_primeira_janela)]) >= tamanho_primeira_janela,
        f"rest_primeira_janela_bombeamento_polpa_{produto_produto_polpa_semana_anterior}_{horas_D14[0]}",
    )

# Para a primeira hora é necessário considerar o bombeamento de água que já pode ter acontecido no dia anterior ao do planejamento

for produto in produtos_conc:
    if parametros_calculados['Bombeamento Acumulado Agua final semana anterior'] > 0:
        tamanho_primeira_janela = bombeamento_restante_janela_anterior_agua
        modelo += (
            lpSum([varBombeamentoPolpa[produto][horas_D14[j]] for j in range(0, tamanho_primeira_janela)]) == 0,
            f"rest_primeira_janela_bombeamento_polpa_{produto}_{horas_D14[0]}",
        )

if cenario['mineroduto']['considerar_janela_final']:
    # Trata os últimos horários (tempo menor que a janela mínima de bombeamento de polpa) para que os bombeamentos de polpa, 
    # se houverem sejam consecutivos até o final
    for produto in produtos_conc:
        for idx_hora in range(len(horas_D14)-janela_min_bombeamento_polpa+1, len(horas_D14)):
            modelo += (
                lpSum(varBombeamentoPolpa[produto][horas_D14[j]] for j in range(idx_hora,len(horas_D14)))
                    >= janela_min_bombeamento_polpa 
                        - (len(horas_D14)-idx_hora) + 1 
                        - janela_min_bombeamento_polpa*(1 - varBombeamentoPolpa[produto][horas_D14[idx_hora]]),
                f"rest_janela_bombeamento_polpa_{produto}_{horas_D14[idx_hora]}",
            )

#for produto in produtos_conc:
for i, hora in enumerate(horas_D14[0:-janela_min_bombeamento_agua+1]):
    modelo += (
        lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc)+ 
        lpSum([varBombeamentoPolpa[produto][horas_D14[j]] 
                for produto in produtos_conc for j in range(i+1, i+janela_min_bombeamento_agua)]) <=
            BIG_M*(1 + lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc) 
                     - lpSum(bombeamento_hora_anterior(produto, i) for produto in produtos_conc)),
        f"rest_janela_bombeamento_agua_{produto}_{hora}",
    )


if fixar_janela_bombeamento_agua == 'fixado_pelo_usuario':
    
    # limite_hora = -janela_fixa_bombeamento_agua
    limite_hora = janela_para_fixar_bombeamento_agua-janela_fixa_bombeamento_agua
    #for produto in produtos_conc:
    for i, hora in enumerate(horas_D14[0:limite_hora]):
        modelo += (
            lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc) + 
                lpSum([varBombeamentoPolpa[produto][horas_D14[j]] for produto in produtos_conc for j in range(i+1, i+janela_fixa_bombeamento_agua)]) <=
                    janela_fixa_bombeamento_agua*(1 + lpSum(varBombeamentoPolpa[produto][horas_D14[i]]for produto in produtos_conc) - lpSum(bombeamento_hora_anterior(produto, i) for produto in produtos_conc)),

            f"rest_fixar_janela_bombeamento_agua_{produto}_{hora}",
        )

    # if cenario['mineroduto']['considerar_janela_final']:
    #     limite_hora = janela_da_utilizacao_minima_mineroduto_horas-janela_fixa_bombeamento_agua
    # else:
    #     limite_hora = -2*janela_fixa_bombeamento_agua
    
    #for produto in produtos_conc:
    for i, hora in enumerate(horas_D14[0:limite_hora]):
        modelo += (
            lpSum(varBombeamentoPolpa[produto][horas_D14[i+janela_fixa_bombeamento_agua]] for produto in produtos_conc) >= 
            -lpSum(varBombeamentoPolpa[produto][horas_D14[i]] for produto in produtos_conc) + lpSum(bombeamento_hora_anterior(produto, i)for produto in produtos_conc),
            f"rest_retornar_bombeamento_polpa_{produto}_{hora}",
        )

# Trata a utilização mínima do mineroduto para bombear polpa
for i in range(0, len(horas_D14), janela_da_utilizacao_minima_mineroduto_horas):
    modelo += (
        lpSum(varBombeamentoPolpa[produto][horas_D14[j]] for produto in produtos_conc for j in range(i,i+janela_da_utilizacao_minima_mineroduto_horas)) 
                >= utilizacao_minima_mineroduto*janela_da_utilizacao_minima_mineroduto_horas,
            f"rest_utilizacao_min_mineroduto_{horas_D14[i]}",
    )

# Define a quantidade bombeada de polpa por hora
for produto in produtos_conc:
    for hora in horas_D14:
        modelo += (
            varBombeado[produto][hora] == varBombeamentoPolpa[produto][hora]*bombeamento_matipo[extrair_dia(hora)],
            f"rest_definie_bombeado_{produto}_{hora}",
        )

# Define a conservação de fluxo em matipo
estoque_eb07 = LpVariable.dicts("Estoque EB07", (produtos_conc, horas_D14), 0, None, LpContinuous)

for produto in produtos_conc:
    for i in range(1, len(horas_D14)):
        modelo += (
            estoque_eb07[produto][horas_D14[i]] == estoque_eb07[produto][horas_D14[i-1]] + varBombeamentoPolpa[produto][horas_D14[i]]*
                (parametros_mina['Vazão bombas - M3'][extrair_dia(horas_D14[i])]-bombeamento_matipo[extrair_dia(horas_D14[i])]),
            f"rest_definie_estoque_eb07_{produto}_{i}",
        )

    modelo += (
        estoque_eb07[produto][horas_D14[0]] == estoque_eb07_d0[produto] + varBombeamentoPolpa[produto][horas_D14[0]]*
            (parametros_mina['Vazão bombas - M3'][extrair_dia(horas_D14[0])]-bombeamento_matipo[extrair_dia(horas_D14[0])]),
        f"rest_definie_estoque_eb07_hora0_{produto}_{hora}",
    )

# Limita as quantidades de produtos no tanque eb07
for hora in horas_D14:
    modelo += (
        lpSum(estoque_eb07[produto][hora] for produto in produtos_conc) <= max_capacidade_eb_07,
        f"rest_limita_max_estoque_eb07_{produto}_{hora}",
    )
    modelo += (
        lpSum(estoque_eb07[produto][hora] for produto in produtos_conc) >= max_capacidade_eb_07*min_capacidade_eb_07,
        f"rest_limita_min_estoque_eb07_{produto}_{hora}",
    )

'''
'''
# Indica a hora de início das manutenções do mineroduto
varInicioManutencoesMineroduto = LpVariable.dicts("Início Manutenção Mineroduto", (range(len(duracao_manutencoes_mineroduto)), horas_Dm3_D14), 0, 1, LpInteger)

# Restrição para garantir que a manutenção do mineroduto se inicia uma única vez
for idx_manut in range(len(duracao_manutencoes_mineroduto)):
    modelo += (
        lpSum([varInicioManutencoesMineroduto[idx_manut][horas_D14[idx_hora]] 
               for idx_hora in range(0, janela_planejamento*24)]) == 1,
        f"rest_define_InicioManutencoesMineroduto_{idx_manut}",
    )

# Restrição que impede que as manutenções ocorram na segunda semana
for idx_manut in range(len(duracao_manutencoes_mineroduto)):
    modelo += (
        lpSum([varInicioManutencoesMineroduto[idx_manut][horas_D14[idx_hora]] 
               for idx_hora in range(janela_planejamento*24, len(horas_D14))]) == 0,
        f"rest_evita_InicioManutencoesMineroduto_{idx_manut}",
    )

# Restrições para evitar que manutenções ocorram ao mesmo tempo
for idx_hora in range(len(horas_D14)):
    for idx_manut in range(len(duracao_manutencoes_mineroduto)):
        modelo += (
            varInicioManutencoesMineroduto[idx_manut][horas_D14[idx_hora]] +
            lpSum(varInicioManutencoesMineroduto[s][horas_D14[j]] 
                  for j in range(idx_hora-duracao_manutencoes_mineroduto[idx_manut]+1,idx_hora)
                  for s in range(len(duracao_manutencoes_mineroduto))
                  if s != idx_manut
                  )
            <= 1,            
           f"rest_separa_manutencoesMineroduto_{idx_manut}_{idx_hora}",
        )

# Fixa o horário de início da manutenção do mineroduto se foi escolhido pelo usuário
for idx_manut, inicio in enumerate(inicio_manutencoes_mineroduto):
    if inicio != 'livre':
        modelo += (
            varInicioManutencoesMineroduto[idx_manut][inicio] == 1,
            f"rest_fixa_InicioManutencaoMineroduto_{idx_manut}",
        )


# Restrição para zerar o bombeado se o mineroduto está em manutenção
for produto in produtos_conc:
    for idx_hora in range(len(horas_D14)):
        modelo += (
            varBombeado[produto][horas_D14[idx_hora]] <= BIG_M*(1 - 
                                        lpSum(varInicioManutencoesMineroduto[idx_manut][horas_D14[j]] 
                                        for idx_manut in range(len(duracao_manutencoes_mineroduto))
                                        for j in range(idx_hora - duracao_manutencoes_mineroduto[idx_manut] + 1, idx_hora))),
            f"rest_manutencao_mineroduto_{produto}_{horas_D14[idx_hora]}",
)
'''
'''
# Restrições para fixar as janelas de bombeamento

# param H:= 24;    # horas
# param d := 14;   # dias
# param dmax := 6; # janela_max_bombeamento_polpa
# param M := 100;  # infinito

# var TB, integer, >=0; # janela_fixa_bombeamento_polpa ou livre
# var Xac{t in 1..H}, integer, >=0; # Bombeamento acumulado
# var X{t in 1..H}, binary; # Bombeamento (já temos) 
# var Xf{t in 1..H}, integer, >=0; # Bombeamento tamanho (último bombeamento)

# Contabiliza o bombeamento acumulado de polpa - Xac
varBombeamentoPolpaAcumulado = LpVariable.dicts("Bombeamento Polpa Acumulado", (horas_D14), 0, len(horas_D14), LpInteger)

# Indica o bombeamento final de polpa
varBombeamentoPolpaFinal = LpVariable.dicts("Bombeamento Polpa Final", (horas_D14), 0, len(horas_D14), LpInteger)

# Restrições de SEQUENCIAMENTO FÁBRICA - CLIENTE para Bombeamento de Polpa

def bombeamento_acumulado_polpa_hora_anterior(idx_hora):
    if idx_hora == 0:
        # subject to Producao2f{t in 1..H}: #maximo de 1s
        #    Xac[1] = 0;
        return parametros_calculados['Bombeamento Acumulado Polpa final semana anterior']
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

# # subject to Producao1b{t in 2..H}: #maximo de 1s
# #    Xac[t] >= Xac[t-1] + 1 - (1- X[t])*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] >=
            bombeamento_acumulado_polpa_hora_anterior(idx_hora) + 1 - 
            (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M,
        f"seq_bomb_1b_{horas_D14[idx_hora]}",
    )

# # subject to Producao1c{t in 2..H}: #maximo de 1s
# #    Xac[t] <= X[t]*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <= lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)*BIG_M,
        f"seq_bomb_1c_{horas_D14[idx_hora]}",
    )

# # subject to Producao2a{t in 2..H}: #maximo de 1s
# #    Xf[t] <= Xac[t-1] + (1 - X[t-1] + X[t])*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= 
            bombeamento_acumulado_polpa_hora_anterior(idx_hora) + 
            (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)
               + lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M,
        f"seq_bomb_2a_{horas_D14[idx_hora]}",
    )

# # subject to Producao2b{t in 2..H}: #maximo de 1s
# #    Xf[t] >= Xac[t-1] - (1 - X[t-1] + X[t])*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoPolpaFinal[horas_D14[idx_hora]] >= 
            bombeamento_acumulado_polpa_hora_anterior(idx_hora) -
            (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc) 
               + lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M,
        f"seq_bomb_2b_{horas_D14[idx_hora]}",
    )

# # subject to Producao2c{t in 2..H}: #maximo de 1s
# #    Xf[t] <= X[t-1]*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)*BIG_M,
        f"seq_bomb_2c_{horas_D14[idx_hora]}",
    )

# # subject to Producao2d{t in 2..H}: #maximo de 1s
# #    Xf[t] <= (1-X[t])*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= 
            (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M,
        f"seq_bomb_2d_{horas_D14[idx_hora]}",
    )

# # subject to Producao2e{t in 1..H}: #maximo de 1s
# #    Xf[t] <= dmax;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= janela_max_bombeamento_polpa,
        f"seq_bomb_2e_{horas_D14[idx_hora]}",
    )

# # subject to Producao2ee{t in 1..H}: #maximo de 1s
# #    Xac[t] <= dmax;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoPolpaAcumulado[horas_D14[idx_hora]] <= janela_max_bombeamento_polpa,
        f"seq_bomb_2ee_{horas_D14[idx_hora]}",
    )

# # subject to Producao2i{t in 1..H}: #maximo de 1s 
# #    X[1] = 0;
# # Já tratado nas restrições rest_define_Bombeamento_inicial_

# se a janela de bombeamento é fixada pelo modelo ou pelo usuário
if fixar_janela_bombeamento in ['fixado_pelo_modelo','fixado_pelo_usuario']:
    janela_fixa = janela_fixa_bombeamento_polpa
    if fixar_janela_bombeamento == 'fixado_pelo_modelo':
        varJanelaFixaBombeamento = LpVariable("Janela Bombeamento Fixa", janela_min_bombeamento_polpa, janela_max_bombeamento_polpa, LpInteger)
        janela_fixa = varJanelaFixaBombeamento

    # subject to Producao3a{t in 2..H}: #maximo de 1s
    #    Xf[t] <= TB + (1 - X[t-1] + X[t])*M;

    for idx_hora in range(len(horas_D14)):
        modelo += (
            varBombeamentoPolpaFinal[horas_D14[idx_hora]] <= 
                janela_fixa + (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc) 
                                 + lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M,
            f"seq_bomb_3a_{horas_D14[idx_hora]}",
        )

    # subject to Producao3b{t in 2..H}: #maximo de 1s
    #    Xf[t] >= TB - (1 - X[t-1] + X[t])*M;

    for idx_hora in range(len(horas_D14)):
        modelo += (
            varBombeamentoPolpaFinal[horas_D14[idx_hora]] >= 
                janela_fixa - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc) 
                                 + lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M,
            f"seq_bomb_3b_{horas_D14[idx_hora]}",
        )

# Restrições de SEQUENCIAMENTO FÁBRICA - CLIENTE para Bombeamento de Água

# Contabiliza o bombeamento acumulado de água - Xac
varBombeamentoAguaAcumulado = LpVariable.dicts("Bombeamento Agua Acumulado", (horas_D14), 0, len(horas_D14), LpInteger)

# Indica o bombeamento final de água
varBombeamentoAguaFinal = LpVariable.dicts("Bombeamento Agua Final", (horas_D14), 0, len(horas_D14), LpInteger)

def bombeamento_acumulado_agua_hora_anterior(idx_hora):
    if idx_hora == 0:
        # subject to Producao2f{t in 1..H}: #maximo de 1s
        #    Xac[1] = 0;
        return parametros_calculados['Bombeamento Acumulado Agua final semana anterior']
    else:
        return varBombeamentoAguaAcumulado[horas_D14[idx_hora-1]]

# subject to Producao1a{t in 2..H}: #maximo de 1s
#    Xac[t] <= Xac[t-1] + 1 + (1- X[t])*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <= 
            bombeamento_acumulado_agua_hora_anterior(idx_hora) + 1 + 
            (1 - (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M,
        f"seq_bomb_agua_1a_{horas_D14[idx_hora]}",
    )

# subject to Producao1b{t in 2..H}: #maximo de 1s
#    Xac[t] >= Xac[t-1] + 1 - (1- X[t])*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoAguaAcumulado[horas_D14[idx_hora]] >=
            bombeamento_acumulado_agua_hora_anterior(idx_hora) + 1 - 
            (1 - (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M,
        f"seq_bomb_agua_1b_{horas_D14[idx_hora]}",
    )

# subject to Producao1c{t in 2..H}: #maximo de 1s
#    Xac[t] <= X[t]*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <= 
            (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc))*BIG_M,
        f"seq_bomb_agua_1c_{horas_D14[idx_hora]}",
    )

# subject to Producao2a{t in 2..H}: #maximo de 1s
#    Xf[t] <= Xac[t-1] + (1 - X[t-1] + X[t])*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoAguaFinal[horas_D14[idx_hora]] <= 
            bombeamento_acumulado_agua_hora_anterior(idx_hora) + 
            (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
               + (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M,
        f"seq_bomb_agua_2a_{horas_D14[idx_hora]}",
    )

# subject to Producao2b{t in 2..H}: #maximo de 1s
#    Xf[t] >= Xac[t-1] - (1 - X[t-1] + X[t])*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoAguaFinal[horas_D14[idx_hora]] >= 
            bombeamento_acumulado_agua_hora_anterior(idx_hora) -
            (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
               + (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M,
        f"seq_bomb_agua_2b_{horas_D14[idx_hora]}",
    )

# subject to Producao2c{t in 2..H}: #maximo de 1s
#    Xf[t] <= X[t-1]*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoAguaFinal[horas_D14[idx_hora]] <= 
            (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))*BIG_M,
        f"seq_bomb_agua_2c_{horas_D14[idx_hora]}",
    )

# subject to Producao2d{t in 2..H}: #maximo de 1s
#    Xf[t] <= (1-X[t])*M;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoAguaFinal[horas_D14[idx_hora]] <= 
            (1 - (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M,
        f"seq_bomb_agua_2d_{horas_D14[idx_hora]}",
    )

# subject to Producao2e{t in 1..H}: #maximo de 1s
#    Xf[t] <= dmax;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoAguaFinal[horas_D14[idx_hora]] <= janela_max_bombeamento_agua,
        f"seq_bomb_agua_2e_{horas_D14[idx_hora]}",
    )

# subject to Producao2ee{t in 1..H}: #maximo de 1s
#    Xac[t] <= dmax;

for idx_hora in range(len(horas_D14)):
    modelo += (
        varBombeamentoAguaAcumulado[horas_D14[idx_hora]] <= janela_max_bombeamento_agua,
        f"seq_bomb_agua_2ee_{horas_D14[idx_hora]}",
    )

# subject to Producao2i{t in 1..H}: #maximo de 1s 
#    X[1] = 0;
# Já tratado nas restrições rest_define_Bombeamento_inicial_


# se a janela de bombeamento é fixada pelo modelo ou pelo usuário
if fixar_janela_bombeamento_agua in ['fixado_pelo_modelo','fixado_pelo_usuario']:
    janela_fixa = janela_fixa_bombeamento_agua
    if fixar_janela_bombeamento_agua == 'fixado_pelo_modelo':
        varJanelaFixaBombeamentoAgua = LpVariable("Janela Bombeamento Fixa Agua", janela_min_bombeamento_agua, janela_max_bombeamento_agua, LpInteger)
        janela_fixa = varJanelaFixaBombeamentoAgua

    # subject to Producao3a{t in 2..H}: #maximo de 1s
    #    Xf[t] <= TB + (1 - X[t-1] + X[t])*M;

    for idx_hora in range(len(horas_D14)):
        modelo += (
            varBombeamentoAguaFinal[horas_D14[idx_hora]] <= 
                janela_fixa + (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc)) 
                                 + (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M,
            f"seq_bomb_agua_3a_{horas_D14[idx_hora]}",
        )

    # subject to Producao3b{t in 2..H}: #maximo de 1s
    #    Xf[t] >= TB - (1 - X[t-1] + X[t])*M;

    for idx_hora in range(len(horas_D14)):
        modelo += (
            varBombeamentoAguaFinal[horas_D14[idx_hora]] >= 
                janela_fixa - (1 - (1 - lpSum(bombeamento_hora_anterior(produto, idx_hora) for produto in produtos_conc))
                                 + (1 - lpSum(varBombeamentoPolpa[produto][horas_D14[idx_hora]] for produto in produtos_conc)))*BIG_M,
            f"seq_bomb_agua_3b_{horas_D14[idx_hora]}",
        )

#----------------------------------- TERMINA AQUI O MINERODUTO E COMEÇA A PARTE DOIS DO MODELO

# Indica chegada de polpa em Ubu, por produto, por hora
varPolpaUbu = LpVariable.dicts("Polpa Ubu (65Hs)", (produtos_conc, horas_D14), 0, None, LpContinuous)

# Define a chegada de polpa em Ubu
for produto in produtos_conc:
    for i in range(3*24,len(horas_Dm3_D14)):
        modelo += (
            varPolpaUbu[produto][horas_Dm3_D14[i]] 
                == varBombeado[produto][horas_Dm3_D14[i-tempo_mineroduto]] + 
                   parametros_mineroduto_ubu['Polpa Ubu (65Hs) - AJUSTE'][horas_Dm3_D14[i]],
            f"rest_define_PolpaUbu_{produto}_{horas_Dm3_D14[i]}",
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
                    varProducaoUbu[produto_c][produto_u][hora] == varProducaoSemIncorporacao[produto_u][hora]*(1+parametros_ubu['Conv.'][extrair_dia(hora)]/100),
                    f"rest_define_ProducaoUbu_{produto_c}_{produto_u}_{hora}",
                )
            else:
                modelo += (
                    varProducaoUbu[produto_c][produto_u][hora] == 0,
                    f"rest_zera_ProducaoUbu_{produto_c}_{produto_u}_{hora}",
                )
'''
'''
# Indica a hora de início das manutenções da usina
varInicioManutencoesUsina = LpVariable.dicts("Início Manutenção Usina", (range(len(duracao_manutencoes_usina)), horas_Dm3_D14), 0, 1, LpInteger)

# Restrição para garantir que a manutenção do usina se inicia uma única vez
for idx_manut in range(len(duracao_manutencoes_usina)):
    modelo += (
        lpSum([varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]] 
               for idx_hora in range(0, janela_planejamento*24)]) == 1,
        f"rest_define_InicioManutencoesUsina_{idx_manut}",
    )

# Restrição que impede que as manutenções ocorram na segunda semana
for idx_manut in range(len(duracao_manutencoes_usina)):
    modelo += (
        lpSum([varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]] 
               for idx_hora in range(janela_planejamento*24, len(horas_D14))]) == 0,
        f"rest_evita_InicioManutencoesUsina_{idx_manut}",
    )

# Restrições para evitar que manutenções ocorram ao mesmo tempo
for idx_hora in range(len(horas_D14)):
    for idx_manut in range(len(duracao_manutencoes_usina)):
        modelo += (
            varInicioManutencoesUsina[idx_manut][horas_D14[idx_hora]] +
            lpSum(varInicioManutencoesUsina[s][horas_D14[j]] 
                  for j in range(idx_hora-duracao_manutencoes_usina[idx_manut]+1,idx_hora)
                  for s in range(len(duracao_manutencoes_usina))
                  if s != idx_manut
                  )
            <= 1,            
           f"rest_separa_manutencoesUsina_{idx_manut}_{idx_hora}",
        )

# Fixa o horário de início da manutenção do usina se foi escolhido pelo usuário
for idx_manut, inicio in enumerate(inicio_manutencoes_usina):
    if inicio != 'livre':
        modelo += (
            varInicioManutencoesUsina[idx_manut][inicio] == 1,
            f"rest_fixa_InicioManutencaoUsina_{idx_manut}",
        )

# Restrição tratar manutenção, lower bound e valor fixo de produção sem incorporação
for produto in produtos_usina:   
    for idx_hora in range(len(horas_D14)):
        # se está em manutenção, zera a taxa de alimentação
        for idx_manut in range(len(duracao_manutencoes_usina)):
            modelo += (
                varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] <= BIG_M*(1 - 
                                        lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]] 
                                        for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
                f"rest_manutencao_usina_{idx_manut}_{horas_D14[idx_hora]}",
        )

    # Define lower bound
        modelo += (
            varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] >= min_producao_sem_incorporacao
                                                - BIG_M*(lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]] 
                                                            for idx_manut in range(len(duracao_manutencoes_usina))
                                                            for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
            f"rest_LB_prod_sem_incorp1_{produto}_{horas_D14[idx_hora]}",
        )
        modelo += (
            varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] <= BIG_M*(1 - lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
                                                            for idx_manut in range(len(duracao_manutencoes_usina)) 
                                                            for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
            f"rest_LB_prod_sem_incorp2_{produto}_{horas_D14[idx_hora]}",
        )

        # se a produção sem incorporação é fixada pelo modelo ou pelo usuário
        if fixar_producao_sem_incorporacao in ['fixado_pelo_modelo','fixado_pelo_usuario']:
            taxa_fixa = producao_sem_incorporacao_fixa
            if fixar_producao_sem_incorporacao == 'fixado_pelo_modelo':
                varProducaoSemIncorporacaoFixa = LpVariable("Producao sem incorporacao Fixa", 0, max_producao_sem_incorporacao, LpContinuous)
                taxa_fixa = varProducaoSemIncorporacaoFixa
            modelo += (
                varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] >= taxa_fixa
                                                    -BIG_M*(lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
                                                            for idx_manut in range(len(duracao_manutencoes_usina))
                                                            for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
                f"rest_prod_sem_incorp_fixa1_{produto}_{horas_D14[idx_hora]}",
            )
            modelo += (
                varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] <= BIG_M*(1 - lpSum(varInicioManutencoesUsina[idx_manut][horas_D14[j]]
                                                                for idx_manut in range(len(duracao_manutencoes_usina))
                                                                for j in range(idx_hora - duracao_manutencoes_usina[idx_manut] + 1, idx_hora))),
                f"rest_prod_sem_incorp_fixa2_{produto}_{horas_D14[idx_hora]}",
            )
            modelo += (
                varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] <= taxa_fixa,
                f"rest_prod_sem_incorp_fixa3_{produto}_{horas_D14[idx_hora]}",
            )
'''
'''
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
                                                            parametros_calculados['% Sólidos - EB06'][extrair_dia(horas_D14[i])] * 
                                                            parametros_ubu['Densid.'][extrair_dia(horas_D14[i])]
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
                                                parametros_calculados['% Sólidos - EB06'][extrair_dia(horas_D14[0])] * 
                                                parametros_ubu['Densid.'][extrair_dia(horas_D14[0])]
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

# Indica, para cada navio, se é a hora que inicia o carregamento
varInicioCarregNavio = LpVariable.dicts("X Inicio Carregamento", (navios, horas_D14), 0, 1, LpInteger)

# Indica, para cada navio, em que data começa o carregamento
varDataInicioCarregNavio = LpVariable.dicts("Ct Inicio Carregamento", (navios), 0, None, LpContinuous)

# Indica o estoque de produto no pátio de Ubu, por hora
varEstoqueProdutoPatio = LpVariable.dicts("S Estoque Produto Patio", (produtos_usina, horas_D14), 0, None, LpContinuous)

for navio in navios:
    for idx_hora in range(len(horas_D14)):
        modelo += (
            (varInicioCarregNavio[navio][horas_D14[idx_hora]] + 
             lpSum(varInicioCarregNavio[navio_j][horas_D14[s]]
                    for navio_j in navios 
                        for s in range(idx_hora, min(idx_hora+math.ceil(parametros_navios['VOLUME'][navio]/parametros_navios['Taxa de Carreg.'][navio])-1, len(horas_D14)))
                            if navio_j != navio)
            ) <= capacidade_carreg_porto_por_dia,
            f"Producao1_{navio}_{horas_D14[idx_hora]}",
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
    # print(navio, extrair_hora(parametros_navios['DATA-REAL'][navio]))
    modelo += (
       lpSum([idx_hora*varInicioCarregNavio[navio][horas_D14[idx_hora]] for idx_hora in range(len(horas_D14))]) >= extrair_hora(parametros_navios['DATA-REAL'][navio]),
        f"rest_limita_DataInicioCarregNavio_{navio}",
    )

# Define o estoque de produto no pátio de Ubu da segunda hora em diante
for produto in produtos_usina:
    for idx_hora in range(1, len(horas_D14)):
        modelo += (
            varEstoqueProdutoPatio[produto][horas_D14[idx_hora]] 
                == varEstoqueProdutoPatio[produto][horas_D14[idx_hora-1]] + 
                    varProducaoSemIncorporacao[produto][horas_D14[idx_hora]] 
                     - lpSum([varInicioCarregNavio[navio][horas_D14[idx_hora_s]] *
                        parametros_navios['Taxa de Carreg.'][navio] *
                        produtos_de_cada_navio[navio][produto]
                            for navio in navios
                                for idx_hora_s in range(max(idx_hora-math.ceil(parametros_navios['VOLUME'][navio]/parametros_navios['Taxa de Carreg.'][navio])+1,1), idx_hora+1)]),
            f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[idx_hora]}",
        )
    # Define o estoque de produto no pátio de Ubu do primeiro dia
    modelo += (
        varEstoqueProdutoPatio[produto][horas_D14[0]] 
            == estoque_produto_patio_d0[produto] +
            varProducaoSemIncorporacao[produto][horas_D14[0]] 
            - lpSum([varInicioCarregNavio[navio][horas_D14[0]] * 
                    parametros_navios['Taxa de Carreg.'][navio] *
                    produtos_de_cada_navio[navio][produto]
                    for navio in navios]),
        f"rest_define_EstoqueProdutoPatio_{produto}_{horas_D14[0]}",
    )

varVolumeAtrasadoNavio = LpVariable.dicts("Volume Atrasado por navio", (navios_ate_d14), 0, None, LpContinuous)

for navio in navios_ate_d14:
    modelo += (
        varVolumeAtrasadoNavio[navio] == 
            (varDataInicioCarregNavio[navio] - extrair_hora(parametros_navios['DATA-REAL'][navio])) *
             parametros_navios['Taxa de Carreg.'][navio],
        f"rest_define_VolumeAtrasadoNavio_{navio}",
    )

# -----------------------------------------------------------------------------

print(f'[OK]\nDefinindo função objetivo...   ', end='')

for fo in cenario['geral']['funcao_objetivo']:
    if not fo in ['max_brit', 'min_atr_nav', 'max_conc', 'max_usina', 'max_est_polpa', 'max_pf', 'min_est_patio']:
        raise Exception(f"Função objetivo {fo} não implementada!")

# Definindo a função objetivo
fo = 0
if 'min_atr_nav' in cenario['geral']['funcao_objetivo']:
    fo += - (lpSum([varVolumeAtrasadoNavio[navio] for navio in navios_ate_d14]))
if 'max_conc' in cenario['geral']['funcao_objetivo']:
    fo += lpSum([varTaxaAlim[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
if 'max_usina' in cenario['geral']['funcao_objetivo']:
    fo += lpSum([varProducaoSemIncorporacao[produto_usina][hora] for produto_usina in produtos_usina for hora in horas_D14])
if 'max_est_polpa' in cenario['geral']['funcao_objetivo']:
    fo += lpSum([varEstoquePolpaUbu[produto_conc][hora] for produto_conc in produtos_conc for hora in horas_D14])
if 'min_est_patio' in cenario['geral']['funcao_objetivo']:
    fo += - (lpSum([varEstoquePatio[hora] for hora in horas_D14]))
if 'max_brit' in cenario['geral']['funcao_objetivo']:
    fo += (lpSum([varTaxaBritagem[produto_mina][hora] for produto_mina in produtos_mina for hora in horas_D14]))

modelo += (fo, "FO",)

# The problem data is written to an .lp file
# prob.writeLP("PSemanal.lp")

print(f'[OK]\nRESOLVENDO o modelo...   ', end='')

# The problem is solved using PuLP's choice of Solver
solver.solve(modelo)

# The status of the solution is printed to the screen
print(f'{LpStatus[modelo.status]}')

print(f'[OK]\nObtendo resultados...   ', end='')

'''
#varBombeado = {"PRDT_C" :{"d01_h01":1270, "d01_h02":1270, "d01_h03":1270, "d01_h04":1270, "d01_h05":1270, "d01_h06":1270, "d01_h07":1270, "d01_h08":1270, "d01_h09":1270, "d01_h10":1270, "d01_h11":1270, "d01_h12":1270, "d01_h13":1270, "d01_h14":0, "d01_h15":0, "d01_h16":0, "d01_h17":0, "d01_h18":0, "d01_h19":0, "d01_h20":1270, "d01_h21":1270, "d01_h22":1270, "d01_h23":1270, "d01_h24":1270, "d02_h01":1270, "d02_h02":1270, "d02_h03":1270, "d02_h04":1270, "d02_h05":1270, "d02_h06":1270, "d02_h07":1270, "d02_h08":1270, "d02_h09":0, "d02_h10":0, "d02_h11":0, "d02_h12":0, "d02_h13":1270, "d02_h14":1270, "d02_h15":1270, "d02_h16":1270, "d02_h17":1270, "d02_h18":1270, "d02_h19":1270, "d02_h20":1270, "d02_h21":1270, "d02_h22":1270, "d02_h23":1270, "d02_h24":1270, "d03_h01":1270, "d03_h02":0, "d03_h03":0, "d03_h04":0, "d03_h05":0, "d03_h06":0, "d03_h07":0, "d03_h08":0, "d03_h09":1270, "d03_h10":1270, "d03_h11":1270, "d03_h12":1270, "d03_h13":1270, "d03_h14":1270, "d03_h15":1270, "d03_h16":1270, "d03_h17":1270, "d03_h18":1270, "d03_h19":1270, "d03_h20":1270, "d03_h21":1270, "d03_h22":0, "d03_h23":0, "d03_h24":0, "d04_h01":0, "d04_h02":1270, "d04_h03":1270, "d04_h04":1270, "d04_h05":1270, "d04_h06":1270, "d04_h07":1270, "d04_h08":1270, "d04_h09":1270, "d04_h10":1270, "d04_h11":1270, "d04_h12":1270, "d04_h13":1270, "d04_h14":1270, "d04_h15":0, "d04_h16":0, "d04_h17":0, "d04_h18":0, "d04_h19":0, "d04_h20":0, "d04_h21":1270, "d04_h22":1270, "d04_h23":1270, "d04_h24":1270, "d05_h01":1270, "d05_h02":1270, "d05_h03":1270, "d05_h04":1270, "d05_h05":1270, "d05_h06":1270, "d05_h07":1270, "d05_h08":1270, "d05_h09":1270, "d05_h10":0, "d05_h11":0, "d05_h12":0, "d05_h13":0, "d05_h14":0, "d05_h15":0, "d05_h16":1270, "d05_h17":1270, "d05_h18":1270, "d05_h19":1270, "d05_h20":1270, "d05_h21":1270, "d05_h22":1270, "d05_h23":1270, "d05_h24":1270, "d06_h01":1270, "d06_h02":1270, "d06_h03":1270, "d06_h04":1270, "d06_h05":0, "d06_h06":0, "d06_h07":0, "d06_h08":0, "d06_h09":0, "d06_h10":0, "d06_h11":1270, "d06_h12":1270, "d06_h13":1270, "d06_h14":1270, "d06_h15":1270, "d06_h16":1270, "d06_h17":1270, "d06_h18":1270, "d06_h19":1270, "d06_h20":1270, "d06_h21":1270, "d06_h22":1270, "d06_h23":1270, "d06_h24":0, "d07_h01":0, "d07_h02":0, "d07_h03":0, "d07_h04":0, "d07_h05":0, "d07_h06":0, "d07_h07":1270, "d07_h08":1270, "d07_h09":1270, "d07_h10":1270, "d07_h11":1270, "d07_h12":1270, "d07_h13":1270, "d07_h14":1270, "d07_h15":1270, "d07_h16":1270, "d07_h17":1270, "d07_h18":1270, "d07_h19":1270, "d07_h20":0, "d07_h21":0, "d07_h22":0, "d07_h23":0, "d07_h24":0, "d08_h01":0, "d08_h02":0, "d08_h03":1270, "d08_h04":1270, "d08_h05":1270, "d08_h06":1270, "d08_h07":1270, "d08_h08":1270, "d08_h09":1270, "d08_h10":1270, "d08_h11":1270, "d08_h12":1270, "d08_h13":1270, "d08_h14":1270, "d08_h15":1270, "d08_h16":0, "d08_h17":0, "d08_h18":0, "d08_h19":0, "d08_h20":0, "d08_h21":0, "d08_h22":0, "d08_h23":1270, "d08_h24":1270, "d09_h01":1270, "d09_h02":1270, "d09_h03":1270, "d09_h04":1270, "d09_h05":1270, "d09_h06":1270, "d09_h07":1270, "d09_h08":1270, "d09_h09":1270, "d09_h10":1270, "d09_h11":1270, "d09_h12":0, "d09_h13":0, "d09_h14":0, "d09_h15":0, "d09_h16":0, "d09_h17":0, "d09_h18":1270, "d09_h19":1270, "d09_h20":1270, "d09_h21":1270, "d09_h22":1270, "d09_h23":1270, "d09_h24":1270, "d10_h01":1270, "d10_h02":1270, "d10_h03":1270, "d10_h04":1270, "d10_h05":1270, "d10_h06":1270, "d10_h07":1270, "d10_h08":0, "d10_h09":0, "d10_h10":0, "d10_h11":0, "d10_h12":0, "d10_h13":0, "d10_h14":0, "d10_h15":1270, "d10_h16":1270, "d10_h17":1270, "d10_h18":1270, "d10_h19":1270, "d10_h20":1270, "d10_h21":1270, "d10_h22":1270, "d10_h23":1270, "d10_h24":1270, "d11_h01":1270, "d11_h02":1270, "d11_h03":1270, "d11_h04":0, "d11_h05":0, "d11_h06":0, "d11_h07":0, "d11_h08":0, "d11_h09":0, "d11_h10":1270, "d11_h11":1270, "d11_h12":1270, "d11_h13":1270, "d11_h14":1270, "d11_h15":1270, "d11_h16":1270, "d11_h17":1270, "d11_h18":1270, "d11_h19":1270, "d11_h20":1270, "d11_h21":1270, "d11_h22":1270, "d11_h23":0, "d11_h24":0, "d12_h01":0, "d12_h02":0, "d12_h03":1270, "d12_h04":1270, "d12_h05":1270, "d12_h06":1270, "d12_h07":1270, "d12_h08":1270, "d12_h09":1270, "d12_h10":1270, "d12_h11":1270, "d12_h12":1270, "d12_h13":1270, "d12_h14":1270, "d12_h15":1270, "d12_h16":0, "d12_h17":0, "d12_h18":0, "d12_h19":0, "d12_h20":1270, "d12_h21":1270, "d12_h22":1270, "d12_h23":1270, "d12_h24":1270, "d13_h01":1270, "d13_h02":1270, "d13_h03":1270, "d13_h04":1270, "d13_h05":1270, "d13_h06":1270, "d13_h07":1270, "d13_h08":1270, "d13_h09":1270, "d13_h10":0, "d13_h11":0, "d13_h12":0, "d13_h13":0, "d13_h14":1270, "d13_h15":1270, "d13_h16":1270, "d13_h17":1270, "d13_h18":1270, "d13_h19":1270, "d13_h20":1270, "d13_h21":1270, "d13_h22":1270, "d13_h23":1270, "d13_h24":1270, "d14_h01":1270, "d14_h02":1270, "d14_h03":0, "d14_h04":0, "d14_h05":0, "d14_h06":0, "d14_h07":0, "d14_h08":0, "d14_h09":0, "d14_h10":1270, "d14_h11":1270, "d14_h12":1270, "d14_h13":1270, "d14_h14":1270, "d14_h15":1270, "d14_h16":1270, "d14_h17":1270, "d14_h18":1270, "d14_h19":1270, "d14_h20":1270, "d14_h21":1270, "d14_h22":1270, "d14_h23":1270, "d14_h24":0}}
modelo_1 = Model_p1()
modelo_1.modelo(cenario, solver, horas_D14, produtos_conc, horas_Dm3_D14, de_para_produtos_mina_conc, min_estoque_pulmao_concentrador, max_estoque_pulmao_concentrador, 
               numero_faixas_producao, max_taxa_alimentacao, parametros_mina, taxa_producao_britagem, produtos_britagem, produtos_mina, faixas_producao_concentrador, 
               estoque_pulmao_inicial_concentrador, parametros_calculados, fatorGeracaoLama, parametros_mineroduto_ubu, estoque_eb06_d0, dias, args)

modelo_2 = Model_p2()
modelo_2.modelo(cenario, solver, horas_D14, produtos_conc, horas_Dm3_D14, varBombeado, parametros_calculados, navios, parametros_mineroduto_ubu, 
                dias, max_producao_sem_incorporacao, args, produtos_usina, de_para_produtos_conc_usina, parametros_ubu, tempo_mineroduto, min_estoque_polpa_ubu, 
                max_estoque_polpa_ubu, max_taxa_envio_patio, max_taxa_retorno_patio_usina, min_estoque_patio_usina, max_estoque_patio_usina, estoque_polpa_ubu, 
                estoque_inicial_patio_usina, fator_limite_excesso_patio, parametros_navios, capacidade_carreg_porto_por_dia, navios_ate_d14, produtos_de_cada_navio, 
                estoque_produto_patio_d0)


# Criando um dicionário com os resultados para salvar os resultados
resultados = {'variaveis':{}}
for v in modelo.variables():
    resultados['variaveis'][v.name] = v.varValue

resultados['parametros']= {'produtos_britagem': produtos_britagem, 'dados': dados}

# Repete os resultados das variáveis de maior interesse de uma forma mais fácil de avaliar
# resultados['Taxa de Alimentação C3'] = [varTaxaAlim[produto_conc][hora].varValue for produto_conc in produtos_conc for hora in horas_D14]
# resultados['Produção sem Incorporação'] = [varProducaoSemIncorporacao[produto_usina][hora].varValue for produto_usina in produtos_usina for hora in horas_D14]
# resultados['Início Carregamento Navios'] = [varDataInicioCarregNavio[navio].varValue for navio in navios_ate_d14]
# resultados['Bombeamento de Polpa'] = [varBombeamentoPolpa[produto_conc][hora].varValue for produto_conc in produtos_conc for hora in horas_D14]
# resultados['Estoque Produto Pátio'] = [varEstoqueProdutoPatio[produto_usina][hora].varValue for produto_usina in produtos_usina for hora in horas_D14]
# resultados['Excesso Volume Pátio'] = [varVolumePatio[produto_conc][hora].varValue  for produto_conc in produtos_conc for hora in horas_D14]
# resultados['Estoque Polpa Ubu'] = [varEstoquePolpaUbu[produto_conc][hora].varValue for produto_conc in produtos_conc for hora in horas_D14]
# resultados['Estoque EB06'] = [varEstoqueEB06[produto_conc][hora].varValue for produto_conc in produtos_conc for hora in horas_D14]

# Salva também os índices
resultados['dias'] = dias
resultados['horas_D14'] = horas_D14
resultados['navios_ate_d14'] = navios_ate_d14

# Salvando informações do cenário
resultados['cenario'] = {
        'nome': cenario['geral']['nome'],
        'max_estoque_polpa_ubu': max_estoque_polpa_ubu
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
nome_arquivo_saida = gerar_nome_arquivo_saida(f"{cenario['geral']['nome']}_resultados")
print(f'[OK]\nGerando arquivo {nome_arquivo_saida}...   ', end='')
with open(f'{args.pasta_saida}/{nome_arquivo_saida}', 'w', encoding='utf8') as f:
    json.dump(resultados, f)

print('[OK]')
