from model_p1 import Model_p1
from model_p2 import Model_p2
from load_data import *
import math

class Learning():

    def __init__(self, varBombeamentoPolpa, data):
        self.varBombeamentoPolpa = varBombeamentoPolpa
        self.cenario = data[0]
        self.solver = data[1]
        self.data = data[2]

    def solve_model(self):

        cenario = self.cenario
        solver = self.solver
        sheet_data = self.data

        modelo_1 = Model_p1()
        status_modelo1, resultados_modelo1 = modelo_1.modelo(cenario, solver, sheet_data, self.varBombeamentoPolpa)

        modelo_2 = Model_p2()
        status_modelo2, resultados_modelo2 = modelo_2.modelo(cenario, solver, sheet_data, self.varBombeamentoPolpa)

        estoque_eb06 = []
        estoque_ubu = []
        prod_concentrador = []
        prod_usina = []
        estoque_eb06.append(sheet_data['estoque_eb06_d0']['PRDT_C'])
        estoque_ubu.append(sheet_data['estoque_polpa_ubu'])


        for v in range(1,25):
            if v<10:
                estoque_eb06.append(resultados_modelo1['variaveis']['Estoque_EB06_PRDT_C_d01_h0'+str(v)])
                estoque_ubu.append(resultados_modelo2['variaveis']['Estoque_Polpa_Ubu_PRDT_C_d01_h0'+str(v)])
                prod_concentrador.append(resultados_modelo1['variaveis']['Producao___C3___Prog_PRDT_C_d01_h0'+str(v)])
                prod_usina.append(resultados_modelo2['variaveis']['Producao_Ubu_PRDT_C_PRDT_U_d01_h0'+str(v)])
            else:
                estoque_eb06.append(resultados_modelo1['variaveis']['Estoque_EB06_PRDT_C_d01_h'+str(v)])
                estoque_ubu.append(resultados_modelo2['variaveis']['Estoque_Polpa_Ubu_PRDT_C_d01_h'+str(v)])
                prod_concentrador.append(resultados_modelo1['variaveis']['Producao___C3___Prog_PRDT_C_d01_h'+str(v)])
                prod_usina.append(resultados_modelo2['variaveis']['Producao_Ubu_PRDT_C_PRDT_U_d01_h'+str(v)])                

        fo_value = 0

        if status_modelo1 == -1 or status_modelo2 == -1:
            fo_value = -math.inf
        else:
            fo_value = sum(prod_usina)

        return fo_value, estoque_eb06, estoque_ubu, prod_concentrador, prod_usina
