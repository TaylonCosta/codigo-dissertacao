import yaml
import pandas
import argparse
from pulp import *
from openpyxl import load_workbook


class Load_data:
    def ler_cenario(self, nome_arquivo):
        "Abre o arquivo YAML com parâmetros do cenário"
        with open(nome_arquivo, 'r') as arquivo:
            cenario = yaml.safe_load(arquivo)
        return cenario


    def load(self):
        parser = argparse.ArgumentParser(description='Otimizador Plano Semanal')
        parser.add_argument('-c', '--cenario', default='cenarios/ws0.yaml', type=str, help='Caminho para o arquivo do cenário a ser experimentado')
        parser.add_argument('-s', '--solver', default='PULP_CBC_CMD', type=str, help='Nome do otimizador a ser usado')
        parser.add_argument('-o', '--pasta-saida', default='experimentos', type=str, help='Pasta onde serão salvos os arquivos de resultados')

        args = parser.parse_args()

        print(f'[OK]\nLendo arquivo {args.cenario}...   ', end='')
        # Abre o arquivo YAML com dados do cenário (parâmetros do problema)
        cenario = self.ler_cenario(args.cenario)

        # -----------------------------------------------------------------------------
        # Solver
        print(f'[OK]\nInstanciando solver {args.solver}...   ', end='')
        solver = getSolver(args.solver, timeLimit=cenario['geral']['timeLimit'], msg=False)

        #------------------------------------------------------------------------------

        print(f'[OK]\nAbrindo planilha {cenario["geral"]["planilha"]}...   ', end='')
        # Abre a planilha e força o cálculo das fórmulas
        wb = load_workbook(cenario['geral']['planilha'], data_only=True)
        wb.calculation.calcMode = "auto"

        # -----------------------------------------------------------------------------
        # Índices usados pelas variáveis e parâmetros

        print(f'[OK]\nCriando índices...   ', end='')
        dias =      [f'd{dia+1:02d}' for dia in range(1)]    # d01, d02, ...   , d14
        horas =     [f'h{hora+1:02d}' for hora in range(24)]  # h01, h02, ...   , h6
        horas_D14 = [f'{dia}_{hora}' for dia in dias for hora in horas] # d01_h01, d01_h02, ...   , d14_h6
        horas_Dm3 = [f'dm{dia+1:02d}_h{hora+1:02d}' for dia in range(-4,-1) for hora in range(len(horas))] # dm-3_h01, dm-3_h02, ...   , dm-1_h6
        horas_Dm3_D14 = horas_Dm3 + horas_D14
        produtos_conc = cenario['concentrador']['produtos_conc']
        produtos_usina = cenario['usina']['produtos_usina']

        de_para_produtos_mina_conc = {'PRDT': {'PRDT_C': 1}}
        de_para_produtos_conc_usina = {'PRDT_C': {'PRDT_U': 1}}

        # Obs.: índices dos navios são definidos ao ler os dados da aba NAVIOS

        BIG_M = 10e6 # Big M

        opcoes_restricoes = ['fixado_pelo_usuario', 'fixado_pelo_modelo', 'livre']

        print(f'[OK]\nObtendo parâmetros do cenário...   ', end='')

        janela_planejamento = cenario['geral']['janela_planejamento']

        #verificar se não vai mesmo britagem

        taxa_alimentacao_britagem = cenario['mina']['taxa_alimentacao_britagem']
        disponibilidade_britagem = cenario['mina']['disponibilidade_britagem']
        utilizacao_britagem = cenario['mina']['utilizacao_britagem']

        taxa_producao_britagem = {dias[d]: taxa_alimentacao_britagem[d] *
                                        disponibilidade_britagem[d]/100 *
                                        utilizacao_britagem[d]/100
                                for d in range(len(dias))}

        # Mina
        campanha_c3 = cenario['mina']['campanha']
        produtos_mina = set()
        for campanha in campanha_c3:
            produtos_mina.add(campanha[0])
        produtos_mina = list(produtos_mina)

        produtos_britagem = {produto: {hora: 0 for hora in horas_D14} for produto in produtos_mina}
        campanha_atual = 0
        for hora in horas_D14:
            if campanha_atual < len(campanha_c3) and hora == campanha_c3[campanha_atual][1]:
                produto_atual = campanha_c3[campanha_atual][0]
                campanha_atual += 1
            produtos_britagem[produto_atual][hora] = 1

        # Concentrador
        estoque_pulmao_inicial_concentrador = {}
        for produto, estoque in cenario['concentrador']['estoque_pulmao_inicial_concentrador']:
            estoque_pulmao_inicial_concentrador[produto] = estoque
        min_estoque_pulmao_concentrador = cenario['concentrador']['min_estoque_pulmao_concentrador']
        max_estoque_pulmao_concentrador = cenario['concentrador']['max_estoque_pulmao_concentrador']
        faixas_producao_concentrador = cenario['concentrador']['faixas_producao_concentrador']
        max_taxa_alimentacao = cenario['concentrador']['max_taxa_alimentacao']
        min_taxa_alimentacao = cenario['concentrador']['min_taxa_alimentacao']
        taxa_alimentacao_fixa = cenario['concentrador']['taxa_alimentacao_fixa']
        fixar_taxa_alimentacao = cenario['concentrador']['fixar_taxa_alimentacao']
        numero_faixas_producao = cenario['concentrador']['numero_faixas_producao']

        # Mineroduto

        estoque_eb06_d0 = {}
        for produto, estoque in cenario['mineroduto']['estoque_inicial_eb06']:
            estoque_eb06_d0[produto] = estoque

        estoque_eb07_d0 = {}
        for produto, estoque in cenario['mineroduto']['estoque_inicial_eb07']:
            estoque_eb07_d0[produto] = estoque

        estoque_ubu_inicial = {}
        for produto, estoque in cenario['usina']['estoque_inicial_polpa_ubu']:
            estoque_ubu_inicial[produto] = estoque

        bombeamento_matipo = cenario['mineroduto']['bombeamento_matipo']

        min_capacidade_eb_07 = cenario['mineroduto']['min_capacidade_eb07']
        max_capacidade_eb_07 = cenario['mineroduto']['max_capacidade_eb07']

        # Usina
        max_producao_sem_incorporacao = cenario['usina']['max_producao_sem_incorporacao']
        min_producao_sem_incorporacao = cenario['usina']['min_producao_sem_incorporacao']
        producao_sem_incorporacao_fixa = cenario['usina']['producao_sem_incorporacao_fixa']
        fixar_producao_sem_incorporacao = cenario['usina']['fixar_producao_sem_incorporacao']
        min_estoque_polpa_ubu = cenario['usina']['min_estoque_polpa_ubu']
        max_estoque_polpa_ubu = cenario['usina']['max_estoque_polpa_ubu']
        max_taxa_retorno_patio_usina = cenario['usina']['max_taxa_retorno_patio_usina']
        min_estoque_patio_usina = cenario['usina']['min_estoque_patio_usina']
        max_estoque_patio_usina = cenario['usina']['max_estoque_patio_usina']
        estoque_inicial_patio_usina = cenario['usina']['estoque_inicial_patio_usina']

        capacidade_carreg_porto_por_dia = cenario['porto']['capacidade_carreg_porto_por_dia']  # número de navios

        janela_min_bombeamento_polpa = cenario['mineroduto']['janela_min_bombeamento_polpa'] # Mínimo de 1's consecutivos no bombeamento de polpa
        janela_max_bombeamento_polpa = cenario['mineroduto']['janela_max_bombeamento_polpa']
        fixar_janela_bombeamento = cenario['mineroduto']['fixar_janela_bombeamento']
        janela_fixa_bombeamento_polpa = cenario['mineroduto']['janela_fixa_bombeamento_polpa']
        bombeamento_restante_janela_anterior_polpa = cenario['mineroduto']['bombeamento_restante_janela_anterior_polpa']
        bombeamento_restante_janela_anterior_agua = cenario['mineroduto']['bombeamento_restante_janela_anterior_agua']

        janela_min_bombeamento_agua = cenario['mineroduto']['janela_min_bombeamento_agua'] # Mínimo de 1's consecutivos no bombeamento de agua
        janela_max_bombeamento_agua = cenario['mineroduto']['janela_max_bombeamento_agua']
        fixar_janela_bombeamento_agua = cenario['mineroduto']['fixar_janela_bombeamento_agua']
        janela_fixa_bombeamento_agua = cenario['mineroduto']['janela_fixa_bombeamento_agua']
        janela_para_fixar_bombeamento_agua = cenario['mineroduto']['janela_para_fixar_bombeamento_agua']
        nro_janelas_livres_agua = cenario['mineroduto']['nro_janelas_livres_agua']
        janela_livre_min_bombeamento_agua = cenario['mineroduto']['janela_livre_min_bombeamento_agua']
        janela_livre_max_bombeamento_agua = cenario['mineroduto']['janela_livre_max_bombeamento_agua']

        utilizacao_minima_mineroduto = cenario['mineroduto']['utilizacao_minima_mineroduto'] # A quantidade de água bombeada (%) não pode ser maior que 1-param
        janela_da_utilizacao_minima_mineroduto_horas = cenario['mineroduto']['janela_da_utilizacao_minima_mineroduto_horas']

        tempo_mineroduto = cenario['mineroduto']['tempo_mineroduto']

        max_taxa_envio_patio = cenario['mineroduto']['max_taxa_envio_patio']

        fator_limite_excesso_patio = cenario['mineroduto']['fator_limite_excesso_patio']

        # Paradas de manutenção
        inicio_manutencoes_britagem = cenario['mina']['inicio_manutencoes_britagem']
        duracao_manutencoes_britagem = cenario['mina']['duracao_manutencoes_britagem']

        inicio_manutencoes_concentrador = cenario['concentrador']['inicio_manutencoes_concentrador']
        duracao_manutencoes_concentrador = cenario['concentrador']['duracao_manutencoes_concentrador']

        inicio_manutencoes_mineroduto = cenario['mineroduto']['inicio_manutencoes_mineroduto']
        duracao_manutencoes_mineroduto = cenario['mineroduto']['duracao_manutencoes_mineroduto']

        inicio_manutencoes_usina = cenario['usina']['inicio_manutencoes_usina']
        duracao_manutencoes_usina = cenario['usina']['duracao_manutencoes_usina']

        def extrair_dia(hora):
            ''' Retorna o dia de uma hora no formato dXX_hYY '''
            return hora.split('_')[0]

        def extrair_hora(dia):
            return (int(dia[1:])-1)*24

        def indice_da_hora(hora):
            return (int(hora[1:3])-1)*24+int(hora[-2:])-1

        resultados_planilha = {}

        # -----------------------------------------------------------------------------

        print(f'[OK]\nObtendo parâmetros da planilha...   ', end='')

        # Lê os dados da aba MINA
        ws = wb["MINA"]

        # configuração das linhas onde se encontram os parâmetros
        conf_parametros_mina = {
            'Campanha - C3': 2,
            'PPCa - C3': 3,
            'PPCc - C3': 4,
            'Pc - C3': 5,
            'Al2O3a - C3': 6,
            'Al2O3c - C3': 7,
            'Hea - C3': 8,
            'Fe_a - C3': 9,
            'Hec - C3': 10,
            'Umidade - C3': 14,
            'Dif. de Balanço - C3': 15,
            'Sól - C3': 16,
            'DF - C3': 17,
            'UD - C3': 18,
            'Número de Tanque - EB06': 33,
            'Utilização - M3': 35,
            'Disponibilidade - M3': 36,
            'Vazão bombas - M3': 37,
            'Utilização - EB07': 41,
            'Disponibilidade - EB07': 42,
            'Vazão bombas - EB07': 43,
        }

        # colunas onde se encontram os dados da aba mina
        coluna_dia_inicial = 'E'
        coluna_dia_final = 'R'
        coluna_min = 'S'
        coluna_max = 'T'

        # guarda os parâmetros da aba mina
        parametros_mina = {}
        # guarda os limites mínimo e máximo de cada parâmetro
        min_parametros_mina = {}
        max_parametros_mina = {}

        # Lê a aba mina guardando os valores dos parâmetros e os valores mínimos e máximos
        for parametro in conf_parametros_mina:
            linha = conf_parametros_mina[parametro]
            parametros_mina[parametro] = {}
            for idx, cell in enumerate(ws[coluna_dia_inicial+str(linha)+':'+coluna_dia_final+str(linha)][0]):
                parametros_mina[parametro][dias[idx]] = cell.value
                break
            min_parametros_mina[parametro] = ws[coluna_min+str(linha)].value if ws[coluna_min+str(linha)].value is not None else 0
            max_parametros_mina[parametro] = ws[coluna_max+str(linha)].value if ws[coluna_max+str(linha)].value is not None  else BIG_M

        # Lê o parâmetro de geração de lama
        fatorGeracaoLama = ws["D26"].value

        # print('\n CONFERINDO parâmetros da MINA')
        # print(f'{parametros_mina=}')
        # print(f'{min_parametros_mina=}')
        # print(f'{max_parametros_mina=}')
        # print(f'{fatorGeracaoLama=}')

        # Validando se os valores dos parâmetros se encontram dentro dos valores mínimos e máximos

        for parametro in parametros_mina:
            if parametro != 'Campanha - C3':
                if (min(parametros_mina[parametro].values()) < min_parametros_mina[parametro]):
                    print('ATENÇÃO: O valor mínimo de ' + parametro + ' está abaixo do permitido')
                elif (max(parametros_mina[parametro].values()) > max_parametros_mina[parametro]):
                    print('ATENÇÃO: O valor máximo de ' + parametro + ' está acima do permitido')

        # -----------------------------------------------------------------------------

        # Lendo dados da aba MINERODUTO(-D3)

        ws = wb["MINERODUTO(-D3)"]

        # configuração das linhas onde se encontram os parâmetros
        conf_parametros_mineroduto_md3 = {
            'Estoque EB06 -D3': 5,
            'Bombeamento Polpa -D3': 6,
            'Bombeado -D3': 7,
        }

        def get_column_name(column_number):
            ''' Retorna o nome de uma coluna de excel correspondente ao índice passado'''
            column_name = ""
            while column_number > 0:
                column_number, remainder = divmod(column_number - 1, 26)
                column_name = chr(65 + remainder) + column_name
            return column_name

        coluna_hora_inicial_mD3 = 3
        coluna_hora_final_mD3 = coluna_hora_inicial_mD3 + len(horas)*3 - 1

        # guarda os parâmetros da aba MINERODUTO(-D3)
        parametros_mineroduto_md3 = {}

        # Lendo os parâmetros da planilha
        for parametro in conf_parametros_mineroduto_md3:
            linha = conf_parametros_mineroduto_md3[parametro]
            parametros_mineroduto_md3[parametro] = {}
            for idx, cell in enumerate(ws[f'{get_column_name(coluna_hora_inicial_mD3)}{linha}:{get_column_name(coluna_hora_final_mD3)}{linha}'][0]):
                parametros_mineroduto_md3[parametro][horas_Dm3[idx]] = cell.value

        # Sobrescreve o bombeamento polpa -D3 com a informação do cenário, porque agora é multiproduto
        parametros_mineroduto_md3['Bombeamento Polpa -D3'] = cenario['mineroduto']['bombeamento_polpa_dm3']

        # print('\n CONFERINDO parâmetros da MINERODUTO(-D3)')
        # print(f'{parametros_mineroduto_md3=}')

        # -----------------------------------------------------------------------------

        # Lendo dados da aba MINERODUTO-UBU

        ws = wb["MINERODUTO-UBU"]

        # Lendo parâmetros de uma única célula
        # estoque_eb6_d0 = ws["C5"].value
        #estoque_polpa_ubu = ['estoque_inicial_polpa_ubu']

        # configuração das linhas onde se encontram os parâmetros da aba MINERODUTO-UBU
        conf_parametros_mineroduto_ubu = {
            'Capacidade EB06': 7,
            'Polpa Ubu (65Hs) - AJUSTE': 9,
        }

        # colunas onde se encontram os dados da aba MINERODUTO-UBU
        coluna_hora_inicial_d14 = 4
        coluna_hora_final_d14 = coluna_hora_inicial_d14 + len(horas)*len(dias) - 1

        # guarda os parâmetros da aba MINERODUTO-UBU
        parametros_mineroduto_ubu = {}

        # Lendo os parâmetros da planilha
        for parametro in conf_parametros_mineroduto_ubu:
            linha = conf_parametros_mineroduto_ubu[parametro]
            parametros_mineroduto_ubu[parametro] = {}
            for idx, cell in enumerate(ws[f'{get_column_name(coluna_hora_inicial_d14)}{linha}:{get_column_name(coluna_hora_final_d14)}{linha}'][0]):
                parametros_mineroduto_ubu[parametro][horas_D14[idx]] = cell.value

        # print('\n CONFERINDO parâmetros da MINERODUTO-UBU')
        # print(f'{estoque_eb6_d0=}')
        # print(f'{estoque_polpa_ubu=}')
        #print(f'{parametros_mineroduto_ubu=}')

        # -----------------------------------------------------------------------------

        # Lendo dados da aba UBU

        ws = wb["UBU"]

        # configuração das linhas onde se encontram os parâmetros da aba UBU
        conf_parametros_mineroduto_ubu = {
            'SE': 3,
            'PPC': 4,
            '- 325#': 5,
            'Si02': 6,
            'CaO': 7,
            'pH': 8,
            'Densid.': 9,
            # 'H20': 10,
            'UD': 11,
            'DF': 12,
            'Conv.': 13,
        }

        # colunas onde se encontram os dados da aba UBU
        coluna_dia_inicial = 'D'
        coluna_dia_final = 'Q'

        # guarda os parâmetros da aba UBU
        parametros_ubu = {}

        # Lendo os parâmetros da planilha
        for parametro in conf_parametros_mineroduto_ubu:
            linha = conf_parametros_mineroduto_ubu[parametro]
            parametros_ubu[parametro] = {}
            for idx, cell in enumerate(ws[coluna_dia_inicial+str(linha)+':'+coluna_dia_final+str(linha)][0]):
                parametros_ubu[parametro][dias[idx]] = cell.value
                break

        # print('\n CONFERINDO parâmetros da aba UBU')
        # print(f'{parametros_ubu}')

        # -----------------------------------------------------------------------------

        # Lendo dados da aba PÁTIO-PORTO

        ws = wb["PÁTIO-PORTO"]

        # estoque_produto_patio_d0 = ws["D10"].value
        estoque_produto_patio_d0 = cenario['porto']['estoque_produto_patio']

        # -----------------------------------------------------------------------------

        # Lendo dados da aba NAVIOS

        ws = wb["NAVIOS"]

        # configuração das linhas onde se encontram os parâmetros da aba NAVIOS
        conf_parametros_navios = {
            'NAVIOS':'A',
            'DATA-PLANEJADA':'B',
            'DATA-REAL':'C',
            'VOLUME':'D',
        }

        # guarda os parâmetros da aba NAVIOS
        parametros_navios = {}

        # Lendo os parâmetros da planilha
        # Obs.: aqui os navios são indexados por índice, mas isso será alterado mais adiante
        #       porque o mesmo nome de navio pode aparecer mais de uma vez
        for parametro in conf_parametros_navios:
            coluna = conf_parametros_navios[parametro]
            parametros_navios[parametro] = {}
            linha = 2
            cell = ws[coluna+str(linha)]
            while cell.value is not None:
                parametros_navios[parametro][linha-2] = cell.value
                linha += 1
                cell = ws[coluna+str(linha)]

        # -----------------------------------------------------------------------------

        # Lendo dados da aba TAXA

        # Usa Pandas porque é mais fácil para fazer agrupamento e cálculo de média de taxa de carregamento
        excel_data_df = pandas.read_excel(cenario['geral']['planilha'], sheet_name='TAXA')
        taxa_carreg_por_navio = excel_data_df.groupby('CUSTOMER')['Taxa de Carreg.'].mean()

        # Guarda os índices dos navios
        navios = []

        # Esse trecho guarda as taxas de carregamento por navio e, além disso, altera os nomes dos navios
        # pois eles podem se repetir, então é necessário adicionar um sufixo para diferenciá-los
        parametros_navios['Taxa de Carreg.'] = {}
        for idx in range(len(parametros_navios['NAVIOS'])):
            navio = parametros_navios['NAVIOS'][idx] + '-L' + str(idx+2)
            navios.append(navio)
            parametros_navios['Taxa de Carreg.'][navio] = taxa_carreg_por_navio[parametros_navios['NAVIOS'][idx]]
            for parametro in conf_parametros_navios:
                parametros_navios[parametro][navio] = parametros_navios[parametro][idx]
                del parametros_navios[parametro][idx]

        # Guarda os índices dos navios com data-real até D14 (ou seja não inclui os navios D+14)
        navios_ate_d14 = []
        for parametro in ['DATA-PLANEJADA','DATA-REAL']:
            for navio in navios:
                if parametros_navios[parametro][navio] != 'D+14':
                    # Usa o mesmo formato dos índices encontrados em `dias`
                    parametros_navios[parametro][navio] = f'd{int(parametros_navios[parametro][navio][1:]):02d}'
                    if parametro == 'DATA-PLANEJADA':
                        navios_ate_d14.append(navio)
                else:
                    parametros_navios[parametro][navio] = 'd15' # Para facilitar D+14 é tratado como d15

        # -----------------------------------------------------------------------------

        # PORTO

        produtos_de_cada_navio = {navio:{produto_usina:0 for produto_usina in produtos_usina} for navio in navios}
        for navio, produto_usina in cenario['porto']['produtos_de_cada_navio']:
            produtos_de_cada_navio[navio][produto_usina] = 1

        print(f'[OK]\nDefinindo parâmetros calculados...   ', end='')

        # Guarda os parâmetros calculados
        parametros_calculados = {}


        parametros_calculados['RP (Recuperação Mássica) - C3'] = {}
        for dia in dias:
            if parametros_mina['Campanha - C3'][dia] == 'RNS':
                valor = -10.72 + (1.6346*parametros_mina['Fe_a - C3'][dia]) \
                        -(3.815*parametros_mina['Al2O3a - C3'][dia])        \
                        -(0.0984*parametros_mina['Hec - C3'][dia])
            elif parametros_mina['Campanha - C3'][dia] == 'RLS':
                valor = -13.18 + (1.614*parametros_mina['Fe_a - C3'][dia]) \
                        -(3.92*parametros_mina['Al2O3a - C3'][dia])        \
                        -(0.0187*parametros_mina['Hec - C3'][dia])
            parametros_calculados['RP (Recuperação Mássica) - C3'][dia] = valor

        parametros_calculados['Rendimento Operacional - C3'] = {}
        for dia in dias:
            parametros_calculados['Rendimento Operacional - C3'][dia] = parametros_mina['UD - C3'][dia] * parametros_mina['DF - C3'][dia]

        parametros_calculados['% Sólidos - EB06'] = {}
        parametros_calculados['Densidade Polpa - EB06'] = {}
        parametros_calculados['Relação: tms - EB06'] = {}
        parametros_calculados['Densidade Polpa - EB07'] = {}
        for dia in dias:
            parametros_calculados['% Sólidos - EB06'][dia] = parametros_mina['Sól - C3'][dia] - 0.012
            parametros_calculados['Densidade Polpa - EB06'][dia] = 1/((parametros_calculados['% Sólidos - EB06'][dia]/4.75)+(1-parametros_calculados['% Sólidos - EB06'][dia]))
            parametros_calculados['Relação: tms - EB06'][dia] = 5395*parametros_calculados['% Sólidos - EB06'][dia]*parametros_calculados['Densidade Polpa - EB06'][dia]/100
            parametros_calculados['Densidade Polpa - EB07'][dia] = parametros_calculados['Densidade Polpa - EB06'][dia]

        parametros_calculados['H20'] = {}
        for dia in dias:
            parametros_calculados['H20'][dia] = 3.296 + (0.002986*parametros_ubu['SE'][dia]) + (0.615*parametros_ubu['PPC'][dia])

        parametros_calculados['Bombeamento Acumulado Polpa final semana anterior'] = 0
        for idx_hora in range(len(horas_Dm3)-1,-1,-1):
            if parametros_mineroduto_md3['Bombeamento Polpa -D3'][idx_hora] == 'H20':
                break;
            else:
                parametros_calculados['Bombeamento Acumulado Polpa final semana anterior'] += 1;

        parametros_calculados['Bombeamento Acumulado Agua final semana anterior'] = 0
        for idx_hora in range(len(horas_Dm3)-1,-1,-1):
            if parametros_mineroduto_md3['Bombeamento Polpa -D3'][idx_hora] == 'H20':
                parametros_calculados['Bombeamento Acumulado Agua final semana anterior'] += 1;
            else:
                break;

        data = {'horas_D14': horas_D14, 'produtos_conc': produtos_conc, 'horas_Dm3_D14': horas_Dm3_D14, 'de_para_produtos_mina_conc': de_para_produtos_mina_conc,
                'min_estoque_pulmao_concentrador': min_estoque_pulmao_concentrador, 'max_estoque_pulmao_concentrador': max_estoque_pulmao_concentrador,
                'numero_faixas_producao': numero_faixas_producao, 'max_taxa_alimentacao': max_taxa_alimentacao, 'parametros_mina': parametros_mina,
                'taxa_producao_britagem': taxa_producao_britagem, 'produtos_britagem': produtos_britagem, 'produtos_mina': produtos_mina,
                'faixas_producao_concentrador': faixas_producao_concentrador, 'estoque_pulmao_inicial_concentrador': estoque_pulmao_inicial_concentrador,
                'parametros_calculados': parametros_calculados, 'fatorGeracaoLama': fatorGeracaoLama, 'parametros_mineroduto_ubu': parametros_mineroduto_ubu,
                'estoque_eb06_d0': estoque_eb06_d0, 'dias': dias, 'args': args, 'max_producao_sem_incorporacao': max_producao_sem_incorporacao,
                'produtos_usina': produtos_usina, 'de_para_produtos_conc_usina': de_para_produtos_conc_usina, 'parametros_ubu': parametros_ubu,
                'tempo_mineroduto': tempo_mineroduto, 'min_estoque_polpa_ubu': min_estoque_polpa_ubu, 'max_estoque_polpa_ubu': max_estoque_polpa_ubu,
                'max_estoque_polpa_ubu': max_estoque_polpa_ubu, 'max_taxa_envio_patio': max_taxa_envio_patio, 'max_taxa_retorno_patio_usina': max_taxa_retorno_patio_usina,
                'min_estoque_patio_usina': min_estoque_patio_usina, 'max_estoque_patio_usina': max_estoque_patio_usina, 'estoque_polpa_ubu': estoque_ubu_inicial['PRDT_C'],
                'estoque_inicial_patio_usina': estoque_inicial_patio_usina, 'fator_limite_excesso_patio': fator_limite_excesso_patio,
                'parametros_navios': parametros_navios, 'capacidade_carreg_porto_por_dia': capacidade_carreg_porto_por_dia, 'navios_ate_d14': navios_ate_d14,
                'produtos_de_cada_navio': produtos_de_cada_navio, 'estoque_produto_patio_d0': estoque_produto_patio_d0, 'parametros_mineroduto_md3': parametros_mineroduto_md3,
                'horas_Dm3': horas_Dm3, 'navios': navios
                }

        return cenario, solver, data

    def load_simplified_data_ppo(self):
        parser = argparse.ArgumentParser(description='Otimizador Plano Semanal')
        parser.add_argument('-c', '--cenario', default='cenarios/ws0.yaml', type=str, help='Caminho para o arquivo do cenário a ser experimentado')
        parser.add_argument('-s', '--solver', default='GUROBI_CMD', type=str, help='Nome do otimizador a ser usado')

        args = parser.parse_args()

        print(f'[OK]\nLendo arquivo {args.cenario}...   ', end='')
        # Abre o arquivo YAML com dados do cenário (parâmetros do problema)
        cenario = self.ler_cenario(args.cenario)

        estoque_eb06_inicial = {}
        for produto, estoque in cenario['mineroduto']['estoque_inicial_eb06']:
            estoque_eb06_inicial[produto] = estoque

        estoque_ubu_inicial = {}
        for produto, estoque in cenario['usina']['estoque_inicial_polpa_ubu']:
            estoque_ubu_inicial[produto] = estoque

        disp_conc_inicial = [600]*24
        disp_usina_inicial = [600]*24

        MaxE06 = cenario['mineroduto']['max_capacidade_eb06']
        MaxEUBU = cenario['usina']['max_estoque_polpa_ubu']
        AguaLi = cenario['mineroduto']['janela_min_bombeamento_agua']
        AguaLs = cenario['mineroduto']['janela_max_bombeamento_agua']
        PolpaLi = cenario['mineroduto']['janela_min_bombeamento_polpa']
        PolpaLs = cenario['mineroduto']['janela_max_bombeamento_polpa']

        return estoque_eb06_inicial['PRDT_C'], estoque_ubu_inicial['PRDT_C'], disp_conc_inicial, disp_usina_inicial, MaxE06, MaxEUBU, AguaLi, AguaLs, PolpaLi, PolpaLs
