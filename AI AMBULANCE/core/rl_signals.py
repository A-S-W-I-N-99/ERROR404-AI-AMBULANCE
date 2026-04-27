import random
import json
import os

# Q-learning for traffic signal control
# State: queue lengths on N, S, E, W approaches (discretized)
# Actions: 0=extend NS green, 1=switch to EW green

class RLTrafficController:
    def __init__(self, node_id, alpha=0.1, gamma=0.9, epsilon=0.1):
        self.node_id = node_id
        self.alpha = alpha      # learning rate
        self.gamma = gamma      # discount factor
        self.epsilon = epsilon  # exploration rate
        self.q_table = {}       # state -> action values
        self.last_state = None
        self.last_action = None
        self.enabled = True
        
        # Signal state
        self.phase = "NS"  # "NS" or "EW"
        self.timer = 0
        self.min_green = 10
        self.max_green = 60
        self.yellow_time = 3
        self.state = "green"  # green, yellow, red
        
    def _get_state(self, queues):
        # Discretize queue lengths: 0, 1-3, 4-7, 8+
        def bucket(q):
            if q == 0: return 0
            if q <= 3: return 1
            if q <= 7: return 2
            return 3
        return (bucket(queues.get("N", 0)), bucket(queues.get("S", 0)),
                bucket(queues.get("E", 0)), bucket(queues.get("W", 0)),
                self.phase)
    
    def choose_action(self, queues):
        state = self._get_state(queues)
        
        if not self.enabled:
            return self._fixed_timing_action()
        
        if state not in self.q_table:
            self.q_table[state] = [0.0, 0.0]
        
        # Epsilon-greedy
        if random.random() < self.epsilon:
            action = random.choice([0, 1])
        else:
            action = 0 if self.q_table[state][0] >= self.q_table[state][1] else 1
        
        self.last_state = state
        self.last_action = action
        return action
    
    def learn(self, reward):
        if self.last_state is None or not self.enabled:
            return
        
        state = self.last_state
        action = self.last_action
        
        if state not in self.q_table:
            self.q_table[state] = [0.0, 0.0]
        
        # Q-learning update
        old_value = self.q_table[state][action]
        # Simplified: next state expected max value (using current table)
        next_max = max(self.q_table[state])
        new_value = old_value + self.alpha * (reward + self.gamma * next_max - old_value)
        self.q_table[state][action] = new_value
    
    def _fixed_timing_action(self):
        if self.timer >= self.max_green:
            return 1  # switch
        if self.timer < self.min_green:
            return 0  # extend
        # At middle, switch if other phase has more demand
        return random.choice([0, 1])
    
    def get_signal_state(self):
        return {
            "phase": self.phase,
            "state": self.state,
            "timer": self.timer,
            "rl_enabled": self.enabled,
            "q_table_size": len(self.q_table)
        }
    
    def toggle_rl(self):
        self.enabled = not self.enabled
        return self.enabled

