import matplotlib.pyplot as plt    # usado para exibir gráficos
from matplotlib.gridspec import GridSpec
import seaborn as sns              # usado para melhor a aparência dos gráficos
import pickle                      # usado para carregar os resultados
import numpy as np
import argparse                    # usado para tratar os argumentos do script

parser = argparse.ArgumentParser(description='Analisador Resultados Otimizador')
parser.add_argument('-a', '--arquivo', default='experimentos/ws0_resultados.pkl', type=str, help='Nome do arquivo .pkl com os resultados do otimizador')
parser.add_argument('-n', '--nao-exibir', action='store_true', help='Não exibe os gráficos na tela')
parser.add_argument('-s', '--salvar', action='store_true', help='Salva os gráficos em uma figura com o mesmo nome do arquivo e extensão .png')
parser.add_argument('-c', '--comparar-resultados', default=None, type=str, help='Se informado, em vez de comparar com os dados da planilha, compara com esse segundo resultado')
parser.add_argument('-g', '--graficos-adicionais', action='store_true', help='Inclui os gráficos do estoque EB06 e Volume Pátio (Pellet Feed)')
args = parser.parse_args()

def extrair_nome_solucao(nome_arquivo):
    # Extrai o nome da solução a partir do nome do arquivo
    # Exemplo: 'experimentos/cenario1_resultados.pkl' -> 'cenario1'
    return nome_arquivo.split('/')[-1].split('\\')[-1].split('_resultados')[0]

# Carregando os dados salvos no arquivo binário usando pickle
print(f'Carregando arquivo {args.arquivo}...   ', end='')
with open(f'{args.arquivo}', 'rb') as f:
    resultados = pickle.load(f)
solucao = extrair_nome_solucao(args.arquivo)

variaveis = set()
for variavel in resultados['variaveis']:
    if not '_dm_' in variavel:
        variaveis.add(variavel[:-7])

variaveis = list(variaveis)
variaveis.sort()

for i, var in enumerate(variaveis):
    print(f'{i} - {var}')

idx_vars = map(int, input("Escolha as variáveis:").split())
vars_esc = [variaveis[idx_variavel] for idx_variavel in idx_vars]

nro_somas = int(input("Quantas somas? "))

fig = plt.figure(figsize=(10,6))
gs = GridSpec(len(vars_esc)+nro_somas, 1)

for idx, var_esc in enumerate(vars_esc):
    dados = []
    for v in resultados['variaveis']:
        if var_esc == v[:-7]:
            # print(v, resultados['variaveis'][v])
            dados.append(resultados['variaveis'][v])
    
    ax = fig.add_subplot(gs[idx, 0])
    ax.plot(resultados['horas_D14'], dados, label=solucao)
    ax.set_title(var_esc)
    ax.set_xticks([])
    ax.set_ylim(0)

#print(resultados['variaveis'][''])

for i in range(nro_somas):
    idx_vars_somadas = map(int, input("Escolha variáveis a serem somadas:").split())
    vars_soma_esc = [variaveis[idx_variavel] for idx_variavel in idx_vars_somadas]

    if len(vars_soma_esc) > 0:
        dados_somados = np.zeros(len(resultados['horas_D14']))
        for idx, var_esc in enumerate(vars_soma_esc): 
            dados = []
            for v in resultados['variaveis']:
                if var_esc == v[:-7]:
                    # print(v, resultados['variaveis'][v])
                    dados.append(resultados['variaveis'][v])
            dados_somados += np.array(dados)

        ax = fig.add_subplot(gs[len(vars_esc)+i, 0])
        ax.plot(resultados['horas_D14'], dados_somados, label=solucao)
        ax.set_title(vars_soma_esc)
        ax.set_xticks([])
        ax.set_ylim(0)

# ax = fig.add_subplot(gs[len(vars_esc), 0])
# ax.plot(resultados['horas_D14'], resultados['parametros']['dados']["RNS"], label=solucao)
# ax.plot(resultados['horas_D14'], resultados['parametros']['dados']["RLS"], label=solucao)
# ax.set_title('produtos_britagem')
# ax.set_xticks([])
# ax.set_ylim(0)

plt.tight_layout()
# plt.savefig('output.png')

# if args.comparar_resultados is not None:
#     print(f'[OK]\nCarregando arquivo {args.comparar_resultados}...   ', end='')
#     with open(f'{args.comparar_resultados}', 'rb') as f:
#         resultados2 = pickle.load(f)
#     solucao2 = extrair_nome_solucao(args.comparar_resultados)
# else:
#     print(f'[OK]\nAlimentando dados da planilha...   ', end='')
#     solucao2 = 'planilha'
#     resultados2 = {}
#     resultados2['Taxa de Alimentação C3'] = [2500]*14*24
#     resultados2['Produção sem Incorporação'] = [25500/24]*14*24
#     resultados2['Estoque Produto Pátio'] = [255823]*24 + [175082]*24 + [134342]*24 + [161601]*24 + [111411]*24 + [78670]*24 + [47730]*24 + [38189]*24 + [65449]*24 + [92708]*24 + [119968]*24 + [147227]*24 + [174487]*24 + [113746]*24
#     resultados2['Início Carregamento Navios'] = [2, 7, 6, 5, 14]
#     resultados2['Bombeamento de Polpa'] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
#     resultados2['Estoque Polpa Ubu'] = [12459,11323,10188,11172,12157,13141,14126,15110,16095,17080,18064,19049,20033,21018,22002,22987,23972,24956,23820,22685,21549,20413,19277,18141,17005,17621,18238,18854,19470,20086,20702,21318,21934,22550,23166,23782,24398,25014,25630,24494,23358,22222,21087,19951,18815,17679,18295,18911,19527,20143,20759,21375,21991,22607,23223,23839,24455,25071,25687,24552,23416,22280,21144,20008,18873,17737,18353,18969,19585,20201,20817,21433,22049,22665,23281,23897,24513,25129,25745,24609,23473,22338,21202,20066,18930,17794,18410,19026,19642,20259,20875,21491,22107,22723,23339,23955,24571,25187,25803,24667,23531,22395,21260,20124,18988,19604,20220,20836,21452,22068,22684,23300,23916,24532,25148,25764,26380,26996,25860,24725,23589,22453,21317,20181,20797,21413,22029,22645,23261,23877,24494,25110,25726,26342,26958,27574,28190,27054,25918,24782,23646,22511,21375,21991,22607,23223,23839,24455,25071,25687,26303,26919,27535,28151,28767,29383,28247,27111,25976,24840,23704,22568,21432,22048,22664,23281,23897,24513,25129,25745,26361,26977,27593,28209,28825,29441,28305,27169,26033,24898,23762,22626,23242,23858,24474,25090,25706,26322,26938,27554,28170,28786,29402,30018,30634,29498,28363,27227,26091,24955,23819,24435,25051,25667,26283,26899,27515,28132,28748,29364,29980,30665,31350,32035,30899,29763,28627,27491,26356,25220,24084,24769,25454,26139,26824,27509,28194,28879,27743,26607,25471,24336,23200,22064,20928,21544,22160,22776,23392,24008,24624,25240,25856,26472,27088,27704,28320,28937,27801,26665,25529,24393,23257,22122,20986,21602,22218,22834,23450,24066,24682,25298,25914,26530,27146,27762,28378,28994,27858,26723,25587,24451,23315,22179,21043,21659,22276,22892,23508,24124,24740,25356,25972,26588,27204,27820,28436,29052,27916,26780,25644,24509,23373,22237,21101,21717,22333,22949,23565,24181,24797,25413,26029,26645,27261,27877,28493,29109,27974,26838,25702,24566,23430,22295,22911,23527,24143,24759,25375,25991,26607,27223,27839,28455,29071,29687,30303,29167,28031,26895,25760,24624,23488,24104,24720,25336]
#     resultados2['Estoque EB06'] = [8066,7638,7210,6782,6354,5926,5498,5070,4642,4214,3786,3358,4200,5042,5884,6726,7568,8410,9252,8824,8396,7968,7540,7112,6712,6313,5914,5515,5116,4716,4317,3918,4789,5660,6531,7401,8272,9143,8744,8345,7946,7546,7147,6748,6349,5950,5551,5151,4750,4350,3949,4818,5687,6556,7425,8294,9163,8762,8361,7960,7559,7159,6758,6357,5956,5555,5154,4753,4352,3951,4820,5689,6567,7445,8323,9201,8810,8418,8026,7634,7242,6850,6458,6066,5674,5282,4890,4498,4106,4984,5862,6740,7618,8496,9374,10252,9856,9460,9064,8668,8272,7876,7480,7084,6688,6292,5896,5500,5104,5978,6852,7726,8600,9474,10348,9952,9556,9160,8764,8368,7928,7489,7050,6611,6171,5732,5293,4854,5684,6515,7346,8177,9007,9838,9399,8960,8520,8081,7642,7203,6763,6324,5885,5446,4723,4001,3279,3877,4475,5073,5671,6269,6867,7465,6743,6021,5299,4577,3855,3133,2411,3009,3607,4205,4803,5401,5999,6597,6196,5795,5394,4993,4592,4191,3790,3389,2988,2586,2185,1784,1383,2252,3121,3990,4859,5728,6597,7466,7065,6663,6262,5861,5466,5070,4674,4278,3882,3487,3091,2695,2299,3174,4048,4922,5796,6670,7545,8419,8023,7627,7232,6836,6440,6044,5648,5253,4873,4494,4115,3736,3357,4247,5138,6029,6920,7811,8701,9592,9213,8834,8454,8075,7696,7317,6938,6558,6179,5800,5421,5042,4649,5526,6404,7281,8158,9036,9913,9521,9128,8735,8343,7950,7557,7165,6772,6380,5987,5594,5202,4809,5686,6564,7441,8318,9179,10039,9629,9219,8809,8399,7989,7579,7170,6760,6350,5940,5530,5120,4710,5570,6431,7291,8151,9011,9871,9461,9051,8641,8214,7786,7359,6931,6504,6076,5649,5221,4794,4366,5209,6051,6894,7736,8579,9421,10264,9836,9408,8981,8553,8126,7698,7271,6847,6423,6000,5576,5152,4728,5574,6421,7267,8113,8959,9805,9382,8958,8534,8110,7687,7263,6839,6415,5991,5568,5144,4720]

# print(f'[OK]\nCriando gráficos...   ', end='')

# # Configurações de estilo do seaborn
# sns.set(style="whitegrid")

# # Criação do grid para o subplot
# fig = plt.figure(figsize=(24, 12))
# if args.graficos_adicionais:
#     gs = GridSpec(9, 2)
# else:
#     gs = GridSpec(7, 2)

# dias = np.array([int(dia[1:]) for dia in resultados['dias']])
# horas = np.array(range(len(resultados['horas_D14'])))

# xticks = range(0, len(resultados['horas_D14']), 24)

# ax1 = fig.add_subplot(gs[0:2, 1])
# ax1.plot(resultados['horas_D14'], resultados['Taxa de Alimentação C3'], label=solucao)
# ax1.plot(resultados['horas_D14'], resultados2['Taxa de Alimentação C3'], label=solucao2)
# ax1.set_title('Taxa de Alimentação C3')
# ax1.set_xticks(xticks)
# ax1.set_xticklabels(resultados['dias'])
# maior = max(max(resultados['Taxa de Alimentação C3']),max(resultados2['Taxa de Alimentação C3']))
# ax1.set_ylim(bottom=-maior*0.1, top=maior*1.1)

# ax2 = fig.add_subplot(gs[3:5, 0])
# ax2.plot(horas, resultados['Produção sem Incorporação'], label=solucao)
# ax2.plot(horas, resultados2['Produção sem Incorporação'], label=solucao2)
# ax2.set_title('Produção sem Incorporação')
# ax2.set_xticks(xticks)
# ax2.set_xticklabels(resultados['dias'])
# maior = max(max(resultados['Produção sem Incorporação']),max(resultados2['Produção sem Incorporação']))
# ax2.set_ylim(bottom=-maior*0.1, top=maior*1.1)
# # Desativa a notação científica no eixo y
# ax2.get_yaxis().get_major_formatter().set_useOffset(False)

# ax3 = fig.add_subplot(gs[2, 0:2])
# # Bombeamento de polpa
# ax3.bar(resultados['horas_D14'], resultados['Bombeamento de Polpa'])
# ax3.bar(resultados['horas_D14'], resultados2['Bombeamento de Polpa'], bottom=1)
# # Bombeamento de água
# ax3.bar(resultados['horas_D14'], [1 if valor == 0 else 0 for valor in resultados['Bombeamento de Polpa']], color=(0.86, 0.86, 0.86))
# ax3.bar(resultados['horas_D14'], [1 if valor == 0 else 0 for valor in resultados2['Bombeamento de Polpa']], bottom=1, color=(0.86, 0.86, 0.86))
# ax3.set_title('Bombeamento Mineroduto')
# ax3.set_yticks([])
# # Configura os rótulos do eixo X sem as linhas de rótulo (ticks)
# ax3.grid(False, axis='x')
# ax3.set_xticks(xticks)
# ax3.set_xticklabels(resultados['dias'])

# ax4 = fig.add_subplot(gs[3:5, 1])
# ax4.plot(horas, resultados2['Estoque Polpa Ubu'], color=sns.color_palette()[1], label=solucao2)
# ax4.plot(horas, resultados['Estoque Polpa Ubu'], label=solucao)
# ax4.axhline(y=resultados['cenario']['max_estoque_polpa_ubu'], color='gray', linestyle='dashed')
# ax4.set_title('Estoque Polpa Ubu')
# ax4.set_xticks(xticks)
# ax4.set_xticklabels(resultados['dias'])
# maior = max(resultados['cenario']['max_estoque_polpa_ubu'], 
#                                max(resultados['Estoque Polpa Ubu']),
#                                max(resultados2['Estoque Polpa Ubu']))
# ax4.set_ylim(bottom=-maior*0.1, top=maior*1.1)

# ax5 = fig.add_subplot(gs[5:7, 0])
# ax5.plot(horas, resultados['Estoque Produto Pátio'], label=solucao)
# ax5.plot(horas, resultados2['Estoque Produto Pátio'], color=sns.color_palette()[1], label=solucao2)
# ax5.set_title('Estoque Pátio Porto')
# ax5.set_xticks(xticks)
# ax5.set_xticklabels(resultados['dias'])
# maior = max(max(resultados['Estoque Produto Pátio']),max(resultados2['Estoque Produto Pátio']))
# ax5.set_ylim(bottom=-maior*0.1, top=maior*1.1)

# ax6 = fig.add_subplot(gs[5:7, 1])
# ax6.scatter([1+h/24 for h in resultados['Início Carregamento Navios']], resultados['navios_ate_d14'], marker='o')
# if args.comparar_resultados:
#     ax6.scatter([1+h/24 for h in resultados2['Início Carregamento Navios']], resultados['navios_ate_d14'], marker='x')
# else:
#     ax6.scatter([d for d in resultados2['Início Carregamento Navios']], resultados['navios_ate_d14'], marker='x')
# # Adicionar rótulos próximos aos pontos de dados
# for i, navio in enumerate(resultados['navios_ate_d14']):
#     ax6.annotate(navio, (1+resultados['Início Carregamento Navios'][i]/24, navio), textcoords="offset points", xytext=(0,10), ha='center')
# ax6.set_yticks([])
# ax6.set_title('Início Carregamento Navios')
# ax6.set_xticks(range(len(resultados['dias'])+1))
# ax6.set_xticklabels(['']+resultados['dias'])

# # Criação da legenda
# legenda = ax1.legend(loc='center right')

# offset = 25
# def texto_resultados(resultados):    
#     texto = (f'{"Cenário:":<{offset}}{resultados["cenario"]["nome"]}\n' +
#             '\n' +         
#             f'Função Objetivo(FO):\n' +
#             f'{" ".join(resultados["solver"]["fo"])}\n' +
#             '\n' +
#             # Comentando: porque o PULP retorna Optimal mesmo que tenha estourado o tempo ou tenha GAP
#             # f'{"Status solução:":<{offset}}{resultados["solver"]["status"]}\n' +
#             f'{"Valor FO:":<{offset}}{resultados["solver"]["valor_fo"]:.1f}\n' +
#             '\n' +
#             f'{"Excesso (Pellet Feed):":<{offset}}{sum(resultados["Excesso Volume Pátio"]):.1f}\n' +
#             '\n' +
#             f'{"Solver:":<{offset}}{resultados["solver"]["nome"]}\n' +
#             f'{"Tempo solução:":<{offset}}{resultados["solver"]["tempo"]:.1f} (s)\n')
#     return texto

# # Adição de informações textuais dos resultados
# fig.text(0.03, 0.75, texto_resultados(resultados), ha='left', fontfamily='monospace', fontweight='bold', fontsize=11, color=sns.color_palette()[0])
# if args.comparar_resultados:
#     fig.text(0.28, 0.75, texto_resultados(resultados2), ha='left', fontfamily='monospace', fontweight='bold', fontsize=11, color=sns.color_palette()[1])
# else:
#     texto = (f'Comparando com {solucao2}\n' +
#             '\n' +
#             f'{"Taxa Alim:":<{offset}}{sum(resultados2["Taxa de Alimentação C3"]):.1f}\n' +
#             f'{"Prod s/ Incorp:":<{offset}}{sum(resultados2["Produção sem Incorporação"]):.1f}')
#     fig.text(0.28, 0.85, texto, ha='left', fontfamily='monospace', fontweight='bold', fontsize=11, color=sns.color_palette()[1])

# if args.graficos_adicionais:
#     ax7 = fig.add_subplot(gs[7:9, 0])
#     ax7.plot(horas, resultados['Estoque EB06'], label=solucao)
#     ax7.plot(horas, resultados2['Estoque EB06'], color=sns.color_palette()[1], label=solucao2)
#     ax7.set_title('Estoque EB06')
#     ax7.set_xticks(xticks)
#     ax7.set_xticklabels(resultados['dias'])
#     maior = max(max(resultados['Estoque EB06']),max(resultados2['Estoque EB06']))
#     ax7.set_ylim(bottom=-maior*0.1, top=maior*1.1)
    
#     ax8 = fig.add_subplot(gs[7:9, 1])
#     ax8.plot(horas, resultados['Excesso Volume Pátio'], label=solucao)
#     if args.comparar_resultados:
#         ax8.plot(horas, resultados2['Excesso Volume Pátio'], color=sns.color_palette()[1], label=solucao2)
#     ax8.set_title('Pellet Feed')
#     ax8.set_xticks(xticks)
#     ax8.set_xticklabels(resultados['dias'])
#     if args.comparar_resultados:
#         maior = max(max(resultados['Excesso Volume Pátio']),max(resultados2['Excesso Volume Pátio']))
#         ax8.set_ylim(bottom=-maior*0.1, top=maior*1.1)

# print(f'[OK]\nAjustando layout...   ', end='')

# Ajuste de layout
plt.tight_layout()

# if args.salvar:
#     nome_arquivo = f'{solucao}_vs_{solucao2}'
#     print(f'[OK]\nSalvando figura {nome_arquivo}...   ', end='')
#     plt.savefig(f'experimentos/{nome_arquivo}', dpi=300, bbox_inches='tight')

if not args.nao_exibir:
    # Exibição dos gráficos
    print(f'[OK]\nExibindo gráficos...   ', end='')
    plt.savefig('output')

print('[OK]')

