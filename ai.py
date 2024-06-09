from model_p1 import Model_p1 as Model
from model_p2 import Model_p2
from load_data import *
import math

class Learning():

    def __init__(self, varBombeamentoPolpa, horizon, data):
        self.varBombeamentoPolpa = varBombeamentoPolpa
        self.cenario = data[0]
        self.solver = data[1]
        self.data = data[2]
        self.horizon = horizon

    def solve_model(self):
    
        cenario = self.cenario
        solver = self.solver
        sheet_data = self.data

        modelo = Model()
        status_modelo, resultados_modelo = modelo.modelo(cenario, solver, sheet_data, self.varBombeamentoPolpa, self.horizon)
        return self.format_results(resultados_modelo, sheet_data)
        # return resultados_modelo
    

    def format_results(self, resultados_modelo, sheet_data):
        if self.horizon != 0:
            horas_D14 = sheet_data['horas_D14'][:self.horizon]
        else:
            horas_D14 = sheet_data['horas_D14']
        produtos_conc = sheet_data['produtos_conc']
        produtos_usina = sheet_data['produtos_usina']
        estoque_eb06 = {produto: {} for produto in produtos_conc}
        estoque_ubu = {produto: {} for produto in produtos_conc}
        prod_ubu = {produto: {aux: 0 for aux in range(24 * 7)} for produto in produtos_conc}        
        prod_concentrador = {produto: {} for produto in produtos_conc}
        # prod_usina = {c: {u: {} for u in produtos_usina} for c in produtos_conc}

        fo_value = 0
        if resultados_modelo['solver']['status'] == 'Infeasible':
            # Set all variables to 0 if the status is 'Infeasible'
            for produto in produtos_conc:
                    estoque_eb06[produto] = {0: 0}
                    estoque_ubu[produto] = {0: 0}
                    for i in range(len(sheet_data['horas_D14'])):
                        estoque_eb06[produto].update({i + 1: 0})
                        estoque_ubu[produto].update({i + 1: 0})
                        prod_concentrador[produto].update({i: 0})
                    for aux in range(len(sheet_data['horas_D14'])):
                        prod_ubu[produto][aux] = 0
            fo_value = -999999
        else:
            # Normal execution if status is not 'Infeasible'
            for produto in produtos_conc:
                # Update initial stock values
                estoque_eb06[produto].update({0: sheet_data['estoque_eb06_d0'][produto]})
                estoque_ubu[produto].update({0: sheet_data['estoque_polpa_ubu'][produto]})
                cont = 1                            
                # Iterate over days and hours
                for hora in horas_D14:
                    key_eb06 = f'Estoque_EB06_{produto}_{hora}'
                    key_ubu = f'Estoque_Polpa_Ubu_{produto}_{hora}'
                    key_prod = f'Producao___C3___Prog_{produto}_{hora}'

                    estoque_eb06[produto].update({cont: resultados_modelo['variaveis'][key_eb06]})
                    estoque_ubu[produto].update({cont: resultados_modelo['variaveis'][key_ubu]})
                    prod_concentrador[produto].update({cont: resultados_modelo['variaveis'][key_prod]})
                    cont += 1
                # Update consumption values for products in the plant
            for prdt_usina in produtos_usina:
                for hora in horas_D14:
                    cont = horas_D14.index(hora)  # Track the index for correct placement
                    for produto in produtos_conc:
                        key_consumo = f'Producao_Ubu_{produto}_{prdt_usina}_{hora}'
                        prod_ubu[produto][cont] += resultados_modelo['variaveis'][key_consumo]
            fo_value = resultados_modelo['solver']['valor_fo']

        # for produto in produtos_conc:
        #     # Update initial stock values
        #     estoque_eb06[produto].update({0: sheet_data['estoque_eb06_d0'][produto]})
        #     estoque_ubu[produto].update({0: sheet_data['estoque_polpa_ubu'][produto]})
            
        #     # Iterate over days and hours
        #     for dia in range(1, 8):
        #         dia_str = f'd0{dia}' if dia < 10 else f'd{dia}'
        #         for v in range(1, 25):
        #             hour_str = f'h0{v}' if v < 10 else f'h{v}'
        #             key_eb06 = f'Estoque_EB06_{produto}_{dia_str}_{hour_str}'
        #             key_ubu = f'Estoque_Polpa_Ubu_{produto}_{dia_str}_{hour_str}'
        #             key_prod = f'Producao___C3___Prog_{produto}_{dia_str}_{hour_str}'

        #             estoque_eb06[produto].update({(dia - 1) * 24 + v: resultados_modelo['variaveis'][key_eb06]})
        #             estoque_ubu[produto].update({(dia - 1) * 24 + v: resultados_modelo['variaveis'][key_ubu]})
        #             prod_concentrador[produto].update({(dia - 1) * 24 + (v - 1): resultados_modelo['variaveis'][key_prod]})

        #     # Update consumption values for products in the plant
        #     if not resultados_modelo['solver']['status'] == 'Infeasible':
        #         for prdt_usina in produtos_usina:
        #             for dia in range(1, 8):
        #                 dia_str = f'd0{dia}' if dia < 10 else f'd{dia}'
        #                 for aux in range(0, 24):
        #                     hour_str = f'h0{aux + 1}' if aux < 9 else f'h{aux + 1}'
        #                     key_consumo = f'Producao_Ubu_{produto}_{prdt_usina}_{dia_str}_{hour_str}'
        #                     consumo_prod_ubu[produto][(dia - 1) * 24 + aux] += resultados_modelo['variaveis'][key_consumo]
        return fo_value, estoque_eb06, estoque_ubu, prod_concentrador, prod_ubu