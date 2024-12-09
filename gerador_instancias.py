import random
import yaml

def generate_random_data():
    # Carrega o arquivo base
    with open('base.yaml', 'r') as file:
        data = yaml.safe_load(file)

    # Atualiza as variáveis especificadas com valores aleatórios
    estoque_conc = 100000
    for i in range (0, 2):
        rand_conc = random.randint(0, estoque_conc)
        if estoque_conc < 0:
            data["concentrador"]["estoque_pulmao_inicial_concentrador"][i] = [f"PRDT{i+1}", 0]
        else:
            data["concentrador"]["estoque_pulmao_inicial_concentrador"][i] = [f"PRDT{i+1}", rand_conc]
        estoque_conc -= rand_conc

    estoque_patio_usina = 300000
    for i in range (0, 3):
        rand_patio = random.randint(0, estoque_patio_usina)
        if estoque_patio_usina < 0:
            data["usina"]["estoque_inicial_patio_usina"][i] = [f"PRDT_C{i+1}", 0]
        else:
            data["usina"]["estoque_inicial_patio_usina"][i] = [f"PRDT_C{i+1}", rand_patio]
        estoque_patio_usina -= rand_patio


    estoque_polpa_ubu = 40000
    for i in range (0, 3):
        rand_polpa = random.randint(0, estoque_polpa_ubu)
        if estoque_polpa_ubu < 0:
            data["usina"]["estoque_inicial_polpa_ubu"][i] = [f"PRDT_C{i+1}", 0]
        else:
            data["usina"]["estoque_inicial_polpa_ubu"][i] = [f"PRDT_C{i+1}", rand_polpa]
        estoque_polpa_ubu -= rand_polpa


    estoque_eb6 = 10250
    for i in range (0, 3):
        rand_eb6 = random.randint(0, estoque_eb6)
        if estoque_eb6 < 0:
            data["mineroduto"]["estoque_inicial_eb06"][i] = [f"PRDT_C{i+1}", 0]
        else:
            data["mineroduto"]["estoque_inicial_eb06"][i] = [f"PRDT_C{i+1}", rand_eb6]
        estoque_eb6 -= rand_eb6

    estoque_porto = 1500000
    for i in range (0, 4):
        rand_porto = random.randint(0, estoque_porto)
        if estoque_porto < 0:
            data["porto"]["estoque_produto_patio"][i] = [f"PRDT_U{i+1}", 0]
        else:
            data["porto"]["estoque_produto_patio"][i] = [f"PRDT_U{i+1}", rand_porto]
        estoque_porto -= rand_porto

    num_navios = random.randint(1, 5)
    navios = [f"NAVIO-{i+1}" for i in range(num_navios)]
    data["porto"]["navios"] = navios
    data["porto"]["navios_horizonte"] = navios

    # Gera dados aleatórios para os navios
    data["porto"]["taxa_carreg_navios"] = {navio: random.randint(4000, 5000) for navio in navios}
    data["porto"]["carga_navios"] = {navio: random.randint(5000, 80000) for navio in navios}
    data["porto"]["data_chegada_navio"] = {navio: random.randint(1, 160) for navio in navios}
    data["porto"]["produtos_de_cada_navio"] = [[navio, random.choice(["PRDT_U1", "PRDT_U2", "PRDT_U3", "PRDT_U4"])] for navio in navios]
    

    total_estoque = 100000
    produtos = ["PRDT_C1", "PRDT_C2", "PRDT_C3", "PRDT_U1", "PRDT_U2", "PRDT_U3", "PRDT_U4"]
    valores = [random.randint(0, total_estoque) for _ in produtos]
    soma_valores = sum(valores)
    if soma_valores > total_estoque:
        valores = [int(v * total_estoque / soma_valores) for v in valores]

    data["porto"]["prod_para_estoque"] = {produto: valor for produto, valor in zip(produtos, valores)}

    return data


for i in range(0, 100):
    # Gerar os dados
    random_data = generate_random_data()

    # Salvar no arquivo YAML
    output_file = f"{i}.yaml"
    with open(output_file, "w") as file:
        yaml.dump(random_data, file, default_flow_style=False, allow_unicode=True)

    print(f"Arquivo gerado: {i}")
