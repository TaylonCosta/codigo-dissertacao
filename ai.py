from model_p1 import Model_p1 as Model
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

        modelo = Model()
        status_modelo, resultados_modelo = modelo.modelo(cenario, solver, sheet_data, self.varBombeamentoPolpa)

        # modelo_2 = Model_p2()
        # status_modelo2, resultados_modelo2 = modelo_2.modelo(cenario, solver, sheet_data, self.varBombeamentoPolpa)

        produtos_conc = sheet_data['produtos_conc']
        produtos_usina = sheet_data['produtos_usina']
        estoque_eb06 = {produto: {} for produto in produtos_conc}
        estoque_ubu = {produto: {} for produto in produtos_conc}
        consumo_prod_ubu = {produto: {d: 0 for d in range(0,24)} for produto in produtos_conc}
        prod_concentrador = {produto: {} for produto in produtos_conc}
        # prod_usina = {c: {u: {} for u in produtos_usina} for c in produtos_conc}

        for produto in produtos_conc:
            estoque_eb06[produto].update({0: sheet_data['estoque_eb06_d0'][produto]})
            estoque_ubu[produto].update({0: sheet_data['estoque_polpa_ubu'][produto]})
            for v in range(1,25):
                if v<10:
                    estoque_eb06[produto].update({v: resultados_modelo['variaveis']['Estoque_EB06_'+str(produto)+'_d01_h0'+str(v)]})
                    estoque_ubu[produto].update({v: resultados_modelo['variaveis']['Estoque_Polpa_Ubu_'+str(produto)+'_d01_h0'+str(v)]})
                    prod_concentrador[produto].update({v-1: resultados_modelo['variaveis']['Producao___C3___Prog_'+str(produto)+'_d01_h0'+str(v)]})
                else:
                    estoque_eb06[produto].update({v: resultados_modelo['variaveis']['Estoque_EB06_'+str(produto)+'_d01_h'+str(v)]})
                    estoque_ubu[produto].update({v: resultados_modelo['variaveis']['Estoque_Polpa_Ubu_'+str(produto)+'_d01_h'+str(v)]})
                    prod_concentrador[produto].update({v-1: resultados_modelo['variaveis']['Producao___C3___Prog_'+str(produto)+'_d01_h'+str(v)]})

            for prdt_usina in produtos_usina:
                for aux in range(0,24):
                    if aux < 9:
                        consumo_prod_ubu[produto][aux]+=resultados_modelo['variaveis']['Producao_Ubu_'+str(produto)+'_'+str(prdt_usina)+'_d01_h0'+str(aux+1)]
                    else:
                        consumo_prod_ubu[produto][aux]+=resultados_modelo['variaveis']['Producao_Ubu_'+str(produto)+'_'+str(prdt_usina)+'_d01_h'+str(aux+1)]
        fo_value = 0
        if status_modelo == -1:
            fo_value = -999999
        else:
                fo_value = resultados_modelo['solver']['valor_fo']

        return fo_value, estoque_eb06, estoque_ubu, prod_concentrador, consumo_prod_ubu
