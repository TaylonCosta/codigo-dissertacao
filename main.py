
from openpyxl import load_workbook # usado para ler a planilha
from pulp import *                 # usado para resolver o problema de otimização
import argparse                    # usado para tratar os argumentos do script
from PPO import run_ppo
from ai import *
from plots import plot_prod_ubu, plot_estoque_eb06, plot_prod_c3, plot_estoque_polpa_ubu, plot_prod_sem_incorp_ubu

def gerar_nome_arquivo_saida(nome_base_arquivo):
    """ Gera o nome padronizado do arquivo de saída """
    if not os.path.exists(nome_base_arquivo + ".json"):
        return nome_base_arquivo + ".json"

    contador = 1
    while os.path.exists(f"{nome_base_arquivo}_{contador}.json"):
        contador += 1
    return f"{nome_base_arquivo}_{contador}.json"

def main():
    # load_data = Load_data()
    # data = load_data.load()
    
    # bomb = {'PRDT_C1': {'d01_h01': 1, 'd01_h02': 1, 'd01_h03': 1, 'd01_h04': 1, 'd01_h05': 1, 'd01_h06': 0, 'd01_h07': 0, 'd01_h08': 0, 'd01_h09': 0, 'd01_h10': 0, 'd01_h11': 0, 'd01_h12': 0, 'd01_h13': 0, 'd01_h14': 0, 'd01_h15': 0, 'd01_h16': 0, 'd01_h17': 0, 'd01_h18': 0, 'd01_h19': 0, 'd01_h20': 0, 'd01_h21': 0, 'd01_h22': 0, 'd01_h23': 0, 'd01_h24': 0,
    #                     'd02_h01': 0, 'd02_h02': 0, 'd02_h03': 0, 'd02_h04': 0, 'd02_h05': 0, 'd02_h06': 0, 'd02_h07': 0, 'd02_h08': 0, 'd02_h09': 0, 'd02_h10': 0, 'd02_h11': 0, 'd02_h12': 0, 'd02_h13': 0, 'd02_h14': 0, 'd02_h15': 0, 'd02_h16': 0, 'd02_h17': 0, 'd02_h18': 0, 'd02_h19': 0, 'd02_h20': 0, 'd02_h21': 0, 'd02_h22': 0, 'd02_h23': 0, 'd02_h24': 0,
    #                     'd03_h01': 0, 'd03_h02': 0, 'd03_h03': 0, 'd03_h04': 0, 'd03_h05': 0, 'd03_h06': 0, 'd03_h07': 0, 'd03_h08': 0, 'd03_h09': 0, 'd03_h10': 0, 'd03_h11': 0, 'd03_h12': 0, 'd03_h13': 0, 'd03_h14': 0, 'd03_h15': 0, 'd03_h16': 0, 'd03_h17': 0, 'd03_h18': 0, 'd03_h19': 0, 'd03_h20': 0, 'd03_h21': 0, 'd03_h22': 0, 'd03_h23': 0, 'd03_h24': 0,
    #                     'd04_h01': 0, 'd04_h02': 0, 'd04_h03': 0, 'd04_h04': 0, 'd04_h05': 0, 'd04_h06': 0, 'd04_h07': 0, 'd04_h08': 0, 'd04_h09': 0, 'd04_h10': 0, 'd04_h11': 0, 'd04_h12': 0, 'd04_h13': 0, 'd04_h14': 0, 'd04_h15': 0, 'd04_h16': 0, 'd04_h17': 0, 'd04_h18': 0, 'd04_h19': 0, 'd04_h20': 0, 'd04_h21': 0, 'd04_h22': 0, 'd04_h23': 0, 'd04_h24': 0,
    #                     'd05_h01': 0, 'd05_h02': 0, 'd05_h03': 0, 'd05_h04': 0, 'd05_h05': 0, 'd05_h06': 0, 'd05_h07': 0, 'd05_h08': 0, 'd05_h09': 0, 'd05_h10': 0, 'd05_h11': 0, 'd05_h12': 0, 'd05_h13': 0, 'd05_h14': 0, 'd05_h15': 0, 'd05_h16': 0, 'd05_h17': 0, 'd05_h18': 0, 'd05_h19': 0, 'd05_h20': 0, 'd05_h21': 0, 'd05_h22': 0, 'd05_h23': 0, 'd05_h24': 0,
    #                     'd06_h01': 0, 'd06_h02': 0, 'd06_h03': 0, 'd06_h04': 0, 'd06_h05': 0, 'd06_h06': 0, 'd06_h07': 0, 'd06_h08': 0, 'd06_h09': 0, 'd06_h10': 0, 'd06_h11': 0, 'd06_h12': 0, 'd06_h13': 0, 'd06_h14': 0, 'd06_h15': 0, 'd06_h16': 0, 'd06_h17': 0, 'd06_h18': 0, 'd06_h19': 0, 'd06_h20': 0, 'd06_h21': 0, 'd06_h22': 0, 'd06_h23': 0, 'd06_h24': 0,
    #                     'd07_h01': 0, 'd07_h02': 0, 'd07_h03': 0, 'd07_h04': 0, 'd07_h05': 0, 'd07_h06': 0, 'd07_h07': 0, 'd07_h08': 0, 'd07_h09': 0, 'd07_h10': 0, 'd07_h11': 0, 'd07_h12': 0, 'd07_h13': 0, 'd07_h14': 0, 'd07_h15': 0, 'd07_h16': 0, 'd07_h17': 0, 'd07_h18': 0, 'd07_h19': 0, 'd07_h20': 0, 'd07_h21': 0, 'd07_h22': 0, 'd07_h23': 0, 'd07_h24': 0}, 
    #         'PRDT_C2': {'d01_h01': 0, 'd01_h02': 0, 'd01_h03': 0, 'd01_h04': 0, 'd01_h05': 0, 'd01_h06': 0, 'd01_h07': 0, 'd01_h08': 0, 'd01_h09': 0, 'd01_h10': 0, 'd01_h11': 0, 'd01_h12': 0, 'd01_h13': 0, 'd01_h14': 0, 'd01_h15': 0, 'd01_h16': 0, 'd01_h17': 0, 'd01_h18': 0, 'd01_h19': 0, 'd01_h20': 0, 'd01_h21': 0, 'd01_h22': 0, 'd01_h23': 0, 'd01_h24': 0,
    #                     'd02_h01': 0, 'd02_h02': 0, 'd02_h03': 0, 'd02_h04': 0, 'd02_h05': 0, 'd02_h06': 0, 'd02_h07': 0, 'd02_h08': 0, 'd02_h09': 0, 'd02_h10': 0, 'd02_h11': 0, 'd02_h12': 0, 'd02_h13': 0, 'd02_h14': 0, 'd02_h15': 0, 'd02_h16': 0, 'd02_h17': 0, 'd02_h18': 0, 'd02_h19': 0, 'd02_h20': 0, 'd02_h21': 0, 'd02_h22': 0, 'd02_h23': 0, 'd02_h24': 0,
    #                     'd03_h01': 0, 'd03_h02': 0, 'd03_h03': 0, 'd03_h04': 0, 'd03_h05': 0, 'd03_h06': 0, 'd03_h07': 0, 'd03_h08': 0, 'd03_h09': 0, 'd03_h10': 0, 'd03_h11': 0, 'd03_h12': 0, 'd03_h13': 0, 'd03_h14': 0, 'd03_h15': 0, 'd03_h16': 0, 'd03_h17': 0, 'd03_h18': 0, 'd03_h19': 0, 'd03_h20': 0, 'd03_h21': 0, 'd03_h22': 0, 'd03_h23': 0, 'd03_h24': 0,
    #                     'd04_h01': 0, 'd04_h02': 0, 'd04_h03': 0, 'd04_h04': 0, 'd04_h05': 0, 'd04_h06': 0, 'd04_h07': 0, 'd04_h08': 0, 'd04_h09': 0, 'd04_h10': 0, 'd04_h11': 0, 'd04_h12': 0, 'd04_h13': 0, 'd04_h14': 0, 'd04_h15': 0, 'd04_h16': 0, 'd04_h17': 0, 'd04_h18': 0, 'd04_h19': 0, 'd04_h20': 0, 'd04_h21': 0, 'd04_h22': 0, 'd04_h23': 0, 'd04_h24': 0,
    #                     'd05_h01': 0, 'd05_h02': 0, 'd05_h03': 0, 'd05_h04': 0, 'd05_h05': 0, 'd05_h06': 0, 'd05_h07': 0, 'd05_h08': 0, 'd05_h09': 0, 'd05_h10': 0, 'd05_h11': 0, 'd05_h12': 0, 'd05_h13': 0, 'd05_h14': 0, 'd05_h15': 0, 'd05_h16': 0, 'd05_h17': 0, 'd05_h18': 0, 'd05_h19': 0, 'd05_h20': 0, 'd05_h21': 0, 'd05_h22': 0, 'd05_h23': 0, 'd05_h24': 0,
    #                     'd06_h01': 0, 'd06_h02': 0, 'd06_h03': 0, 'd06_h04': 0, 'd06_h05': 0, 'd06_h06': 0, 'd06_h07': 0, 'd06_h08': 0, 'd06_h09': 0, 'd06_h10': 0, 'd06_h11': 0, 'd06_h12': 0, 'd06_h13': 0, 'd06_h14': 0, 'd06_h15': 0, 'd06_h16': 0, 'd06_h17': 0, 'd06_h18': 0, 'd06_h19': 0, 'd06_h20': 0, 'd06_h21': 0, 'd06_h22': 0, 'd06_h23': 0, 'd06_h24': 0,
    #                     'd07_h01': 0, 'd07_h02': 0, 'd07_h03': 0, 'd07_h04': 0, 'd07_h05': 0, 'd07_h06': 0, 'd07_h07': 0, 'd07_h08': 0, 'd07_h09': 0, 'd07_h10': 0, 'd07_h11': 0, 'd07_h12': 0, 'd07_h13': 0, 'd07_h14': 0, 'd07_h15': 0, 'd07_h16': 0, 'd07_h17': 0, 'd07_h18': 0, 'd07_h19': 0, 'd07_h20': 0, 'd07_h21': 0, 'd07_h22': 0, 'd07_h23': 0, 'd07_h24': 0}, 
    #         'PRDT_C3': {'d01_h01': 0, 'd01_h02': 0, 'd01_h03': 0, 'd01_h04': 0, 'd01_h05': 0, 'd01_h06': 0, 'd01_h07': 0, 'd01_h08': 0, 'd01_h09': 0, 'd01_h10': 0, 'd01_h11': 0, 'd01_h12': 0, 'd01_h13': 0, 'd01_h14': 0, 'd01_h15': 0, 'd01_h16': 0, 'd01_h17': 0, 'd01_h18': 0, 'd01_h19': 0, 'd01_h20': 0, 'd01_h21': 0, 'd01_h22': 0, 'd01_h23': 0, 'd01_h24': 0,
    #                     'd02_h01': 0, 'd02_h02': 0, 'd02_h03': 0, 'd02_h04': 0, 'd02_h05': 0, 'd02_h06': 0, 'd02_h07': 0, 'd02_h08': 0, 'd02_h09': 0, 'd02_h10': 0, 'd02_h11': 0, 'd02_h12': 0, 'd02_h13': 0, 'd02_h14': 0, 'd02_h15': 0, 'd02_h16': 0, 'd02_h17': 0, 'd02_h18': 0, 'd02_h19': 0, 'd02_h20': 0, 'd02_h21': 0, 'd02_h22': 0, 'd02_h23': 0, 'd02_h24': 0,
    #                     'd03_h01': 0, 'd03_h02': 0, 'd03_h03': 0, 'd03_h04': 0, 'd03_h05': 0, 'd03_h06': 0, 'd03_h07': 0, 'd03_h08': 0, 'd03_h09': 0, 'd03_h10': 0, 'd03_h11': 0, 'd03_h12': 0, 'd03_h13': 0, 'd03_h14': 0, 'd03_h15': 0, 'd03_h16': 0, 'd03_h17': 0, 'd03_h18': 0, 'd03_h19': 0, 'd03_h20': 0, 'd03_h21': 0, 'd03_h22': 0, 'd03_h23': 0, 'd03_h24': 0,
    #                     'd04_h01': 0, 'd04_h02': 0, 'd04_h03': 0, 'd04_h04': 0, 'd04_h05': 0, 'd04_h06': 0, 'd04_h07': 0, 'd04_h08': 0, 'd04_h09': 0, 'd04_h10': 0, 'd04_h11': 0, 'd04_h12': 0, 'd04_h13': 0, 'd04_h14': 0, 'd04_h15': 0, 'd04_h16': 0, 'd04_h17': 0, 'd04_h18': 0, 'd04_h19': 0, 'd04_h20': 0, 'd04_h21': 0, 'd04_h22': 0, 'd04_h23': 0, 'd04_h24': 0,
    #                     'd05_h01': 0, 'd05_h02': 0, 'd05_h03': 0, 'd05_h04': 0, 'd05_h05': 0, 'd05_h06': 0, 'd05_h07': 0, 'd05_h08': 0, 'd05_h09': 0, 'd05_h10': 0, 'd05_h11': 0, 'd05_h12': 0, 'd05_h13': 0, 'd05_h14': 0, 'd05_h15': 0, 'd05_h16': 0, 'd05_h17': 0, 'd05_h18': 0, 'd05_h19': 0, 'd05_h20': 0, 'd05_h21': 0, 'd05_h22': 0, 'd05_h23': 0, 'd05_h24': 0,
    #                     'd06_h01': 0, 'd06_h02': 0, 'd06_h03': 0, 'd06_h04': 0, 'd06_h05': 0, 'd06_h06': 0, 'd06_h07': 0, 'd06_h08': 0, 'd06_h09': 0, 'd06_h10': 0, 'd06_h11': 0, 'd06_h12': 0, 'd06_h13': 0, 'd06_h14': 0, 'd06_h15': 0, 'd06_h16': 0, 'd06_h17': 0, 'd06_h18': 0, 'd06_h19': 0, 'd06_h20': 0, 'd06_h21': 0, 'd06_h22': 0, 'd06_h23': 0, 'd06_h24': 0,
    #                     'd07_h01': 0, 'd07_h02': 0, 'd07_h03': 0, 'd07_h04': 0, 'd07_h05': 0, 'd07_h06': 0, 'd07_h07': 0, 'd07_h08': 0, 'd07_h09': 0, 'd07_h10': 0, 'd07_h11': 0, 'd07_h12': 0, 'd07_h13': 0, 'd07_h14': 0, 'd07_h15': 0, 'd07_h16': 0, 'd07_h17': 0, 'd07_h18': 0, 'd07_h19': 0, 'd07_h20': 0, 'd07_h21': 0, 'd07_h22': 0, 'd07_h23': 0, 'd07_h24': 0}}

    # L = Learning(bomb, data)
    # resultados = L.solve_model()

    # plot_estoque_eb06(resultados)
    # plot_prod_c3(resultados)
    # plot_estoque_polpa_ubu(resultados)
    # plot_prod_ubu(resultados)
    # plot_prod_sem_incorp_ubu(resultados)

    # print(resultados['solver']['valor_fo'])

    run_ppo()

    print("\n Finished!")

if __name__ == "__main__":
    main()