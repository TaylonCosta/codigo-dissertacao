
from openpyxl import load_workbook # usado para ler a planilha
from pulp import *                 # usado para resolver o problema de otimização
import argparse                    # usado para tratar os argumentos do script
from PPO import run_ppo
from ai import *

def gerar_nome_arquivo_saida(nome_base_arquivo):
    """ Gera o nome padronizado do arquivo de saída """
    if not os.path.exists(nome_base_arquivo + ".json"):
        return nome_base_arquivo + ".json"
    
    contador = 1
    while os.path.exists(f"{nome_base_arquivo}_{contador}.json"):
        contador += 1
    return f"{nome_base_arquivo}_{contador}.json"

# # bomb = {'PRDT_C': {'d01_h01': 0.0, 'd01_h02': 1.0, 'd01_h03':1.0, 'd01_h04': 1.0, 'd01_h05': 1.0, 'd01_h06': 0, 'd01_h07': 0, 'd01_h08': 0, 'd01_h09': 0, 'd01_h10': 0, 'd01_h11': 0, 'd01_h12': 0, 'd01_h13': 0, 'd01_h14': 0, 'd01_h15': 0, 'd01_h16': 0, 'd01_h17': 0, 'd01_h18': 0, 'd01_h19': 0, 'd01_h20': 0, 'd01_h21': 0, 'd01_h22': 0, 'd01_h23': 0, 'd01_h24': 0}}
# # L = Learning(bomb)
# L.solve_model()
run_ppo()



print("\n Finished!")