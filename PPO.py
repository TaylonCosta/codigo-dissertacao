import numpy as np
import gym
from gym import spaces
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize
from stable_baselines3 import PPO
import itertools
from ai import Learning
import random
from PPO import Load_data

UNIQUE_INSTANCE = True
UNIQUE_INSTANCE_SEED = 51
TRAINING_STEPS = 500000
USAR_LOG_TENSORBOARD = True # Para ver o log, execute o comando: tensorboard --logdir ./ppo_tensorboard/
SEMENTE = 5
RANDOM = False
SIZE = 24

if not UNIQUE_INSTANCE:
   UNIQUE_INSTANCE_SEED = None

class CustomizedEnv(gym.Env):
  
  def initialize(rand):
    if rand:
      estoque_eb06_inicial = random.randint()
      estoque_ubu_inicial = random.randint()
      disp_conc_inicial = random.randint()
      disp_usina_inicial = random.randint()
      MaxE06 = random.randint()
      MaxEUBU = random.randint()
      AguaLi = random.randint()
      AguaLs = random.randint()
      PolpaLi = random.randint()
      PolpaLs = random.randint()

    else:
      load_data = Load_data()
      self.estoque_eb06_inicial, self.estoque_ubu_inicial, self.disp_conc_inicial, self.disp_usina_inicial, self.MaxE06, self.MaxEUBU, self.AguaLi, self.AguaLs, self.PolpaLi, self.PolpaLs = load_data.load_simplified_data_ppo()

  
  def evaluate(self, BombeamentoPolpa):
    estoque_eb06, estoque_ubu, prod_concentrador, prod_usina = Learning.solve_model(BombeamentoPolpa)
    return estoque_eb06, estoque_ubu, prod_concentrador, prod_usina


  def create_instance(self):
    self.estoque_eb06_inicial, self.estoque_ubu_inicial, self.disp_conc_inicial, self.disp_usina_inicial, self.MaxE06, self.MaxEUBU, self.AguaLi, self.AguaLs, self.PolpaLi, self.PolpaLs = self.initialize(RANDOM)
    self.MaxCon = max(self.disp_conc_inicial)
    self.MaxUbu= max(self.disp_usina_inicial)

  def use_instance(self):
    self.estoque_eb06 = self.estoque_eb06_inicial.copy() #Volume 
    self.estoque_ubu = self.estoque_ubu_inicial.copy() #Volume
    self.disp_conc = self.disp_conc_inicial.copy() #Produção Max Hora 
    self.disp_usina = self.disp_usina_inicial.copy() #Produção Max Hora


  def __init__(self, unique_instance=False, seed=None):
    super(CustomizedEnv, self).__init__()

    print(f"Criando ambiente: {unique_instance=} {seed=}" )  
    
    size = int(SIZE) #int(2*TAMANHO)
    # Define action and observation space
    n_actions = 2
    self.action_space = spaces.MultiBinary(n_actions)
    #self.observation_space = spaces.Box(len(self.Lista0)*[tam]+len(self.Lista0)*[self.Dmax])
    self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(4*size), dtype=np.float64)

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
      temp_state[i] = temp_state[i]/(self.disp_usina)

    return np.clip(np.array(temp_state)*2 - 1, self.observation_space.low, self.observation_space.high) 

  def reset(self):
    """
    Important: the observation must be a numpy array
    :return: (np.array) 
    """
    if not self.unique_instance: self.create_instance()

    self.use_instance()
    self.passo = 0
    self.nBatchsP = 0
    self.nBatchsA = 0
    self.ultima_acao = None
    self.ultima_recompensa = 0
    self.BombeamentoPolpa = [0]*SIZE
    self.estoque_eb06, self.estoque_ubu, self.prod_concentrador, self.prod_usina = self.evaluate(self.BombeamentoPolpa)
    self.FO_Inicial = sum(self.prod_usina)
    self.FO_Best = self.FO_Inicial
    return self.normalize_state(self.estoque_eb06 + self.estoque_ubu + self.disp_conc + self.disp_usina)
  
self.AguaLi, self.AguaLs, self.PolpaLi, self.PolpaLs
  
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
      self.BombeamentoPolpa[self.passo] = action
      self.passo +=1
      
      self.FO_anterior = sum(self.prod_usina)

      self.estoque_eb06, self.estoque_ubu, self.prod_concentrador, self.prod_usina = self.evaluate(self.BombeamentoPolpa)
      
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

def run_ppo():
  print("===== CHECANDO AMBIENTE =====")

  env = CustomizedEnv(unique_instance=UNIQUE_INSTANCE, seed=UNIQUE_INSTANCE_SEED)
  # If the environment don't follow the interface, an error will be thrown
  check_env(env, warn=True)

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
  vec_env = make_vec_env(CustomizedEnv, n_envs=n_envs, env_kwargs={'unique_instace': UNIQUE_INSTANCE, 'seed': UNIQUE_INSTANCE_SEED})

  # Usa um adaptador para normalizar as recompensas
  vec_env = VecNormalize(vec_env, training=True, norm_obs=False, norm_reward=True, clip_reward=10.)

  if USAR_LOG_TENSORBOARD:
    tensorboard_log="./ppo_tensorboard/"
  else:
    tensorboard_log=None

  # Train the agent
  model = PPO('MlpPolicy', vec_env, verbose=1, tensorboard_log=tensorboard_log).learn(TRAINING_STEPS)

  model.save("ppo_Mineroduto")

  #model = PPO.load("ppo_Routing", env=env)

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