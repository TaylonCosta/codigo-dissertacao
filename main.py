
from openpyxl import load_workbook # usado para ler a planilha
from pulp import *                 # usado para resolver o problema de otimização
import argparse                    # usado para tratar os argumentos do script
from PPO import run_ppo
from ai import *
from load_data import *

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
    
    L = Learning(None, data)
    L.solve_model()

    print("\n Finished!")

if __name__ == "__main__":
    main()
