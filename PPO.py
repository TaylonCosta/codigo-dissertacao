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
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from sb3_contrib.common.wrappers import ActionMasker
from sb3_contrib.ppo_mask import MaskablePPO
from sb3_contrib.common.maskable.utils import get_action_masks
from datetime import datetime

UNIQUE_INSTANCE = True
UNIQUE_INSTANCE_SEED = 51
TRAINING_STEPS = 250000
USAR_LOG_TENSORBOARD = (
    True  # Para ver o log, execute o comando: tensorboard --logdir ./ppo_tensorboard/
)
SEMENTE = 5
RANDOM = False
SIZE = 1
SIZE_BOMBEAMENTO = 168
SAVE = True
LOAD = False


if not UNIQUE_INSTANCE:
    UNIQUE_INSTANCE_SEED = None


class CustomizedEnv(gymnasium.Env):

    def convert_bombeamento_list(
        self,
        BombeamentoPolpa,
    ):
        bombeamento = {produto: {} for produto in self.prdt_conc}
        cont = 0
        dias = [f"d{dia+1:02d}" for dia in range(7)]
        horas = [f"h{hora+1:02d}" for hora in range(24)]
        horas_D14 = [f"{dia}_{hora}" for dia in dias for hora in horas]
        for i in horas_D14:
            if BombeamentoPolpa[cont] == 1:
                bombeamento["PRDT_C1"].update({i: 1})
                bombeamento["PRDT_C2"].update({i: 0})
                bombeamento["PRDT_C3"].update({i: 0})
            elif BombeamentoPolpa[cont] == 2:
                bombeamento["PRDT_C2"].update({i: 1})
                bombeamento["PRDT_C1"].update({i: 0})
                bombeamento["PRDT_C3"].update({i: 0})
            elif BombeamentoPolpa[cont] == 3:
                bombeamento["PRDT_C3"].update({i: 1})
                bombeamento["PRDT_C1"].update({i: 0})
                bombeamento["PRDT_C2"].update({i: 0})
            else:
                bombeamento["PRDT_C1"].update({i: 0})
                bombeamento["PRDT_C2"].update({i: 0})
                bombeamento["PRDT_C3"].update({i: 0})
            cont += 1
        return bombeamento

    def initialize(self, rand):
        if rand:
            self.estoque_eb06_inicial = random.randint(0, 10000)
            self.estoque_ubu_inicial = random.randint(0, 10000)
            self.disp_conc_inicial = [random.randint(0, 10000)] * 24
            self.disp_usina_inicial = [random.randint(0, 10000)] * 24
            self.MaxE06 = random.randint(0, 10000)
            self.MaxEUBU = random.randint(0, 10000)
            self.AguaLi = 4
            self.AguaLs = 7
            self.PolpaLi = 10
            self.PolpaLs = 15

        else:
            (
                self.estoque_eb06_inicial,
                self.estoque_ubu_inicial,
                self.disp_conc_inicial,
                self.disp_usina_inicial,
                self.MaxE06,
                self.MaxEUBU,
                self.AguaLi,
                self.AguaLs,
                self.PolpaLi,
                self.PolpaLs,
                self.vazao_bombas_eb06,
                self.prdt_conc,
                self.prdt_usina,
            ) = self.inital_data_ppo

        return (
            self.estoque_eb06_inicial,
            self.estoque_ubu_inicial,
            self.disp_conc_inicial,
            self.disp_usina_inicial,
            self.MaxE06,
            self.MaxEUBU,
            self.AguaLi,
            self.AguaLs,
            self.PolpaLi,
            self.PolpaLs,
            self.vazao_bombas_eb06,
            self.prdt_conc,
            self.prdt_usina,
        )

    def evaluate(self, BombeamentoPolpa, passo, data):
        L = Learning(self.convert_bombeamento_list(BombeamentoPolpa), passo, data)
        status, estoque_eb06, estoque_ubu, prod_concentrador, prod_usina = (
            L.solve_model()
        )
        return status, estoque_eb06, estoque_ubu, prod_concentrador, prod_usina

    def create_instance(self):
        # randomness = 0.2
        # RANDOM = False
        # if random.random() < randomness:
        #     RANDOM = True
        (
            self.estoque_eb06_inicial,
            self.estoque_ubu_inicial,
            self.disp_conc_inicial,
            self.disp_usina_inicial,
            self.MaxE06,
            self.MaxEUBU,
            self.AguaLi,
            self.AguaLs,
            self.PolpaLi,
            self.PolpaLs,
            self.vazao_bombas_eb06,
            self.prdt_conc,
            self.prdt_usina,
        ) = self.initialize(RANDOM)
        self.MaxCon = self.disp_conc_inicial
        self.MaxUbu = self.disp_usina_inicial

    def use_instance(self):
        self.estoque_eb06 = self.estoque_eb06_inicial  # Volume
        self.estoque_ubu = self.estoque_ubu_inicial  # Volume
        self.disp_conc = self.disp_conc_inicial # Produção Max Hora
        self.disp_usina = self.disp_usina_inicial  # Produção Max Hora

    def __init__(self, unique_instance=False, seed=None):
        super(CustomizedEnv, self).__init__()

        print(f"Criando ambiente: {unique_instance=} {seed=}")

        # self.binary_array = np.zeros(4, dtype=int)
        size = int(SIZE)  # int(2*TAMANHO)
        # Define action and observation space
        n_actions = 1
        # self.observation_space = spaces.Box(len(self.Lista0)*[tam]+len(self.Lista0)*[self.Dmax])
        load_data = Load_data()
        self.inital_data_ppo = load_data.load_simplified_data_ppo()
        self.data = load_data.load()
        self.unique_instance = unique_instance
        if self.unique_instance:
            self.create_instance()
        self.n_produtos_conc = len(self.prdt_conc)
        self.n_produtos_usina = len(self.prdt_usina)
        self.action_space = spaces.Discrete(self.n_produtos_conc + 1)
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(4 * size * self.n_produtos_conc,),
            dtype=np.float64,
        )
        self.seed(seed)
        self.passo = 0
        self.iter = 0
        self.cont_fo = 0
        self.cont_reward = 0
        self.ultima_acao = None
        self.ultima_recompensa = None
        self.Agua = 1
        self.Polpa = [1] * len(self.prdt_conc)

    def normalize_state(self, state):

        temp_state = state
        for i in range(SIZE * self.n_produtos_conc):
            temp_state[i] = temp_state[i] / (self.MaxE06)

        for i in range(SIZE * self.n_produtos_conc, 2 * SIZE * self.n_produtos_conc):
            temp_state[i] = temp_state[i] / (self.MaxEUBU)

        for i in range(
            2 * SIZE * self.n_produtos_conc, 3 * SIZE * self.n_produtos_conc
        ):
            temp_state[i] = temp_state[i] / (self.MaxCon)

        for i in range(
            3 * SIZE * self.n_produtos_conc, 4 * SIZE * self.n_produtos_conc
        ):
            temp_state[i] = temp_state[i] / (self.MaxUbu)

        return np.clip(
            np.array(temp_state) * 2 - 1,
            self.observation_space.low,
            self.observation_space.high,
        )

    def reset(self, seed=None, options=None):
        """
        Important: the observation must be a numpy array
        :return: (np.array)
        """
        if not self.unique_instance:
            self.create_instance()
        self.seedNum = seed
        info = {}
        self.state = []
        self.use_instance()
        self.passo = 0
        self.nBatchsP = 0
        self.nBatchsA = 0
        self.cont_fo = 0
        self.cont_reward = 0
        self.Agua = 0
        self.Polpa = [0] * len(self.prdt_conc)
        self.status = -1
        self.ultima_acao = None
        self.ultima_recompensa = 0
        self.BombeamentoPolpa = [0] * SIZE_BOMBEAMENTO
        (
            self.fo_value,
            self.estoque_eb06,
            self.estoque_ubu,
            self.prod_concentrador,
            self.prod_usina,
        ) = self.evaluate(self.BombeamentoPolpa, 0,self.data)

        for produto_conc in self.prdt_conc:
            self.state.append(self.estoque_eb06_inicial[produto_conc])
            self.state.append(self.estoque_ubu_inicial[produto_conc])
            self.state.append(self.prod_concentrador[produto_conc][1])
            self.state.append(self.prod_usina[produto_conc][1])
        self.FO_Inicial = self.fo_value
        self.FO_Best = self.FO_Inicial

        # checa se ha polpa suficiente para bombear o produto escolhido na action

        return self.normalize_state(self.state), info

    def step(self, action):
        FIM = SIZE_BOMBEAMENTO - 1
        self.Agua = 1
        self.Polpa = [1] * len(self.prdt_conc)
        self.actual_state = []
        # fixa o batch no tamanho minimo para apenas um produto:
        if self.nBatchsP == 0 and action != 0:
            if (
                self.passo + self.PolpaLi <= SIZE_BOMBEAMENTO - 1
                and self.nBatchsP + self.PolpaLi <= self.PolpaLs
            ):
                for i in range(self.passo, (self.passo + self.PolpaLi)):
                    self.BombeamentoPolpa[i] = action
                    self.passo += 1
                    self.nBatchsP += 1
            elif (
                not self.passo + self.PolpaLi <= SIZE_BOMBEAMENTO - 1
                and self.nBatchsP + self.PolpaLi <= self.PolpaLs
            ):
                for i in range(self.passo, SIZE_BOMBEAMENTO - 1):
                    self.BombeamentoPolpa[i] = action
                    self.passo += 1
                    self.nBatchsP += 1
            self.Agua = 1
            self.Polpa = [0] * len(self.prdt_conc)
            self.Polpa[action - 1] = 1
            self.nBatchsA = 0

        elif self.nBatchsA == 0 and action == 0:
            if (
                self.passo + self.AguaLi <= SIZE_BOMBEAMENTO - 1
                and self.nBatchsA + self.AguaLi <= self.AguaLs
            ):
                for i in range(self.passo, (self.passo + self.AguaLi)):
                    self.BombeamentoPolpa[i] = action
                    self.passo += 1
                    self.nBatchsA += 1
            elif (
                not self.passo + self.AguaLi <= SIZE_BOMBEAMENTO - 1
                and self.nBatchsA + self.AguaLi <= self.AguaLs
            ):
                for i in range(self.passo, SIZE_BOMBEAMENTO - 1):
                    self.BombeamentoPolpa[i] = action
                    self.passo += 1
                    self.nBatchsA += 1
            self.Agua = 1
            self.Polpa = [1] * len(self.prdt_conc)
            self.nBatchsP = 0

        elif (
            action != 0
            and self.nBatchsP >= self.PolpaLi
            and self.nBatchsP < self.PolpaLs
        ):
            self.BombeamentoPolpa[self.passo] = action
            self.Agua = 1
            self.Polpa = [0] * len(self.prdt_conc)
            self.Polpa[action - 1] = 1
            self.passo += 1
            self.nBatchsP += 1
            self.nBatchsA = 0

        elif (
            action == 0 and self.nBatchsA >= self.AguaLi and self.nBatchsA < self.AguaLs
        ):
            self.BombeamentoPolpa[self.passo] = action
            self.Agua = 1
            self.Polpa = [1] * len(self.prdt_conc)
            self.passo += 1
            self.nBatchsA += 1
            self.nBatchsP = 0

        terminou_episodio = bool(self.passo == FIM)

        self.FO_anterior = self.fo_value
        (
            self.fo_value,
            self.estoque_eb06,
            self.estoque_ubu,
            self.prod_concentrador,
            self.prod_usina,
        ) = self.evaluate(self.BombeamentoPolpa, self.passo, self.data)
        for produto_conc in self.prdt_conc:
            self.actual_state.append(self.estoque_eb06[produto_conc][self.passo])
            self.actual_state.append(self.estoque_ubu[produto_conc][self.passo])
            self.actual_state.append(self.prod_concentrador[produto_conc][self.passo])
            self.actual_state.append(self.prod_usina[produto_conc][self.passo])

        self.FO = self.fo_value

        if self.FO > self.FO_Best:
            self.FO_Best = self.FO

        recompensa = float(self.FO - self.FO_anterior)

        if self.FO == self.FO_anterior or self.ultima_recompensa == recompensa:
            self.cont_fo += 1
            self.cont_reward += 1

        if self.cont_fo == 30 or self.cont_reward == 30:
            terminou_episodio = bool(self.passo == FIM)
            self.reset()

        self.ultima_acao = action
        self.ultima_recompensa = recompensa



        truncated = False

        # Optionally we can pass additional info, we are not using that for now
        print(f"step {self.passo}")
        print(
            f"\tlast action: {self.ultima_acao}, FO: {self.FO}, Melhor FO: {self.FO_Best}"
        )
        print(f"\tbomb: {self.BombeamentoPolpa}")
        print(f"\treward: {self.ultima_recompensa}")
        info = {}

        return (
            self.normalize_state(self.actual_state),
            recompensa,
            terminou_episodio,
            truncated,
            info,
        )

    def render(self, mode="console"):
        if mode != "console":
            raise NotImplementedError()

        if self.passo > 0:
            print(f"Passo {self.passo}")
        else:
            print("Instância:")

        print(f"\tÚltima ação: {self.ultima_acao}, FO: {self.FO}")
        print(f"\tLista: {self.BombeamentoPolpa}")
        print(f"\tRecompensa: {self.ultima_recompensa}")

    def close(self):
        pass

    def seed(self, seed=None):
        self.rand_generator = np.random.RandomState(seed)
        self.action_space.seed(seed)

    def valid_action_mask(self):
        # self.mask= np.array([0, 0, 1, 0])
        cont = 0
        for produto_conc in self.prdt_conc:
            if (self.estoque_eb06[produto_conc][self.passo] + (self.PolpaLi* 
            (self.disp_conc_inicial - self.vazao_bombas_eb06)) < 0):
                self.Polpa[cont] = 0
                self.Agua = 1
            else:
                self.Polpa[cont] = 1
            cont += 1
        self.mask = np.array([self.Agua])
        for i in range(0, len(self.Polpa)):
            self.mask = np.append(self.mask, self.Polpa[i])
        return self.mask


class RandomAgent:
    def __init__(self, env):
        self.env = env

    def predict(self, observation, deterministic=False):
        # ignora o parâmetro deterministic
        return self.env.action_space.sample(), None


def mask_fn(env: gymnasium.Env) -> np.ndarray:
    return env.valid_action_mask()


def evaluate_results(model, env, seeds, render=False):
    results = []
    FO_bests = []

    for seed in seeds:
        env.seed(seed)
        obs, info = env.reset()
        if render:
            env.render()
        done = False
        while not done:
            env = ActionMasker(env, mask_fn)
            action_masks = get_action_masks(env)
            # action, _ = model.predict(obs, deterministic=True)
            # print(obs)
            print(action_masks)
            action, _ = model.predict(
                obs, action_masks=action_masks, deterministic=True
            )
            obs, reward, done, truncated, info = env.step(action)
            # obs, reward, done, tr, info = env.step(action)
            if render:
                env.render()

    results.append({"FO_Best": env.FO_Best, "FO_inicial": env.FO_Inicial})
    FO_bests.append(env.FO_Best)

    return np.average(FO_bests), results


def run_ppo():

    print("===== CHECANDO AMBIENTE =====")

    env = CustomizedEnv(unique_instance=UNIQUE_INSTANCE, seed=UNIQUE_INSTANCE_SEED)
    # If the environment don't follow the interface, an error will be thrown
    # check_env(env, warn=True)

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
    # env = ActionMasker(CustomizedEnv, n_envs=n_envs, env_kwargs={'unique_instance': UNIQUE_INSTANCE, 'seed': UNIQUE_INSTANCE_SEED})

    env = ActionMasker(env, mask_fn)

    # Usa um adaptador para normalizar as recompensas
    # vec_env = VecNormalize(vec_env, training=True, norm_obs=False, norm_reward=True, clip_reward=10.0)

    if USAR_LOG_TENSORBOARD:
        tensorboard_log = "./ppo_tensorboard/"
    else:
        tensorboard_log = None

    # Train the agent
    model = MaskablePPO(
        MaskableActorCriticPolicy, env, verbose=1, tensorboard_log=tensorboard_log
    ).learn(TRAINING_STEPS)
    if SAVE:
        model.save("model_ppo")

    if LOAD:
        model = MaskablePPO.load("model_ppo", env=env)
    # model.learn(total_timesteps=TRAINING_STEPS)
    # model.save("ppo_Mineroduto")

    print("===== DEMONSTRANDO RESULTADO =====")

    FIXED_EVALUATION_SEEDS = [51, 312, 4, 207, 461, 394, 859, 639, 138, 727]

    if UNIQUE_INSTANCE:
        qtde_avaliacoes = 1
    else:
        qtde_avaliacoes = 10

    # OLHAR COMO FIXAR SEED NO AMBIENTE
    EVALUATION_SEEDS = FIXED_EVALUATION_SEEDS[:qtde_avaliacoes]

    # PPO_avg_FO_bests, PPO_results = evaluate_results(
    #     model, env, EVALUATION_SEEDS, render=False
    # )
    # random_avg_FO_bests, random_results = evaluate_results(RandomAgent(env), env, SEMENTES_AVALIACAO, render=False)
    myfile = open("resultados.txt", "w")
    myfile.write(str(env.PPO_avg_FO_bests) + "\n")
    myfile.write(str(env.PPO_results))
    myfile.close()
    print(datetime.now())
    print(f"Done! Resultado: {env.FO_Best} (inicial: {env.FO_Inicial})")
