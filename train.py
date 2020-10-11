#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 任意一个主机对之间的单位时间的数据量（数据包的数目）
# 由A到B的平均时延
# A, B之间在每个路径的分割比

import argparse
from ns3gym import ns3env
from my_agent import *

parser = argparse.ArgumentParser(description = 'Start simulation script on/off')
parser.add_argument('--start', type = int, default = 1,
                    help = 'Start ns-3 simulation script 0/1, Default: 1')
parser.add_argument('--iterations', type = int, default = 1,
                    help = 'Number of iterations, Default: 1')
parser.add_argument('--learning_rate', type = float, default = 0.0002, 
                    help = 'Learning rate')
parser.add_argument('--gamma', type = float, default = 0.98)
parser.add_argument('--buffer_limit', type = int, default = 6000)
parser.add_argument('--rollout_len', type = int, default = 10)
parser.add_argument('--batch_size', type = int, default = 4)
parser.add_argument('--c', type = float, default = 1.5)
parser.add_argument('--possion_lambda', type = int, default = 4)
parser.add_argument('--clipping', type = float, default = 0.1)

args = parser.parse_args()
startSim = bool(args.start)
iterationNum = int(args.iterations)

port = 5555
simTime = 5 # seconds
stepTime = 0.5  # seconds
seed = 0
simArgs = {"--simTime": simTime,
           "--stepTime": stepTime,
           "--testArg": 123}
debug = False

env = ns3env.Ns3Env(port = port, stepTime = stepTime, startSim = startSim, 
    simSeed = seed, simArgs = simArgs, debug = debug)

# simpler:
#env = ns3env.Ns3Env()
env.reset()

ob_space = env.observation_space
ac_space = env.action_space
print("Observation space: ", ob_space,  ob_space.dtype)
print("Action space: ", ac_space, ac_space.dtype)

stepIdx = 0
currIt = 0

memory = ReplayBuffer(buffer_limit = args.buffer_limit)
model = ActorCritic()
optimizer = optim.Adam(model.parameters(), lr = args.learning_rate)

score = 0.0
print_interval = 20

try:
    while True:
        print("Start iteration: ", currIt)
        obs = env.reset()
        print("Step: ", stepIdx)
        print("---obs: ", obs)
        done = False
            
        while not done:
            stepIdx += 1
            print("Step: ", stepIdx)
            seq_data = []
            for t in range(args.rollout_len): 
                prob = model.pi(torch.from_numpy(obs).float())
                action = Categorical(prob).sample().item()
                s_prime, r, done, info = env.step(action)
                seq_data.append((obs, action, r / 100.0, prob.detach().numpy(), done))

                score += r
                obs = s_prime
                if done:
                    stepIdx = 0
                    break

            memory.put(seq_data)
            if memory.size() > 500:
                train(model, optimizer, memory, args.c, args.gamma, args.clipping, args.batch_size, on_policy = False)
                # 计算优先级
                # train(model, optimizer, memory, args.c, args.gamma, args.clipping, args.batch_size, on_policy = False, calculate_prio = True)
                # for i in range(np.random.poisson(args.possion_lambda)):
                #     train(model, optimizer, memory, args.c, args.gamma, args.clipping, args.batch_size)
                #     # 计算优先级
                #     train(model, optimizer, memory, args.c, args.gamma, args.clipping, args.batch_size, calculate_prio = True)

        currIt += 1
        if currIt == iterationNum:
            break
        if currIt % print_interval == 0 and currIt != 0:
            print("# of episode :{}, avg score : {:.1f}, buffer size : {}".format(n_epi, score/print_interval, memory.size()))
            score = 0.0

except KeyboardInterrupt:
    print("Ctrl-C -> Exit")
finally:
    env.close()
    print("Done")