import numpy as np
import gym
from gym import spaces
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize
from stable_baselines3 import PPO
import itertools

INSTANCIA_UNICA = False
SEMENTE_INSTANCIA_UNICA = 51
PASSOS_TREINAMENTO = 500000
USAR_LOG_TENSORBOARD = True # Para ver o log, execute o comando: tensorboard --logdir ./ppo_tensorboard/
FACTOR = 25
TAMANHO_TOTAL = 100
TAMANHO = 5
MAXIMO = 200
SEMENTE = 5
TROCAS = int(np.round(0.3*TAMANHO))

if not INSTANCIA_UNICA:
   SEMENTE_INSTANCIA_UNICA = None

class CustomizedEnv(gym.Env):

  
  def Avalia(self, lista, distancia):
    FO = 0
    n = len(lista)
    ListaD = [0 for x in lista]
    my_list0 = [x for x in lista if x != -1]
    lista_original  = self.Lista_inicial.copy()

    my_list = [x for x in lista_original if x not in my_list0]
    subset = distancia[:, my_list] 

    for i in range(n-1):
        if lista[i] != -1 and lista[i+1] != -1:
          FO = FO + distancia[lista[i], lista[i+1]]
        else:
          if lista[i] !=-1 and lista[i+1] == -1:
            FO = FO + np.max(subset[lista[i],:])
          if lista[i] ==-1 and lista[i+1] != -1:
            FO = FO + np.max(subset[lista[i+1],:])
          if lista[i] ==-1 and lista[i+1] == -1:
            FO = FO + self.Dmax_instancia
        ListaD[i] = FO
    if lista[n-1] != -1 and lista[0] != -1:
      FO = FO + distancia[lista[i], lista[i+1]]
    else:
      if lista[n-1] !=-1 and lista[0] == -1:
        FO = FO + np.max(subset[lista[n-1],:])
      if lista[n-1] ==-1 and lista[0] != -1:
        FO = FO + np.max(subset[lista[0],:])
      if lista[n-1] ==-1 and lista[0] == -1:
        FO = FO + self.Dmax_instancia
    ListaD[i] = FO

    return FO,ListaD

  def Swap (self, ListaI, ListaF, distancia, action):

    a = action[0]
    b = action[1]
    valor = ListaI[a]
    ListaI[a] = -1
    ListaF[b] = valor

    FOnew,ListaD = self.Avalia(ListaF, distancia)

    return ListaI,ListaF,ListaD, FOnew
    
  def escolher_subconjunto_de_posicoes(self,matriz, tamanho_subconjunto):
      """
      Escolhe um subconjunto de posições de uma matriz aleatoriamente.

      Args:
          matriz: A matriz a partir da qual as posições serão escolhidas.
          tamanho_subconjunto: O tamanho do subconjunto a ser escolhido.

      Returns:
          Um subconjunto de posições da matriz.
      """

      # Gera um vetor de números aleatórios entre 0 e o tamanho da matriz.
      numeros_aleatorios = self.rand_generator.choice(range(0, matriz.shape[0]), size = tamanho_subconjunto, replace=False)

      # Retorna as posições correspondentes aos números aleatórios.
      return numeros_aleatorios

  def criar_instancia(self):
    self.Distancia_inicial = self.gerar_matriz_distancias_aleatorias(TAMANHO_TOTAL, MAXIMO, SEMENTE)
    #self.rand_generator.randint(5,self.Dmax, size=(TAMANHO,TAMANHO))
    subconjunto_de_posicoes = self.escolher_subconjunto_de_posicoes(self.Distancia_inicial, TAMANHO)
    self.Distancia = self.Distancia_inicial[subconjunto_de_posicoes,:]
    self.Distancia = self.Distancia[:,subconjunto_de_posicoes]

    diagonal_mask = np.diag_indices_from(self.Distancia)
    Distancia_temp  =  self.Distancia.copy()
    Distancia_temp[diagonal_mask] = -1
    self.Dmax_instancia = Distancia_temp.max()
    self.UB_Geral = sum(list(Distancia_temp.max(axis=1)))
    Distancia_temp[diagonal_mask] = 1000
    self.Dmin_instancia = Distancia_temp.min()

    diagonal_mask = np.diag_indices_from(self.Distancia_inicial)
    Distancia_temp  =  self.Distancia_inicial.copy()
    Distancia_temp[diagonal_mask] = -1
    self.DmaxG_instancia = Distancia_temp.max()
    Distancia_temp[diagonal_mask] = 1000
    self.DminG_instancia = Distancia_temp.min()

    diagonal_mask = np.diag_indices_from(self.Distancia)
    Distancia_temp  =  self.Distancia.copy()
    Distancia_temp[diagonal_mask] = 0
    self.Media_instancia = Distancia_temp.mean()

    #self.UB_Geral = sum(list(self.Distancia.max(axis=1)))
    self.LB_inicial = sum(list(self.Distancia.min(axis=1)))    
    self.Lista_inicial =  sorted(subconjunto_de_posicoes)
    self.Lista_Final =  list(map(lambda x: -1, self.Lista_inicial))
    self.FO_Best_inicial = self.UB_Geral
    self.FO_inicial = self.UB_Geral
    self.FO_Best = self.FO_Best_inicial
    self.ListaD_Inicial =  [self.DmaxG_instancia for i in range(TAMANHO)]
    self.ListaD_Inicial = list(itertools.accumulate(self.ListaD_Inicial))

  def usar_instancia(self):
    self.Distancia = self.Distancia_inicial.copy()
    self.LB = self.LB_inicial
    self.ListaI = self.Lista_inicial.copy()
    self.ListaF = self.Lista_Final.copy()
    self.FO = self.UB_Geral
    self.FO_Best = self.FO
    self.ListaD = self.ListaD_Inicial

  def gerar_matriz_distancias_aleatorias(self, n, maximo, seed):
      """
      Gera uma matriz de distâncias aleatórias com n pontos e semente fixa.

      Args:
          n: O número de pontos na matriz.
          seed: A semente para o gerador de números aleatórios.

      Returns:
          Uma matriz de distâncias aleatórias.
      """

      # Inicializa o gerador de números aleatórios com a semente fornecida.
      np.random.seed(seed)

      # Gera as coordenadas dos pontos.
      pontos = np.random.rand(n, 2)

      # Calcula as distâncias entre todos os pares de pontos.
      distancias = np.linalg.norm(pontos - pontos[:, np.newaxis], axis=2)*FACTOR
    
      # Itera sobre a matriz.
      for i in range(distancias.shape[0]):
        # Define a distância para ele mesmo como infinito.
        distancias[i, i] = float("inf")

      # Limita as distâncias ao máximo especificado.
      distancias = np.clip(distancias, 0, maximo)

      return distancias

  def __init__(self, instancia_unica=False, seed=None):
    super(CustomizedEnv, self).__init__()

    print(f"Criando ambiente: {instancia_unica=} {seed=}" )  
    
    tam = TAMANHO
    self.Dmax = 10*tam
    
    self.Lista0 = [0]*tam

    size = int(TAMANHO) #int(2*TAMANHO)
    # Define action and observation space
    self.action_space = spaces.MultiDiscrete(np.array([tam,tam]))
    #self.observation_space = spaces.Box(len(self.Lista0)*[tam]+len(self.Lista0)*[self.Dmax])
    self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(3*size+1,), dtype=np.float64)

    self.seed(seed)
    self.instancia_unica = instancia_unica
    if self.instancia_unica: self.criar_instancia()
    self.passo = 0
    self.iter = 0
    self.ultima_acao = None
    self.ultima_recompensa = None    
  

  def normalizar_estado(self, estado):
    
    estado_temp = estado.copy()

    for i in range(TAMANHO):
      estado_temp[i] = estado_temp[i]/(TAMANHO_TOTAL)
    
    for i in range(TAMANHO, 2*TAMANHO):
      estado_temp[i] = estado_temp[i]/(TAMANHO_TOTAL)

    for i in range(2*TAMANHO, 3*TAMANHO):
      estado_temp[i] = estado_temp[i]/TAMANHO*(self.Dmax_instancia - self.Dmin_instancia)

    estado_temp[3*TAMANHO] =   estado_temp[TAMANHO]/(self.DmaxG_instancia-self.DminG_instancia)
   
    return np.clip(np.array(estado_temp)*2 - 1, self.observation_space.low, self.observation_space.high) 

  def reset(self):
    """
    Important: the observation must be a numpy array
    :return: (np.array) 
    """
    if not self.instancia_unica: self.criar_instancia()

    self.usar_instancia()
    self.passo = 0
    self.iter = 0
    self.ultima_acao = None
    self.ultima_recompensa = 0
    # self.ListaD = self.GeraListaD(self.Lista)
    self.oldAction = [0,0]
    return self.normalizar_estado(self.ListaI + self.ListaF + self.ListaD + [self.Media_instancia])
  
  
  def step(self, action):
    
    FIM = TAMANHO

    if self.ListaI[action[0]] == -1 or self.ListaF[action[1]] != -1:
      recompensa = -100000
    else:
      self.iter =  self.iter + 1
      self.FO_anterior = self.FO
      self.ListaI, self.ListaF, self.ListaD, self.FO = self.Swap(self.ListaI, self.ListaF, self.Distancia_inicial, action)
      self.ultima_acao = action

      recompensa = float(self.FO_anterior - self.FO)

      if self.FO_Best > self.FO:
        self.FO_Best = self.FO
        recompensa = 100*recompensa
      else:
        if recompensa < 0:
          recompensa = -10*recompensa
        else:
          recompensa = 10*recompensa

    self.oldAction = action

    #recompensa = (0.66)*self.ultima_recompensa + (0.33)*recompensa
    self.ultima_recompensa = recompensa
    # self.ListaD = self.GeraListaD(self.Lista)
    terminou_episodio = bool(self.FO == self.LB or self.iter == FIM)

    # Optionally we can pass additional info, we are not using that for now
    info = {}

    self.passo += 1

    return self.normalizar_estado(self.ListaI + self.ListaF + self.ListaD + [self.Media_instancia]), recompensa, terminou_episodio, info
  
  def render(self, mode='console'):
    if mode != 'console':
      raise NotImplementedError()
    
    if (self.passo > 0): 
      print(f'Passo {self.passo}') 
    else: 
      print('Instância:')
    
    print(f'\tÚltima ação: {self.ultima_acao}, FO: {self.FO}')
    print(f'\tLista: {self.Lista}')
    print(f'\tListaD: {self.ListaD}')
    print(f'\tRecompensa: {self.ultima_recompensa}')

  def close(self):
    pass
  
  def seed(self, seed=None):
    self.rand_generator = np.random.RandomState(seed)
    self.action_space.seed(seed)

print("===== CHECANDO AMBIENTE =====")

env = CustomizedEnv(instancia_unica=INSTANCIA_UNICA, seed=SEMENTE_INSTANCIA_UNICA)
# If the environment don't follow the interface, an error will be thrown
check_env(env, warn=True)

print()
print("===== DEMONSTRANDO AMBIENTE =====")
env = CustomizedEnv(instancia_unica=INSTANCIA_UNICA, seed=SEMENTE_INSTANCIA_UNICA)

print(f"{env.observation_space=}")
print(f"{env.action_space=}")
print(f"{env.action_space.sample()=}")

print()
print("===== TREINANDO COM POO =====")

if INSTANCIA_UNICA:
   n_envs = 1
else:
   n_envs = 4

# Cria um ambiente vetorizado considerando 4 ambientes (atores do PPO)
vec_env = make_vec_env(CustomizedEnv, n_envs=n_envs, env_kwargs={'instancia_unica': INSTANCIA_UNICA, 'seed': SEMENTE_INSTANCIA_UNICA})

# Usa um adaptador para normalizar as recompensas
vec_env = VecNormalize(vec_env, training=True, norm_obs=False, norm_reward=True, clip_reward=10.)

if USAR_LOG_TENSORBOARD:
  tensorboard_log="./ppo_tensorboard/"
else:
  tensorboard_log=None

# Train the agent
model = PPO('MlpPolicy', vec_env, verbose=1, tensorboard_log=tensorboard_log).learn(PASSOS_TREINAMENTO)

model.save("ppo_Routing_v2")

#model = PPO.load("ppo_Routing", env=env)


print()
print("===== DEMONSTRANDO RESULTADO =====")

class RandomAgent():
  def __init__(self, env):
    self.env = env

  def predict(self, observation, deterministic=False):
    # ignora o parâmetro deterministic
    return self.env.action_space.sample(), None

def evaluate_results(model, env, seeds, render=False):
  results = []
  FO_bests = []
  
  for seed in seeds:
    env.seed(seed)
    obs = env.reset()
    if render: env.render()
    done = False
    while not done:
      action, _ = model.predict(obs, deterministic=True)
      print(obs)
      print(action)
      obs, reward, done, info = env.step(action)
      if render: env.render()
    
    results.append({'FO_Best': env.FO_Best, 'FO_inicial': env.FO_inicial, 'LB': env.LB})  
    FO_bests.append(env.FO_Best)
  
  return np.average(FO_bests), results


SEMENTES_FIXAS_AVALIACAO = [51, 312, 4, 207, 461, 394, 859, 639, 138, 727]

if INSTANCIA_UNICA:  
  qtde_avaliacoes = 1
else:
  qtde_avaliacoes = 10

#OLHAR COMO FIXAR SEED NO AMBIENTE
SEMENTES_AVALIACAO = SEMENTES_FIXAS_AVALIACAO[:qtde_avaliacoes]

PPO_avg_FO_bests, PPO_results = evaluate_results(model, env, SEMENTES_AVALIACAO, render=False)
#random_avg_FO_bests, random_results = evaluate_results(RandomAgent(env), env, SEMENTES_AVALIACAO, render=False)

myfile = open("resultados.txt", "w")
myfile.write(str(PPO_avg_FO_bests) +"\n")
myfile.write("-------------------------"+"\n")
myfile.write(str(random_results) +"\n")
myfile.close()


print(f"Done! Resultado: {env.FO_Best} (inicial: {env.FO_inicial}, LB: {env.LB})")

print()
print(f"{'Execução':^20}{'FO_Best PPO':^20}{'FO_Best Random':^20}{'FO_inicial PPO':^20}{'FO_inicial Random':^20}{'LB PPO':^20}{'LB Random':^20}")
for i in range(len(PPO_results)):
  print(f"{i+1:^20}", end="")
  print(f"{PPO_results[i]['FO_Best']:^20}", end="")
  print(f"{random_results[i]['FO_Best']:^20}", end="")
  print(f"{PPO_results[i]['FO_inicial']:^20}", end="")
  print(f"{random_results[i]['FO_inicial']:^20}", end="")
  print(f"{PPO_results[i]['LB']:^20}", end="")
  print(f"{random_results[i]['LB']:^20}")

print()
print(f"FO_Best médio do PPO: {PPO_avg_FO_bests}")
print(f"FO_Best médio do Random: {random_avg_FO_bests}")
