__author__ = 'alibaba'
__date__ = '2018/11/19'

from a_secure_mobile_crowdsensing_game_with_drl.model import *
from a_secure_mobile_crowdsensing_game_with_drl.ddqn_onedim.dqn import *
import os
import matplotlib.pyplot as plt
import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

if not os.path.exists('img'):
    os.makedirs('img')

if not os.path.exists('data'):
    os.makedirs('data')
# 初始化 平台和用户的基本参数
mcs = MCSAgent(range(0, 51, 2))
user1 = UserAgent(range(0, 11, 1),
                  [1, 10],
                  [0.1, 0.9],
                  0.9,
                  5,
                  [0, 1, 2, 3, 4, 5],
                  [0.02, 0.04, 0.3, 0.3, 0.3, 0.04],
                  np.arange(0, 5.5, 0.5))
user2 = UserAgent(range(0, 11, 1),
                  [1, 10],
                  [0.1, 0.9],
                  0.9,
                  5,
                  [0, 1, 2, 3, 4, 5],
                  [0.02, 0.04, 0.3, 0.3, 0.3, 0.04],
                  np.arange(0, 5.5, 0.5))

RL_user2 = DeepQNetwork("user2")
RL_user1 = DeepQNetwork("user1")
RL = DeepQNetwork("mcs")
# 初始化程序变量
max_episode = 200
max_step = 1500
learn_episode = 200
memory_size = 50
beta = 10  # effort贡献率


def game():
    utility_mcs = [[0 for _ in range(max_episode)] for _ in range(max_step)]
    utility_user1 = [[0 for _ in range(max_episode)] for _ in range(max_step)]
    utility_user2 = [[0 for _ in range(max_episode)] for _ in range(max_step)]
    action_mcs = [[0 for _ in range(max_episode)] for _ in range(max_step)]
    action_user1 = [[0 for _ in range(max_episode)] for _ in range(max_step)]
    action_user2 = [[0 for _ in range(max_episode)] for _ in range(max_step)]
    action_mcs_hist = np.zeros(len(mcs.actions))
    action_user1_hist = np.zeros(len(user1.actions))
    action_user2_hist = np.zeros(len(user2.actions))
    action_mcs_list = list()
    action_user1_list = list()
    action_user2_list = list()
    cost_user1 = [[0 for _ in range(max_episode)] for _ in range(max_step)]
    cost_user2 = [[0 for _ in range(max_episode)] for _ in range(max_step)]
    for episode in range(max_episode):
        print('episode', episode, ':')
        RL.DataList = []
        RL_user1.DataList = []
        RL_user2.DataList = []
        # 平台选择一个action即支付的基础值，用户选择一个action和snr，用作系统的初始化动作和状态
        mcs_action = mcs.select_action()
        mcs_action_index = mcs.get_action_index(mcs_action)
        payment = mcs.get_payment_layer(mcs_action, 11, 0.5)
        user1_snr = user1.select_snr()
        user1_snr_index = user1.get_snr_index(user1_snr)
        user2_snr = user2.select_snr()
        user2_snr_index = user2.get_snr_index(user2_snr)
        user1_action = user1.select_action()
        user1_action_index = user1.get_action_index(user1_action)
        user2_action = user2.select_action()
        user2_action_index = user2.get_action_index(user2_action)
        for step in range(max_step):
            if step <= memory_size:
                # 组合状态
                mcs_state = str([user1_action_index, user2_action_index])
                user1_state = str([mcs_action_index, user1_snr_index])
                user2_state = str([mcs_action_index, user2_snr_index])
                user1_action = user1.select_action()
                user1_action_index = user1.get_action_index(user1_action)
                user2_action = user2.select_action()
                user2_action_index = user2.get_action_index(user2_action)
                mcs_action = mcs.select_action()
                mcs_action_index = mcs.get_action_index(mcs_action)
                payment = mcs.get_payment_layer(mcs_action, 11, 0.5)
            if step > memory_size:
                # for i in range(learn_episode):
                RL.learn()
                RL_user1.learn()
                RL_user2.learn()

                # 组合状态
                mcs_state = str([user1_action_index, user2_action_index])
                user1_state = str([mcs_action_index, user1_snr_index])
                user2_state = str([mcs_action_index, user2_snr_index])
                user1_action_index = RL_user1.select_action(mcs_state, user1_state, user2_state)
                user1_action = user1.get_action_by_index(user1_action_index)
                user2_action_index = RL_user2.select_action(mcs_state, user1_state, user2_state)
                user2_action = user2.get_action_by_index(user2_action_index)
                mcs_action_index = RL.select_action(mcs_state, user1_state, user2_state)
                mcs_action = mcs.get_action_by_index(mcs_action_index)

            # 获取reward
            r_user1 = payment[user1_action_index] - user1.select_cost_by_index(
                user1_action_index) * user1_action / user1.get_snr_by_index(user1_snr_index)
            r_user2 = payment[user2_action_index] - user2.select_cost_by_index(
                user2_action_index) * user2_action / user2.get_snr_by_index(user2_snr_index)
            r_mcs = beta * (user2.get_action_by_index(
                user2_action_index) + user1.get_action_by_index(
                user1_action_index)) - payment[user1_action_index] - payment[user2_action_index]

            user1_speed = user1.select_speed()
            user2_speed = user2.select_speed()
            next_snr1, next_snr_prob1 = user1.get_snr_prob(user1_speed, user1_snr)
            next_snr2, next_snr_prob2 = user2.get_snr_prob(user2_speed, user2_snr)
            user1_snr_index = user1.get_snr_index(next_snr1)
            user2_snr_index = user2.get_snr_index(next_snr2)
            # 获取下一状态
            _mcs_state = str([user1_action_index, user2_action_index])
            _user1_state = str([mcs_action_index, user1_snr_index])
            _user2_state = str([mcs_action_index, user2_snr_index])

            # 存储四元组
            RL.store_transition(mcs_state, user1_state, user2_state, mcs_action_index, user1_action_index,
                                user2_action_index, r_mcs, r_user1, r_user2, _mcs_state, _user1_state, _user2_state)
            RL_user1.store_transition(mcs_state, user1_state, user2_state, mcs_action_index, user1_action_index,
                                        user2_action_index, r_mcs, r_user1, r_user2, _mcs_state, _user1_state,
                                        _user2_state)
            RL_user2.store_transition(mcs_state, user1_state, user2_state, mcs_action_index, user1_action_index,
                                        user2_action_index, r_mcs, r_user1, r_user2, _mcs_state, _user1_state,
                                        _user2_state)

            # 参数存储：效用值
            utility_mcs[step][episode] = r_mcs
            utility_user1[step][episode] = r_user1
            utility_user2[step][episode] = r_user2
            # 参数存储：动作值
            action_mcs[step][episode] = mcs_action
            action_user1[step][episode] = user1_action
            action_user2[step][episode] = user2_action
            # 参数存储: 消耗值
            cost_user1[step][episode] = user1.select_cost_by_index(user1_action_index)
            cost_user2[step][episode] = user1.select_cost_by_index(user2_action_index)
            # 参数存储: 动作数量值
            action_user1_hist[user1_action_index] += 1
            action_user2_hist[user2_action_index] += 1
            action_mcs_hist[mcs_action_index] += 1

            action_mcs_list.append(mcs_action_index)
            action_user1_list.append(user1_action_index)
            action_user2_list.append(user2_action_index)

    # utility的平均趋势
    avu_mcs = np.sum(utility_mcs, axis=1)/max_episode
    avu_mcs = avu_mcs.T
    avu_user1 = np.sum(utility_user1, axis=1)/max_episode
    avu_user1 = avu_user1.T
    avu_user2 = np.sum(utility_user2, axis=1)/max_episode
    avu_user2 = avu_user2.T
    avc_user1 = np.sum(cost_user1, axis=1)/max_episode
    avc_user1 = avc_user1.T
    avc_user2 = np.sum(cost_user2, axis=1)/max_episode
    avc_user2 = avc_user2.T
    # 画图 两个汽车的消耗值
    plt.figure(0)
    plt.plot(range(max_step), avc_user1, label='Energy consumption of the 1th vehicle')
    plt.plot(range(max_step), avc_user2, label='Energy consumption of the 2th vehicle')
    plt.xlabel('Time slot')
    plt.ylabel('Energy consumption of the vehicle')
    plt.legend(shadow=True)
    plt.savefig(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'img', 'consumption.png')))
    plt.close()
    # 画图 汽车和服务器的效用值
    plt.figure(1)
    plt.subplot(221)
    plt.ylabel('Utility of the vehicle')
    plt.plot(range(max_step), avu_user1)
    plt.subplot(222)
    # plt.ylabel('Utility of the vehicle')
    plt.plot(range(max_step), avu_user2)
    plt.subplot(212)
    plt.xlabel('Time Slot')
    plt.ylabel('Utility of the mcs')
    plt.plot(range(max_step), avu_mcs)
    plt.savefig(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'img', 'utility.png')))
    plt.tight_layout()
    plt.close()
    # action的平均趋势
    ava_mcs = np.sum(action_mcs, axis=1) / max_episode
    ava_mcs = ava_mcs.T
    ava_user1 = np.sum(action_user1, axis=1) / max_episode
    ava_user1 = ava_user1.T
    ava_user2 = np.sum(action_user2, axis=1) / max_episode
    ava_user2 = ava_user2.T
    np.savetxt('data\\aca_mcs.txt', ava_mcs)
    np.savetxt('data\\ava_user1.txt', ava_user1)
    np.savetxt('data\\ava_user2.txt', ava_user2)

    # 画图 汽车的感知精度和服务器的支付
    plt.figure(2)
    plt.subplot(221)
    plt.ylabel('Sense Effort of the vehicle')
    plt.plot(range(max_step), ava_user1)
    plt.subplot(222)
    # plt.ylabel('Sense Effort of the vehicle')
    plt.plot(range(max_step), ava_user2)
    plt.subplot(212)
    plt.xlabel('Time Slot')
    plt.ylabel('Payment of the mcs')
    plt.plot(range(max_step), ava_mcs)
    plt.savefig(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'img', 'sense_effort.png')))
    plt.tight_layout()
    plt.close()

    # 画图 汽车和服务器的动作选择直方图
    plt.figure(3)
    plt.hist(action_mcs_list, bins=26, align='mid', facecolor='yellow', edgecolor='black')
    plt.title('The Histogram of mcs\'s action')
    plt.xlabel('The actions')
    plt.ylabel('The number of actions')
    plt.savefig(
        os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'img', 'mcs_action_hist.png')))
    np.savetxt('data\\action_mcs_hist.txt', action_mcs_hist)
    plt.close()
    plt.figure(4)
    plt.hist(action_user1_list, bins=11, align='mid', facecolor='yellow', edgecolor='black')
    plt.title('The Histogram of user1\'s action')
    # plt.plot(action_user1_hist)
    plt.xlabel('The actions')
    plt.ylabel('The number of actions')
    plt.savefig(
        os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'img', 'user1_action_hist.png')))
    np.savetxt('data\\action_user1_hist.txt', action_user1_hist)
    plt.close()
    plt.figure(5)
    plt.hist(action_user2_list, bins=11, align='mid', facecolor='yellow', edgecolor='black')
    plt.title('The Histogram of user2\'s action')
    plt.xlabel('The actions')
    plt.ylabel('The number of actions')
    plt.savefig(
        os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'img', 'user2_action_hist.png')))
    np.savetxt('data\\action_user2_hist.txt', action_user2_hist)
    plt.close()


if __name__ == '__main__':
    game()
