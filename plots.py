import matplotlib.pyplot as plt
import numpy as np


def plot_britagem(resultados):
    britagem_prdt1_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Taxa_Britagem_PRDT1_")]
    britagem_prdt2_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Taxa_Britagem_PRDT2_")]

    hours = range(0, 168)

    plt.plot(hours, britagem_prdt1_values, label='Taxa_Britagem_PRDT1_')
    plt.plot(hours, britagem_prdt2_values, label='Taxa_Britagem_PRDT2_')

    plt.xlabel('Hour')
    plt.ylabel('Value')
    plt.legend()
    plt.show()

def plot_estoque_eb06(resultados):
    bombeado_prdt_c1_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Estoque_EB06_PRDT_C1")]
    bombeado_prdt_c2_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Estoque_EB06_PRDT_C2")]
    bombeado_prdt_c3_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Estoque_EB06_PRDT_C3")]

    hours = range(0, 168)

    plt.plot(hours, bombeado_prdt_c1_values, label='Estoque_EB06_PRDT_C1')
    plt.plot(hours, bombeado_prdt_c2_values, label='Estoque_EB06_PRDT_C2')
    plt.plot(hours, bombeado_prdt_c3_values, label='Estoque_EB06_PRDT_C3')

    plt.xlabel('Hour')
    plt.ylabel('Value')
    plt.legend()
    plt.show()

def plot_bombeado(resultados):
    bombeado_prdt_c1_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Bombeado_PRDT_C1")]
    bombeado_prdt_c2_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Bombeado_PRDT_C2")]
    bombeado_prdt_c3_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Bombeado_PRDT_C3")]

    hours = range(0, 168)

    plt.plot(hours, bombeado_prdt_c1_values, label='Bombeado_PRDT_C1')
    plt.plot(hours, bombeado_prdt_c2_values, label='Bombeado_PRDT_C2')
    plt.plot(hours, bombeado_prdt_c3_values, label='Bombeado_PRDT_C3')

    plt.xlabel('Hour')
    plt.ylabel('Value')
    plt.legend()
    plt.show()

def plot_estoque_polpa_ubu(resultados):
    estoque_polpa_ubu_prdt_c1_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Estoque_Polpa_Ubu_PRDT_C1")]
    estoque_polpa_ubu_prdt_c2_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Estoque_Polpa_Ubu_PRDT_C2")]
    estoque_polpa_ubu_prdt_c3_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Estoque_Polpa_Ubu_PRDT_C3")]

    hours = range(0, 168)

    plt.plot(hours, estoque_polpa_ubu_prdt_c1_values, label='Estoque_ubu_PRDT_C1')
    plt.plot(hours, estoque_polpa_ubu_prdt_c2_values, label='Estoque_ubu_PRDT_C2')
    plt.plot(hours, estoque_polpa_ubu_prdt_c3_values, label='Estoque_ubu_PRDT_C3')

    plt.xlabel('Hour')
    plt.ylabel('Value')
    plt.legend()
    plt.show()



def plot_prod_c3(resultados):
    prod_c3_prdt_c1_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao___C3___Prog_PRDT_C1")]
    prod_c3_prdt_c2_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao___C3___Prog_PRDT_C2")]
    prod_c3_prdt_c3_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao___C3___Prog_PRDT_C3")]

    hours = range(0, 168)

    plt.plot(hours, prod_c3_prdt_c1_values, label='Producao___C3___Prog_PRDT_C1')
    plt.plot(hours, prod_c3_prdt_c2_values, label='Producao___C3___Prog_PRDT_C2')
    plt.plot(hours, prod_c3_prdt_c3_values, label='Producao___C3___Prog_PRDT_C3')

    plt.xlabel('Hour')
    plt.ylabel('Value')
    plt.legend()
    plt.show()


def plot_prod_sem_incorp_ubu(resultados):
    prod_ubu_u1_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_sem_incorporacao_PRDT_U1")]
    prod_ubu_u2_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_sem_incorporacao_PRDT_U2")]
    prod_ubu_u3_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_sem_incorporacao_PRDT_U3")]
    prod_ubu_u4_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_sem_incorporacao_PRDT_U4")]


    hours = range(0, 168)

    plt.plot(hours, prod_ubu_u1_values, label='Producao_sem_incorporacao_PRDT_U1')
    plt.plot(hours, prod_ubu_u2_values, label='Producao_sem_incorporacao_PRDT_U2')
    plt.plot(hours, prod_ubu_u3_values, label='Producao_sem_incorporacao_PRDT_U3')
    plt.plot(hours, prod_ubu_u4_values, label='Producao_sem_incorporacao_PRDT_U4')

    plt.xlabel('Hour')
    plt.ylabel('Value')
    plt.legend()
    plt.show()


def plot_prod_ubu(resultados):
    prod_ubu_c1_u1 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C1_PRDT_U1")]
    prod_ubu_c2_u1 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C2_PRDT_U1")]
    prod_ubu_c3_u1 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C3_PRDT_U1")]

    prod_ubu_c1_u2 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C1_PRDT_U2")]
    prod_ubu_c2_u2 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C2_PRDT_U2")]
    prod_ubu_c3_u2 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C3_PRDT_U2")]

    prod_ubu_c1_u3 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C1_PRDT_U3")]
    prod_ubu_c2_u3 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C2_PRDT_U3")]
    prod_ubu_c3_u3 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C3_PRDT_U3")]

    prod_ubu_c1_u4 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C1_PRDT_U4")]
    prod_ubu_c2_u4 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C2_PRDT_U4")]
    prod_ubu_c3_u4 = [value for key, value in resultados["variaveis"].items() if key.startswith("Producao_Ubu_PRDT_C3_PRDT_U4")]

    hours = range(0, 168)

    fig, axs = plt.subplots(4, 1, figsize=(10, 8))

    # Plot for group 1
    axs[0].plot(hours, prod_ubu_c1_u1, label='prod_c1_u1')
    axs[0].plot(hours, prod_ubu_c2_u1, label='prod_c2_u1')
    axs[0].plot(hours, prod_ubu_c3_u1, label='prod_c3_u1')
    axs[0].set_title('produto 1')
    axs[0].legend()

    # Plot for group 2
    axs[1].plot(hours, prod_ubu_c1_u2, label='prod_c1_u2')
    axs[1].plot(hours, prod_ubu_c2_u2, label='prod_c2_u2')
    axs[1].plot(hours, prod_ubu_c3_u2, label='prod_c3_u2')
    axs[1].set_title('produto 2')
    axs[1].legend()

    # Plot for group 3
    axs[2].plot(hours, prod_ubu_c1_u3, label='prod_c1_u3')
    axs[2].plot(hours, prod_ubu_c2_u3, label='prod_c2_u3')
    axs[2].plot(hours, prod_ubu_c3_u3, label='prod_c3_u3')
    axs[2].set_title('produto 3')

    axs[3].plot(hours, prod_ubu_c1_u4, label='prod_c1_u4')
    axs[3].plot(hours, prod_ubu_c2_u4, label='prod_c2_u4')
    axs[3].plot(hours, prod_ubu_c3_u4, label='prod_c3_u4')
    axs[3].set_title('produto 4')
    axs[3].legend()

    # Adjust layout
    plt.tight_layout()

    plt.show()

def plot_produto_patio(resultados):
    estoque_patio_u1_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Estoque_Produto_Patio_PRDT_U1")]
    estoque_patio_u2_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Estoque_Produto_Patio_PRDT_U2")]
    estoque_patio_u3_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Estoque_Produto_Patio_PRDT_U3")]
    estoque_patio_u4_values = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Estoque_Produto_Patio_PRDT_U4")]

    hours = range(0, 168)

    plt.plot(hours, estoque_patio_u1_values, label='Estoque_Patio_PRDT_U1')
    plt.plot(hours, estoque_patio_u2_values, label='Estoque_Patio_PRDT_U2')
    plt.plot(hours, estoque_patio_u3_values, label='Estoque_Patio_PRDT_U3')
    plt.plot(hours, estoque_patio_u4_values, label='Estoque_Patio_PRDT_U4')


    plt.xlabel('Hour')
    plt.ylabel('Value')
    plt.legend()
    plt.show()



def format_carreg_array(arr):
    indices_of_ones = np.where(arr == 1)[0]

    if len(indices_of_ones) >= 2:
        start, end = indices_of_ones[0], indices_of_ones[1]
        arr[start:end+1] = 1
    
    return arr

def plot_carreg_navio(resultados):
    # Extract start and end values for each ship
    start_values_ship1 = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Inicio_Carregamento_NAVIO_1")]
    end_values_ship1 = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Fim_Carregamento_NAVIO_1")]

    start_values_ship2 = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Inicio_Carregamento_NAVIO_2")]
    end_values_ship2 = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Fim_Carregamento_NAVIO_2")]
    
    # start_values_ship3 = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Inicio_Carregamento_NUIRON_L4_")]
    # end_values_ship3 = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Fim_Carregamento_NUIRON_L4_")]
    
    # start_values_ship4 = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Inicio_Carregamento_NAVIO_1_")]
    # end_values_ship4 = [value for key, value in resultados["variaveis"].items() if key.startswith("Porto_Fim_Carregamento_NAVIO_1_")]


    # Get the labels (time periods) and convert them to indices for plotting
    labels = resultados["horas_D14"]
    time_indices = np.arange(len(labels))  # Create numeric indices for each time period
    
    loading_duration_ship1 = np.array(end_values_ship1) + np.array(start_values_ship1)
    loading_duration_ship2 = np.array(end_values_ship2) + np.array(start_values_ship2)
    # loading_duration_ship3 = np.array(end_values_ship3) + np.array(start_values_ship3)
    # loading_duration_ship4 = np.array(end_values_ship4) + np.array(start_values_ship4)

    print()

    loading_duration_arr_ship1 = format_carreg_array(loading_duration_ship1)
    loading_duration_arr_ship2 = format_carreg_array(loading_duration_ship2)
    # loading_duration_arr_ship3 = format_carreg_array(loading_duration_ship3)
    # loading_duration_arr_ship4 = format_carreg_array(loading_duration_ship4)
    
    # Create a single plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot each ship's loading duration on the same bar chart
    bar_width = 1  # Reduced bar width to fit an extra bar
    x = np.arange(len(labels))

    # Plot each ship with an offset for each bar
    ax.bar(x + 0.5 * bar_width, loading_duration_arr_ship1, color='blue', width=bar_width, label='NAVIO-1')
    ax.bar(x - 0.5 * bar_width, loading_duration_arr_ship2, color='green', width=bar_width, label='NAVIO-2')
    # ax.bar(x - 0.5 * bar_width, loading_duration_arr_ship3, color='red', width=bar_width, label='SNUIRON_L4')
    # ax.bar(x + 0.5 * bar_width, loading_duration_arr_ship4, color='black', width=bar_width, label='Ship 4')


    # Labels and title
    ax.set_xlabel('Time Period (d01_h01 to d07_h24)', fontsize=12)
    ax.set_ylabel('Loading Duration (hours)', fontsize=12)
    ax.set_title('Loading Duration from Start to End for All Ships', fontsize=14)

    # Rotate x-axis labels and add legend
    plt.xticks(x, labels, rotation=90)
    ax.legend()

    # Adjust layout and show plot
    plt.tight_layout()
    plt.show()