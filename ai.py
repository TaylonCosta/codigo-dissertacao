from model_p1 import Model_p1
from model_p2 import Model_p2

class Learning():

    def function(cenario, solver, horas_D14, produtos_conc, horas_Dm3_D14, de_para_produtos_mina_conc, min_estoque_pulmao_concentrador, max_estoque_pulmao_concentrador, 
               numero_faixas_producao, max_taxa_alimentacao, parametros_mina, taxa_producao_britagem, produtos_britagem, produtos_mina, faixas_producao_concentrador, 
               estoque_pulmao_inicial_concentrador, parametros_calculados, fatorGeracaoLama, parametros_mineroduto_ubu, estoque_eb06_d0, dias, args, varBombeamentoPolpa,
               max_producao_sem_incorporacao, produtos_usina, de_para_produtos_conc_usina, parametros_ubu, tempo_mineroduto, min_estoque_polpa_ubu, 
                max_estoque_polpa_ubu, max_taxa_envio_patio, max_taxa_retorno_patio_usina, min_estoque_patio_usina, max_estoque_patio_usina, estoque_polpa_ubu, 
                estoque_inicial_patio_usina, fator_limite_excesso_patio, parametros_navios, capacidade_carreg_porto_por_dia, navios_ate_d14, produtos_de_cada_navio, 
                estoque_produto_patio_d0, parametros_mineroduto_md3, horas_Dm3, navios):
        
        
        modelo_1 = Model_p1()
        resultados_modelo1 = modelo_1.modelo(cenario, solver, horas_D14, produtos_conc, horas_Dm3_D14, de_para_produtos_mina_conc, min_estoque_pulmao_concentrador, max_estoque_pulmao_concentrador, 
               numero_faixas_producao, max_taxa_alimentacao, parametros_mina, taxa_producao_britagem, produtos_britagem, produtos_mina, faixas_producao_concentrador, 
               estoque_pulmao_inicial_concentrador, parametros_calculados, fatorGeracaoLama, parametros_mineroduto_ubu, estoque_eb06_d0, dias, args, varBombeamentoPolpa)

        modelo_2 = Model_p2()
        resultados_modelo2 = modelo_2.modelo(cenario, solver, horas_D14, produtos_conc, horas_Dm3, horas_Dm3_D14, parametros_calculados, navios, parametros_mineroduto_ubu, varBombeamentoPolpa,
                dias, max_producao_sem_incorporacao, args, produtos_usina, de_para_produtos_conc_usina, parametros_ubu, tempo_mineroduto, min_estoque_polpa_ubu, 
                max_estoque_polpa_ubu, max_taxa_envio_patio, max_taxa_retorno_patio_usina, min_estoque_patio_usina, max_estoque_patio_usina, estoque_polpa_ubu, 
                estoque_inicial_patio_usina, fator_limite_excesso_patio, parametros_navios, capacidade_carreg_porto_por_dia, navios_ate_d14, produtos_de_cada_navio, 
                estoque_produto_patio_d0, parametros_mineroduto_md3)
        
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
                

        return varBombeamentoPolpa, estoque_eb06, estoque_ubu, prod_concentrador, prod_usina