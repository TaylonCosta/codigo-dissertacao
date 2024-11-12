
from openpyxl import load_workbook # usado para ler a planilha
from pulp import *                 # usado para resolver o problema de otimização
import argparse                    # usado para tratar os argumentos do script
import json
from PPO import run_ppo
from ai import *
from plots import plot_prod_ubu, plot_estoque_eb06, plot_prod_c3, plot_estoque_polpa_ubu, plot_prod_sem_incorp_ubu, plot_carreg_navio, plot_britagem, plot_produto_patio

def gerar_nome_arquivo_saida(nome_base_arquivo):
    """ Gera o nome padronizado do arquivo de saída """
    if not os.path.exists(nome_base_arquivo + ".json"):
        return nome_base_arquivo + ".json"

    contador = 1
    while os.path.exists(f"{nome_base_arquivo}_{contador}.json"):
        contador += 1
    return f"{nome_base_arquivo}_{contador}.json"

def run_plots():
    with open('experimentos/ws1.json', 'r') as file:
        resultados = json.load(file)

    # plot_britagem(resultados)
    # plot_estoque_eb06(resultados)
    # plot_prod_c3(resultados)
    # plot_estoque_polpa_ubu(resultados)
    # plot_prod_ubu(resultados)
    plot_prod_sem_incorp_ubu(resultados)
    plot_produto_patio(resultados)
    plot_carreg_navio(resultados)


def run_model(args):
    load_data = Load_data()
    data = load_data.load(args)

    L = Learning(None, 168, data)
    resultados = L.solve_model()
    print(resultados['solver']['valor_fo'])

    # run_ppo()

    print("\n Finished!")


def main():
    parser = argparse.ArgumentParser(description='Otimizador Plano Semanal')
    parser.add_argument('-c', '--cenario', type=str, help='Caminho para o arquivo do cenário a ser experimentado')
    parser.add_argument('-s', '--solver', default='GUROBI', type=str, help='Nome do otimizador a ser usado')
    parser.add_argument('-o', '--pasta-saida', default='experimentos', type=str, help='Pasta onde serão salvos os arquivos de resultados')
    parser.add_argument('--relax-and-fix', action='store_true', help='Habilita a heurística Relax And Fix das variáveis do mineroduto')
    parser.add_argument('--opt-partes', action='store_true', help='Habilita a heurística de otimização por partes')
    parser.add_argument('--ppo', action='store_true', help='Resolve o mdoelo pelo ppo')
    args = parser.parse_args()
    run_model(args)
    run_plots()


if __name__ == "__main__":
    main()