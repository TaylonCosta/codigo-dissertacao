import matplotlib.pyplot as plt  

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