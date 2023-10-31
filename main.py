print(f'Inicializando otimizador...   ', end='')

# from ai import Learning
from openpyxl import load_workbook # usado para ler a planilha
from pulp import *                 # usado para resolver o problema de otimização
import argparse                    # usado para tratar os argumentos do script
# from PPO import *
from ai import Learning

def gerar_nome_arquivo_saida(nome_base_arquivo):
    """ Gera o nome padronizado do arquivo de saída """
    if not os.path.exists(nome_base_arquivo + ".json"):
        return nome_base_arquivo + ".json"
    
    contador = 1
    while os.path.exists(f"{nome_base_arquivo}_{contador}.json"):
        contador += 1
    return f"{nome_base_arquivo}_{contador}.json"

parser = argparse.ArgumentParser(description='Otimizador Plano Semanal')
parser.add_argument('-o', '--pasta-saida', default='experimentos', type=str, help='Pasta onde serão salvos os arquivos de resultados')
args = parser.parse_args()


estoque_polpa_ubu = 3000
# print(parametros_mineroduto_md3['Bombeamento Polpa -D3'])
# varBombeamentoPolpa = cenario['mineroduto']['bombeamento_polpa']
varBombeamentoPolpa = 0
L = Learning(varBombeamentoPolpa)
L.solve_model()


# varBombeamentoPolpa, estoque_eb06, estoque_ubu, prod_concentrador, prod_usina = Learning.function(cenario, solver, horas_D14, produtos_conc, horas_Dm3_D14, de_para_produtos_mina_conc, min_estoque_pulmao_concentrador, max_estoque_pulmao_concentrador, 
#                numero_faixas_producao, max_taxa_alimentacao, parametros_mina, taxa_producao_britagem, produtos_britagem, produtos_mina, faixas_producao_concentrador, 
#                estoque_pulmao_inicial_concentrador, parametros_calculados, fatorGeracaoLama, parametros_mineroduto_ubu, estoque_eb06_d0, dias, args, varBombeamentoPolpa,
#                max_producao_sem_incorporacao, produtos_usina, de_para_produtos_conc_usina, parametros_ubu, tempo_mineroduto, min_estoque_polpa_ubu, 
#                 max_estoque_polpa_ubu, max_taxa_envio_patio, max_taxa_retorno_patio_usina, min_estoque_patio_usina, max_estoque_patio_usina, estoque_polpa_ubu, 
#                 estoque_inicial_patio_usina, fator_limite_excesso_patio, parametros_navios, capacidade_carreg_porto_por_dia, navios_ate_d14, produtos_de_cada_navio, 
#                 estoque_produto_patio_d0, parametros_mineroduto_md3, horas_Dm3, navios)

# print(varBombeamentoPolpa, estoque_eb06, estoque_ubu, prod_concentrador, prod_usina)


#
#ter uma função como entrada o vetor resultado do mineroduto, dos tanques (eb06 e tanque concentrador), taxa de prod conc e taxa de prod usina
#retornar esses valores
#resultados da ia é a saída de mineroduto
#