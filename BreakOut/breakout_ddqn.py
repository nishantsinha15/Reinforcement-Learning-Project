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

# done save model
# todo Initialize replay memory
# todo remove deque
# done merge this pipeline with taking pixels as input
# done create a state class?
# done keep the target network as a part of the model class


EPISODES = 100000
file_name = 'breakout_ddqn_v1'


class StackedFrame:
    def __init__(self, images):
        self.images = list(images)

    def get_input_layer(self):
        ret = [(self.images[0]).reshape((105, 80, 1)) / 255.0,
                           (self.images[1]).reshape((105, 80, 1)) / 255.0,
                           (self.images[2]).reshape((105, 80, 1)) / 255.0,
                        (self.images[3]).reshape((105, 80, 1)) / 255.0]
        ret = np.asarray(ret).reshape(105,80,4)
        ret = np.expand_dims(ret, axis=0)
        return ret

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
        self.target_model = self._build_model()

    '''
    Further, whenever we call load_model(remember, we needed it for the target network), 
    we will need to pass custom_objects={'huber_loss': huber_loss as an argument to tell Keras where to find huber_loss.
    '''

    # Note: pass in_keras=False to use this function with raw numbers of numpy arrays for testing
    def huber_loss(self, a, b, in_keras=True):
        error = a - b
        quadratic_term = error * error / 2
        linear_term = abs(error) - 1 / 2
        use_linear_term = (abs(error) > 1.0)
        if in_keras:
            # Keras won't let us multiply floats by booleans, so we explicitly cast the booleans to floats
            use_linear_term = K.cast(use_linear_term, 'float32')
        return use_linear_term * linear_term + (1 - use_linear_term) * quadratic_term

    def _build_model(self):
        model = Sequential()
        model.add(Conv2D(32, kernel_size=8, strides=4, activation='relu', input_shape=(105, 80, 4)))
        model.add(Conv2D(64, kernel_size=4, strides=2, activation='relu'))
        model.add(Conv2D(64, kernel_size=3, strides=1, activation='relu'))
        model.add(Flatten())
        model.add(Dense(512, input_dim=self.state_size, activation='relu'))
        model.add(Dense(self.action_size))
        model.compile(loss=self.huber_loss, optimizer=Adam(lr=self.learning_rate), metrics=['mae'])
        return model

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        if random.random() < 0.5:
            act_values = self.model.predict(state.get_input_layer())
        else:
            act_values = self.target_model.predict(state.get_input_layer())
        # print(act_values)
        # print("Focus = ",type(act_values), (len(act_values)), type(act_values[0][0]) )
        return np.argmax(act_values[0])  # returns action

    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)
        coin_toss = random.random() < 0.5
        # if coin_toss:
        #     m1 = self.model
        #     m2 = self.target_model
        # else:
        #     m1 = self.target_model
        #     m2 = self.model
        if coin_toss:
            for state, action, reward, next_state, done in minibatch:
                target = reward
                if not done:
                    best_action = -1
                    val = -100000000
                    temp_val = self.model.predict(next_state.get_input_layer())[0]
                    for a in range(self.action_size):
                        if temp_val[a] > val:
                            val = temp_val[a]
                            best_action = a
                    '''check understading '''
                    target = (reward + self.gamma * self.target_model.predict(next_state.get_input_layer())[0][
                        best_action])  # Double Q learning
                target_f = self.model.predict(state.get_input_layer())
                target_f[0][action] = target
                '''check understading '''
                self.model.fit(state.get_input_layer(), target_f, epochs=1, verbose=0)
        else:
            for state, action, reward, next_state, done in minibatch:
                target = reward
                if not done:
                    best_action = -1
                    val = -100000000
                    temp_val = self.target_model.predict(next_state.get_input_layer())[0]
                    for a in range(self.action_size):
                        if temp_val[a] > val:
                            val = temp_val[a]
                            best_action = a
                    '''check understading '''
                    target = (reward + self.gamma * self.model.predict(next_state.get_input_layer())[0][
                        best_action])  # Double Q learning
                target_f = self.target_model.predict(state.get_input_layer())
                target_f[0][action] = target
                '''check understading '''
                self.target_model.fit(state.get_input_layer(), target_f, epochs=1, verbose=0)


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
    c = 0
    # agent.load(file_name + "model.h5")
    done = False
    batch_size = 32
    recent_average = deque(maxlen=10)
    max_score = 0
    for e in range(EPISODES):
        state = env.reset()
        state = preprocess(state)
        mystate = deque(maxlen=4)
        mystate.append(state)
        prev_state = StackedFrame([state for i in range(4)])
        curr_state = StackedFrame([state for i in range(4)])
        # state = np.reshape(state, [1, state_size])
        # state = preprocess(state).reshape((105, 80, 1)) / 255.0
        # state = np.expand_dims(state, axis=0)
        total_reward = 0
        for time in range(500000):
            c += 1
            # env.render()
            action = agent.act(curr_state)
            # action = env.action_space.sample()
            next_state, reward, done, _ = env.step(action)
            next_state = preprocess(next_state)
            total_reward += reward
            reward = reward if not done else -1
            print(reward)
            mystate.append(next_state)
            if len(mystate) == 4:
                curr_state = StackedFrame(mystate)
                agent.remember(prev_state, action, reward, curr_state, done)
                prev_state = curr_state

            state = next_state

            if done:
                print(total_reward, time)
                if total_reward > max_score: max_score = total_reward
                print("episode: {}/{}, score: {}, e: {:.2}, c = {}, max_score = {}"
                      .format(e, EPISODES, total_reward, agent.epsilon, c, max_score))
                recent_average.append(total_reward)
                av = sum(recent_average) / len(recent_average)
                print(" Recent Average = ", av)
                eVSs.append((e + 1, av))
                break

            if len(agent.memory) > batch_size:
                agent.replay(batch_size)

            if c % 5000 == 0:
                agent.target_model.set_weights(agent.model.get_weights())
                print("Updated the target model")

        if agent.epsilon > agent.epsilon_min: agent.epsilon = agent.epsilon_decay * c + 1

        if e % 50 == 0:
            agent.save(file_name + "model.h5")
            plot(eVSs)
