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

        produtos_conc = sheet_data['produtos_conc']
        produtos_usina = sheet_data['produtos_usina']
        estoque_eb06 = {produto: {} for produto in produtos_conc}
        estoque_ubu = {produto: {} for produto in produtos_conc}
        consumo_prod_ubu = {produto: {d: 0 for d in range(0,24)} for produto in produtos_conc}
        prod_concentrador = {produto: {} for produto in produtos_conc}
        # prod_usina = {c: {u: {} for u in produtos_usina} for c in produtos_conc}

        for produto in produtos_conc:
            # Update initial stock values
            estoque_eb06[produto].update({0: sheet_data['estoque_eb06_d0'][produto]})
            estoque_ubu[produto].update({0: sheet_data['estoque_polpa_ubu'][produto]})
            
            # Iterate over days and hours
            for dia in range(1, 8):
                dia_str = f'd0{dia}' if dia < 10 else f'd{dia}'
                for v in range(1, 25):
                    hour_str = f'h0{v}' if v < 10 else f'h{v}'
                    key_eb06 = f'Estoque_EB06_{produto}_{dia_str}_{hour_str}'
                    key_ubu = f'Estoque_Polpa_Ubu_{produto}_{dia_str}_{hour_str}'
                    key_prod = f'Producao___C3___Prog_{produto}_{dia_str}_{hour_str}'

                    estoque_eb06[produto].update({(dia - 1) * 24 + v: resultados_modelo['variaveis'][key_eb06]})
                    estoque_ubu[produto].update({(dia - 1) * 24 + v: resultados_modelo['variaveis'][key_ubu]})
                    prod_concentrador[produto].update({(dia - 1) * 24 + (v - 1): resultados_modelo['variaveis'][key_prod]})

            # Update consumption values for products in the plant
            for prdt_usina in produtos_usina:
                for aux in range(0, 24):
                    hour_str = f'h0{aux + 1}' if aux < 9 else f'h{aux + 1}'
                    key_consumo = f'Producao_Ubu_{produto}_{prdt_usina}_d01_{hour_str}'
                    consumo_prod_ubu[produto][aux] += resultados_modelo['variaveis'][key_consumo]
                fo_value = 0
                if resultados_modelo['solver']['status'] == 'Infeasible':
                    fo_value = -999999
                else:
                    fo_value = resultados_modelo['solver']['valor_fo']

        return fo_value, estoque_eb06, estoque_ubu, prod_concentrador, consumo_prod_ubu