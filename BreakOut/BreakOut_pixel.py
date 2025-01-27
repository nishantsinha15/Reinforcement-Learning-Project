import random
import gym
import numpy as np
from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import sgd, Adam
import matplotlib.pyplot as plt
from keras.layers import Dense, Conv2D, Flatten

from keras import backend as K

# todo save model
# todo Initialize replay memory
# todo remove deque
# todo merge this pipeline with taking pixels as input


'''
Further, whenever we call load_model(remember, we needed it for the target network), 
we will need to pass custom_objects={'huber_loss': huber_loss as an argument to tell Keras where to find huber_loss.
'''


# Note: pass in_keras=False to use this function with raw numbers of numpy arrays for testing
def huber_loss(a, b, in_keras=True):
    error = a - b
    quadratic_term = error * error / 2
    linear_term = abs(error) - 1 / 2
    use_linear_term = (abs(error) > 1.0)
    if in_keras:
        # Keras won't let us multiply floats by booleans, so we explicitly cast the booleans to floats
        use_linear_term = K.cast(use_linear_term, 'float32')
    return use_linear_term * linear_term + (1 - use_linear_term) * quadratic_term


EPISODES = 100000
file_name = 'breakout'


def to_grayscale(img):
    return np.mean(img, axis=2).astype(np.uint8)


def downsample(img):
    return img[::2, ::2]


def preprocess(img):
    return to_grayscale(downsample(img))


def plot(data):
    x = []
    y = []
    for i, j in data:
        x.append(i)
        y.append(j)
    plt.plot(x, y)
    plt.savefig(file_name + '.png')


class DeepQAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=20000)
        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_min = 0.1
        self.epsilon_decay = -(9 / 10000000)
        self.learning_rate = 0.00025
        self.model = self._build_model()

    def _build_model(self):
        model = Sequential()
        model.add(Conv2D(16, kernel_size=8, strides=4, activation='relu', input_shape = (105, 80, 1)))
        model.add(Conv2D(32, kernel_size=4, strides = 2, activation='relu'))
        model.add(Flatten())
        model.add(Dense(256,  activation='relu'))
        model.add(Dense(self.action_size))
        model.compile(loss=huber_loss, optimizer=Adam(lr=self.learning_rate), metrics=['mae'])
        return model

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        act_values = self.model.predict(state)
        # print(act_values)
        # print("Focus = ",type(act_values), (len(act_values)), type(act_values[0][0]) )
        return np.argmax(act_values[0])  # returns action

    def replay(self, batch_size, agent2):
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            temp = agent2.model.predict(next_state)
            if not done:
                target = (reward + self.gamma *
                          np.amax(agent2.model.predict(next_state)[0]))
            target_f = self.model.predict(state)  # What does this return? Ans type = [[0.08708638 0.4333976 ]]
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=0)

    def load(self, name):
        self.model.load_weights(name)

    def save(self, name):
        self.model.save_weights(name)


if __name__ == "__main__":
    eVSs = deque(maxlen=1000)
    env = gym.make('Breakout-v0')
    state_size = env.observation_space.shape[0]
    action_size = env.action_space.n
    agent = DeepQAgent(state_size, action_size)
    agent2 = DeepQAgent(state_size, action_size)
    c = 0
    # agent.load(file_name + "model.h5")
    done = False
    batch_size = 32
    recent_average = deque(maxlen=10)

    for e in range(EPISODES):
        state = env.reset()
        # state = np.reshape(state, [1, state_size])
        state =  preprocess(state).reshape((105, 80, 1))/255.0
        state = np.expand_dims(state, axis = 0)
        total_reward = 0
        for time in range(500):
            c += 1
            # env.render()
            action = agent.act(state)
            next_state, reward, done, _ = env.step(action)
            total_reward += reward
            reward = reward if not done else -1
            next_state = preprocess(next_state).reshape((105, 80, 1))/255.0
            next_state = np.expand_dims(next_state, axis=0)
            agent.remember(state, action, reward, next_state, done)
            state = next_state
            # print(state.shape)
            if done:
                print("episode: {}/{}, score: {}, e: {:.2}, c = {}"
                      .format(e, EPISODES, total_reward, agent.epsilon, c))
                recent_average.append(total_reward)
                av = sum(recent_average) / len(recent_average)
                print(" Recent Average = ", av)
                eVSs.append((e + 1, av))
                break

            if len(agent.memory) > batch_size and c % 4 == 0:
                agent.replay(batch_size, agent2)

            if c % 10000 == 0:
                agent2.model.set_weights(agent.model.get_weights())
                print("Updated the target model")

        if agent.epsilon > agent.epsilon_min: agent.epsilon = agent.epsilon_decay * c + 1

        # if e % 10 == 0:
        #     plot(eVSs)
        #
        # if e % 50 == 0:
        #     agent.save(file_name + "model.h5")
