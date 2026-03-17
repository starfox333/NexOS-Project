"""
NexOS — Systeme de memoire ISO
Un ISO se souvient de ses experiences et ajuste son comportement.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import defaultdict


@dataclass
class Experience:
    """Une experience vecue par un ISO"""
    state_key: str        # Cle resumant l'etat (ex: "low_energy|fertile|no_threat")
    action: str           # Action effectuee
    reward: float         # Recompense obtenue (positive = bien, negative = mal)
    cycle: int = 0        # Cycle ou l'experience a eu lieu


class Memory:
    """
    Memoire d'un ISO — stocke les experiences et apprend.

    L'apprentissage est simple mais efficace :
    - Chaque (etat, action) a un score cumule
    - Les actions avec haut score sont preferees
    - L'exploration permet de decouvrir de nouvelles strategies
    """

    def __init__(self, capacity: int = 500, learning_rate: float = 0.1,
                 exploration_rate: float = 0.3):
        self.capacity = capacity
        self.learning_rate = learning_rate
        self.exploration_rate = exploration_rate

        self.experiences: List[Experience] = []

        # Q-table simplifiee : {state_key: {action: score}}
        self.q_table: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # Compteurs
        self.total_experiences = 0
        self.total_reward = 0.0

    def store_experience(self, state_key: str, action: str, reward: float, cycle: int = 0):
        """Stocke une experience et met a jour la Q-table"""
        exp = Experience(state_key=state_key, action=action, reward=reward, cycle=cycle)
        self.experiences.append(exp)
        self.total_experiences += 1
        self.total_reward += reward

        # Mise a jour Q-table (apprentissage par renforcement simplifie)
        old_q = self.q_table[state_key][action]
        self.q_table[state_key][action] = old_q + self.learning_rate * (reward - old_q)

        # Limiter la taille
        if len(self.experiences) > self.capacity:
            self.experiences = self.experiences[-self.capacity:]

    def recall_similar(self, state_key: str) -> List[Experience]:
        """Retrouve les experiences similaires a l'etat actuel"""
        return [e for e in self.experiences if e.state_key == state_key]

    def get_best_action(self, state_key: str, available_actions: List[str]) -> str:
        """
        Choisit la meilleure action selon la memoire.
        Epsilon-greedy : explore parfois, exploite le reste du temps.
        """
        if not available_actions:
            return 'rest'

        # Exploration : action aleatoire
        if random.random() < self.exploration_rate:
            return random.choice(available_actions)

        # Exploitation : meilleure action connue
        scores = self.q_table.get(state_key, {})
        if not scores:
            return random.choice(available_actions)

        best_action = max(available_actions, key=lambda a: scores.get(a, 0.0))
        return best_action

    def learn(self):
        """Ajuste l'exploration en fonction de l'experience accumulee"""
        # Diminuer l'exploration au fil du temps (l'ISO devient plus sur de lui)
        if self.total_experiences > 100:
            self.exploration_rate = max(0.05, self.exploration_rate * 0.999)

    def get_stats(self) -> dict:
        return {
            'experiences': len(self.experiences),
            'total': self.total_experiences,
            'total_reward': round(self.total_reward, 1),
            'exploration_rate': round(self.exploration_rate, 3),
            'known_states': len(self.q_table)
        }
