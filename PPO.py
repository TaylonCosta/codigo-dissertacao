import numpy as np
import gymnasium
from gymnasium import spaces
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize
from stable_baselines3 import PPO
import itertools
import math
from ai import Learning
import random
from load_data import Load_data

UNIQUE_INSTANCE = True
UNIQUE_INSTANCE_SEED = 51
TRAINING_STEPS = 5
USAR_LOG_TENSORBOARD = True # Para ver o log, execute o comando: tensorboard --logdir ./ppo_tensorboard/
SEMENTE = 5
RANDOM = False
SIZE = 24

if not UNIQUE_INSTANCE:
   UNIQUE_INSTANCE_SEED = None

class CustomizedEnv(gymnasium.Env):

  def convert_bombeamento_list(self, BombeamentoPolpa, ):
    bombeamento = {"PRDT_C":{}}
    cont = 0
    dias =      [f'd{dia+1:02d}' for dia in range(1)]
    horas =     [f'h{hora+1:02d}' for hora in range(24)]
    horas_D14 = [f'{dia}_{hora}' for dia in dias for hora in horas]
    for i in horas_D14:
      bombeamento['PRDT_C'].update({i: BombeamentoPolpa[cont]})
      cont += 1

    return bombeamento

  def initialize(self, rand):
    if rand:
      self.estoque_eb06_inicial = random.randint()
      self.estoque_ubu_inicial = random.randint()
      self.disp_conc_inicial = random.randint()
      self.disp_usina_inicial = random.randint()
      self.MaxE06 = random.randint()
      self.MaxEUBU = random.randint()
      self.AguaLi = random.randint()
      self.AguaLs = random.randint()
      self.PolpaLi = random.randint()
      self.PolpaLs = random.randint()

    else:
      load_data = Load_data()
      self.estoque_eb06_inicial, self.estoque_ubu_inicial, self.disp_conc_inicial, self.disp_usina_inicial, self.MaxE06, self.MaxEUBU, self.AguaLi, self.AguaLs, self.PolpaLi, self.PolpaLs = load_data.load_simplified_data_ppo()
      return self.estoque_eb06_inicial, self.estoque_ubu_inicial, self.disp_conc_inicial, self.disp_usina_inicial, self.MaxE06, self.MaxEUBU, self.AguaLi, self.AguaLs, self.PolpaLi, self.PolpaLs
  
  def evaluate(self, BombeamentoPolpa):
    L = Learning(self.convert_bombeamento_list(BombeamentoPolpa))
    status, estoque_eb06, estoque_ubu, prod_concentrador, prod_usina = L.solve_model()
    return status, estoque_eb06, estoque_ubu, prod_concentrador, prod_usina


  def create_instance(self):
    self.estoque_eb06_inicial, self.estoque_ubu_inicial, self.disp_conc_inicial, self.disp_usina_inicial, self.MaxE06, self.MaxEUBU, self.AguaLi, self.AguaLs, self.PolpaLi, self.PolpaLs = self.initialize(RANDOM)
    self.MaxCon = max(self.disp_conc_inicial)
    self.MaxUbu= max(self.disp_usina_inicial)

  def use_instance(self):
    self.estoque_eb06 = self.estoque_eb06_inicial #Volume 
    self.estoque_ubu = self.estoque_ubu_inicial #Volume
    self.disp_conc = self.disp_conc_inicial.copy() #Produção Max Hora 
    self.disp_usina = self.disp_usina_inicial.copy() #Produção Max Hora


  def __init__(self, unique_instance=False, seed=None):
    super(CustomizedEnv, self).__init__()

    print(f"Criando ambiente: {unique_instance=} {seed=}" )  
    
    size = int(SIZE) #int(2*TAMANHO)
    # Define action and observation space
    n_actions = 1
    self.action_space = spaces.MultiBinary(n_actions)
    #self.observation_space = spaces.Box(len(self.Lista0)*[tam]+len(self.Lista0)*[self.Dmax])
    self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(4*size,), dtype=np.float64)

    self.seed(seed)
    self.unique_instance = unique_instance
    if self.unique_instance: self.create_instance()
    self.passo = 0
    self.iter = 0
    self.ultima_acao = None
    self.ultima_recompensa = None
    

  def normalize_state(self, state):
    
    temp_state = state.copy()

    for i in range(SIZE):
      temp_state[i] = temp_state[i]/(self.MaxE06)

    for i in range(SIZE, 2*SIZE):
      temp_state[i] = temp_state[i]/(self.MaxEUBU)

    for i in range(2*SIZE, 3*SIZE):
      temp_state[i] = temp_state[i]/(self.MaxCon)

    for i in range(3*SIZE, 4*SIZE):
      temp_state[i] = temp_state[i]/(self.MaxUbu)

    return np.clip(np.array(temp_state)*2 - 1, self.observation_space.low, self.observation_space.high) 

  def reset(self, seed=None, options=None):
    """
    Important: the observation must be a numpy array
    :return: (np.array) 
    """
    if not self.unique_instance: self.create_instance()
    self.seedNum = seed
    info = {}
    self.use_instance()
    self.passo = 0
    self.nBatchsP = 0
    self.nBatchsA = 0
    self.status = -1
    self.ultima_acao = None
    self.ultima_recompensa = 0
    self.BombeamentoPolpa = [0]*SIZE
    self.fo_value, self.estoque_eb06, self.estoque_ubu, self.prod_concentrador, self.prod_usina = self.evaluate(self.BombeamentoPolpa)
    self.FO_Inicial = self.fo_value
    self.FO_Best = self.FO_Inicial
    return self.normalize_state(self.estoque_eb06 + self.estoque_ubu + self.disp_conc + self.disp_usina), info

  def step(self, action):
    
    FIM = SIZE
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
        self.nBatchsP = 0
        self.nBatchsA += 0    

    if Erro == False:
      self.BombeamentoPolpa[self.passo] = action[0]
      self.passo +=1
      
      self.FO_anterior = sum(self.prod_usina)

      self.fo_value, self.estoque_eb06, self.estoque_ubu, self.prod_concentrador, self.prod_usina = self.evaluate(self.BombeamentoPolpa)
      
      self.FO = self.fo_value

      if self.FO > self.FO_Best:
        self.FO_Best = self.FO_Inicial

      recompensa = float(self.FO - self.FO_anterior)

      self.ultima_acao = action


    self.ultima_recompensa = recompensa
   
    terminou_episodio = bool(self.passo == FIM)
    truncated = False

    # Optionally we can pass additional info, we are not using that for now
    info = {}

    return self.normalize_state(self.estoque_eb06 + self.estoque_ubu + self.disp_conc + self.disp_usina), recompensa, terminou_episodio, truncated, info
  
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

class RandomAgent():
  def __init__(self, env):
    self.env = env

  def predict(self, observation, deterministic=False):
    # ignora o parâmetro deterministic
    return self.env.action_space.sample(), None

def evaluate_results(model, env, seeds, render=False):
  results = []
  FO_bests = []
  c=1
  
  for seed in seeds:
    env.seed(seed)
    obs, info = env.reset()
    if render: env.render()
    done = False
    while not done:
      print('++++++++++++++++++'+str(c))
      action, _ = model.predict(obs, deterministic=True)
      print(obs)
      print(action)
      obs, reward, done, tr, info = env.step(action)
      if render: env.render()
      c=c+1
    
    results.append({'FO_Best': env.FO_Best, 'FO_inicial': env.FO_inicial})  
    FO_bests.append(env.FO_Best)
  
  return np.average(FO_bests), results

def run_ppo():

  print("===== CHECANDO AMBIENTE =====")

  env = CustomizedEnv(unique_instance=UNIQUE_INSTANCE, seed=UNIQUE_INSTANCE_SEED)
  # If the environment don't follow the interface, an error will be thrown
  #check_env(env, warn=True)

  print()
  print("===== DEMONSTRANDO AMBIENTE =====")
  print(f"{env.observation_space=}")
  print(f"{env.action_space=}")
  print(f"{env.action_space.sample()=}")
  print("===== TREINANDO COM POO =====")

  if UNIQUE_INSTANCE:
    n_envs = 1
  else:
    n_envs = 4

  # Cria um ambiente vetorizado considerando 4 ambientes (atores do PPO)
  vec_env = make_vec_env(CustomizedEnv, n_envs=n_envs, env_kwargs={'unique_instance': UNIQUE_INSTANCE, 'seed': UNIQUE_INSTANCE_SEED})

  # Usa um adaptador para normalizar as recompensas
  vec_env = VecNormalize(vec_env, training=True, norm_obs=False, norm_reward=True, clip_reward=10.0)

  if USAR_LOG_TENSORBOARD:
    tensorboard_log="./ppo_tensorboard/"
  else:
    tensorboard_log=None

  # Train the agent
  model = PPO('MlpPolicy', vec_env, verbose=1, tensorboard_log=tensorboard_log)
  model.learn(total_timesteps=TRAINING_STEPS)
  model.save("ppo_Mineroduto")

  print("===== DEMONSTRANDO RESULTADO =====")
    
  FIXED_EVALUATION_SEEDS = [51, 312, 4, 207, 461, 394, 859, 639, 138, 727]

  if UNIQUE_INSTANCE:  
    qtde_avaliacoes = 1
  else:
    qtde_avaliacoes = 10

  #OLHAR COMO FIXAR SEED NO AMBIENTE
  EVALUATION_SEEDS = FIXED_EVALUATION_SEEDS[:qtde_avaliacoes]

  PPO_avg_FO_bests, PPO_results = evaluate_results(model, env, EVALUATION_SEEDS, render=False)
  #random_avg_FO_bests, random_results = evaluate_results(RandomAgent(env), env, SEMENTES_AVALIACAO, render=False)
  myfile = open("resultados.txt", "w")
  myfile.write(str(PPO_avg_FO_bests) +"\n")
  myfile.close()

  print(f"Done! Resultado: {env.FO_Best} (inicial: {env.FO_inicial})")