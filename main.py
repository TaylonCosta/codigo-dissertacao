
from openpyxl import load_workbook # usado para ler a planilha
from pulp import *                 # usado para resolver o problema de otimização
import argparse                    # usado para tratar os argumentos do script
from PPO import run_ppo
from ai import *
from plots import plot_prod_ubu, plot_estoque_eb06, plot_prod_c3, plot_estoque_polpa_ubu

def gerar_nome_arquivo_saida(nome_base_arquivo):
    """ Gera o nome padronizado do arquivo de saída """
    if not os.path.exists(nome_base_arquivo + ".json"):
        return nome_base_arquivo + ".json"

    contador = 1
    while os.path.exists(f"{nome_base_arquivo}_{contador}.json"):
        contador += 1
    return f"{nome_base_arquivo}_{contador}.json"

def main():
    load_data = Load_data()
    data = load_data.load()
    
    bomb = {'PRDT_C1': {'d01_h01': 0, 'd01_h02': 0, 'd01_h03': 0, 'd01_h04': 0, 'd01_h05': 0, 'd01_h06': 0, 'd01_h07': 0, 'd01_h08': 0, 'd01_h09': 0, 'd01_h10': 0, 'd01_h11': 0, 'd01_h12': 0, 'd01_h13': 0, 'd01_h14': 0, 'd01_h15': 0, 'd01_h16': 0, 'd01_h17': 0, 'd01_h18': 0, 'd01_h19': 0, 'd01_h20': 0, 'd01_h21': 0, 'd01_h22': 0, 'd01_h23': 0, 'd01_h24': 0}, 'PRDT_C2': {'d01_h01': 0, 'd01_h02': 0, 'd01_h03': 0, 'd01_h04': 0, 'd01_h05': 0, 'd01_h06': 0, 'd01_h07': 0, 'd01_h08': 0, 'd01_h09': 0, 'd01_h10': 0, 'd01_h11': 0, 'd01_h12': 0, 'd01_h13': 0, 'd01_h14': 0, 'd01_h15': 0, 'd01_h16': 0, 'd01_h17': 0, 'd01_h18': 0, 'd01_h19': 0, 'd01_h20': 0, 'd01_h21': 0, 'd01_h22': 0, 'd01_h23': 0, 'd01_h24': 0}, 'PRDT_C3': {'d01_h01': 0, 'd01_h02': 0, 'd01_h03': 0, 'd01_h04': 0, 'd01_h05': 0, 'd01_h06': 0, 'd01_h07': 0, 'd01_h08': 0, 'd01_h09': 0, 'd01_h10': 0, 'd01_h11': 0, 'd01_h12': 0, 'd01_h13': 0, 'd01_h14': 0, 'd01_h15': 0, 'd01_h16': 0, 'd01_h17': 0, 'd01_h18': 0, 'd01_h19': 0, 'd01_h20': 0, 'd01_h21': 0, 'd01_h22': 0, 'd01_h23': 0, 'd01_h24': 0}}

    L = Learning(bomb, data)
    resultados = L.solve_model()

    plot_estoque_polpa_ubu(resultados)
    plot_prod_ubu(resultados)

    print(resultados['solver']['valor_fo'])

    # run_ppo()

    print("\n Finished!")

if __name__ == "__main__":
    main()