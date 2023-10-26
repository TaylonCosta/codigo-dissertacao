import numpy as np
import gym
from gym import spaces
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize
from stable_baselines3 import PPO
import itertools

INSTANCIA_UNICA = True
SEMENTE_INSTANCIA_UNICA = 51
PASSOS_TREINAMENTO = 500000
USAR_LOG_TENSORBOARD = True # Para ver o log, execute o comando: tensorboard --logdir ./ppo_tensorboard/
SEMENTE = 5
ALEATORIO = FALSE
TAMANHO = 24

if not INSTANCIA_UNICA:
   SEMENTE_INSTANCIA_UNICA = None

class CustomizedEnv(gym.Env):

  
  def Avalia(self, BombeamentoPolpa):
    return estoque_eb06, estoque_ubu, prod_concentrador, prod_usina  = Learning.function(BombeamentoPolpa)


  def criar_instancia(self):
    self.estoque_eb06_inicial, self.estoque_ubu_inicial, self.disp_conc_inicial, self.disp_usina_inicial, self.MaxE06, self.MaxEUBU, self.AguaLi, self.AguaLs, self.PolpaLi, self.PolpaLs  = Inicializar(ALEATORIO)
    self.MaxCon = max(self.disp_conc_inicial)
    self.MaxUbu= max(self.disp_usina_inicial)

  def usar_instancia(self):
    self.estoque_eb06 = self.estoque_eb06_inicial.copy() #Volume 
    self.estoque_ubu = self.estoque_ubu_inicial.copy() #Volume
    self.disp_conc = self.disp_conc_inicial.copy() #Produção Max Hora 
    self.disp_usina = self.disp_usina_inicial.copy() #Produção Max Hora


  def __init__(self, instancia_unica=False, seed=None):
    super(CustomizedEnv, self).__init__()

    print(f"Criando ambiente: {instancia_unica=} {seed=}" )  
    
    size = int(TAMANHO) #int(2*TAMANHO)
    # Define action and observation space
    n_actions = 2
    self.action_space = spaces.MultiBinary(n_actions)
    #self.observation_space = spaces.Box(len(self.Lista0)*[tam]+len(self.Lista0)*[self.Dmax])
    self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(4*size), dtype=np.float64)

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
      estado_temp[i] = estado_temp[i]/(self.MaxE06)
    
    for i in range(TAMANHO, 2*TAMANHO):
      estado_temp[i] = estado_temp[i]/(self.MaxEUBU)

    for i in range(2*TAMANHO, 3*TAMANHO):
      estado_temp[i] = estado_temp[i]/(self.MaxCon)

    for i in range(3*TAMANHO, 4*TAMANHO):
      estado_temp[i] = estado_temp[i]/(self.disp_usina)

    return np.clip(np.array(estado_temp)*2 - 1, self.observation_space.low, self.observation_space.high) 

  def reset(self):
    """
    Important: the observation must be a numpy array
    :return: (np.array) 
    """
    if not self.instancia_unica: self.criar_instancia()

    self.usar_instancia()
    self.passo = 0
    self.nBatchsP = 0
    self.nBatchsA = 0
    self.ultima_acao = None
    self.ultima_recompensa = 0
    self.BombeamentoPolpa = [0]*TAMANHO
    self.estoque_eb06, self.estoque_ubu, self.prod_concentrador, self.prod_usina = Avalia(self.BombeamentoPolpa)
    self.FO_Inicial = sum(self.prod_usina)
    self.FO_Best = self.FO_Inicial
    return self.normalizar_estado(self.estoque_eb06 + self.estoque_ubu + self.disp_conc + self.disp_usina)
  
  self.AguaLi, self.AguaLs, self.PolpaLi, self.PolpaLs
  
  def step(self, action):
    
    FIM = TAMANHO

    Erro = False

    if action == 1:
      if self.nBatchsP + 1 > self.PolpaLs:
        recompensa = -100000000
        Erro = True
      elif self.nBatchsA >0 and self.nBatchsA < self.AguaLi:
        recompensa = -100000000
        Erro = True
      if Erro == False:
        recompensa = 1
        self.nBatchsP += 1
        self.nBatchsA = 0

    if action == 0:
      if self.nBatchsA + 1 > self.AguaLs:
        recompensa = -100000000
        Erro = True
      elif self.nBatchsP >0 and self.nBatchsP < self.PolpaLi:
        recompensa = -100000000
        Erro = True
      if Erro == False:
        recompensa = 1
        self.nBatchsP = 0
        self.nBatchsA += 0    

    if Erro == False:
      self.BombeamentoPolpa[self.passo] = action
      self.passo +=1
      
      self.FO_anterior = sum(self.prod_usina)

      self.estoque_eb06, self.estoque_ubu, self.prod_concentrador, self.prod_usina = Avalia(self.BombeamentoPolpa)
      
      self.FO = sum(self.prod_usina)

      if self.FO > self.FO_Best:
        self.FO_Best = self.FO_Inicial

      recompensa = float(self.FO - self.FO_anterior)

      self.ultima_acao = action


    self.ultima_recompensa = recompensa
   
    terminou_episodio = bool(self.passo == FIM)

    # Optionally we can pass additional info, we are not using that for now
    info = {}

    return self.normalizar_estado(self.estoque_eb06 + self.estoque_ubu + self.disp_conc + self.disp_usina), recompensa, terminou_episodio, info
  
  def render(self, mode='console'):
    if mode != 'console':
      raise NotImplementedError()
    
    if (self.passo > 0): 
      print(f'Passo {self.passo}') 
    else: 
      print('Instância:')
    
    print(f'\tÚltima ação: {self.ultima_acao}, FO: {self.FO}')
    print(f'\tLista: {self.BombeamentoPolpa}')
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

model.save("ppo_Mineroduto")

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
    
    results.append({'FO_Best': env.FO_Best, 'FO_inicial': env.FO_inicial})  
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
myfile.close()


print(f"Done! Resultado: {env.FO_Best} (inicial: {env.FO_inicial})")
