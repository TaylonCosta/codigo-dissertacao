import random
import yaml

def generate_random_data():
    # Carrega o arquivo base
    with open('base.yaml', 'r') as file:
        data = yaml.safe_load(file)

    # Atualiza as variáveis especificadas com valores aleatórios
    data["concentrador"]["estoque_pulmao_inicial_concentrador"] = [
        ["PRDT1", random.randint(1000, 20000)],
        ["PRDT2", random.randint(1000, 20000)]
    ]

    data["usina"]["estoque_inicial_patio_usina"] = {
        "PRDT_C1": random.randint(1000, 10000),
        "PRDT_C2": random.randint(1000, 10000),
        "PRDT_C3": random.randint(1000, 10000),
    }

    data["usina"]["estoque_inicial_polpa_ubu"] = [
        ["PRDT_C1", random.randint(1000, 20000)],
        ["PRDT_C2", random.randint(1000, 20000)],
        ["PRDT_C3", random.randint(1000, 20000)]
    ]

    data["mineroduto"]["estoque_inicial_eb06"] = [
        ["PRDT_C1", random.randint(0, 5000)],
        ["PRDT_C2", random.randint(0, 5000)],
        ["PRDT_C3", random.randint(0, 5000)]
    ]

    data["porto"]["estoque_produto_patio"] = {
        "PRDT_U1": random.randint(10000, 50000),
        "PRDT_U2": random.randint(10000, 50000),
        "PRDT_U3": random.randint(10000, 50000),
        "PRDT_U4": random.randint(10000, 50000),
    }

    num_navios = random.randint(1, 5)
    navios = [f"NAVIO-{i+1}" for i in range(num_navios)]
    data["porto"]["navios"] = navios
    data["porto"]["navios_horizonte"] = navios

    # Gera dados aleatórios para os navios
    data["porto"]["taxa_carreg_navios"] = {navio: random.randint(4000, 5000) for navio in navios}
    data["porto"]["carga_navios"] = {navio: random.randint(5000, 80000) for navio in navios}
    data["porto"]["data_chegada_navio"] = {navio: random.randint(1, 100) for navio in navios}
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
