from model_p1 import Model_p1
from model_p2 import Model_p2
from load_data import *

class Learning():

    def __init__(self, varBombeamentoPolpa):
        self.varBombeamentoPolpa = varBombeamentoPolpa

    def solve_model(self):
        
        load_dt = Load_data()
        cenario, solver, data = load_dt.load()

        modelo_1 = Model_p1()
        resultados_modelo1 = modelo_1.modelo(cenario, solver, data, self.varBombeamentoPolpa)

        modelo_2 = Model_p2()
        resultados_modelo2 = modelo_2.modelo(cenario, solver, data, self.varBombeamentoPolpa)
        
        print('[OK]')

        estoque_eb06 = {}
        estoque_ubu = {}

        for v in range(1,24):
            if v<10:
                dia_esotque_eb06 = f'Estoque_EB06_PRDT_C_d01_h0'+str(v)
            else:
                dia_esotque_eb06 = f'Estoque_EB06_PRDT_C_d01_h'+str(v)

            if v<10:
                dia_estoque_ubu = f'Estoque_Polpa_Ubu_PRDT_C_d01_h0'+str(v)
            else:
                dia_estoque_ubu = f'Estoque_Polpa_Ubu_PRDT_C_d01_h'+str(v)
            
            
            estoque_eb06[v] = resultados_modelo1['variaveis'][dia_esotque_eb06]
            estoque_ubu[v] = resultados_modelo2['variaveis'][dia_estoque_ubu]

        prod_concentrador = resultados_modelo1['variaveis']['Producao___C3___Prog_PRDT_C_d01_h01']
        prod_usina = resultados_modelo2['variaveis']['Producao_Ubu_PRDT_C_PRDT_U_d01_h01']
                

        return estoque_eb06, estoque_ubu, prod_concentrador, prod_usina