"""
NexOS — Systeme genetique
Genes, mutations, reproduction.
L'evolution naturelle façonne les ISOs sur les generations.
"""

import random
from typing import Dict


# Traits genetiques par defaut avec bornes
DEFAULT_TRAITS = {
    'speed':      {'min': 0.5, 'max': 2.0, 'default': 1.0},
    'curiosity':  {'min': 0.1, 'max': 1.0, 'default': 0.5},
    'efficiency': {'min': 0.5, 'max': 1.5, 'default': 1.0},
    'perception': {'min': 3.0, 'max': 8.0, 'default': 5.0},
    'resilience':   {'min': 0.5, 'max': 1.5, 'default': 1.0},
    'intelligence': {'min': 0.3, 'max': 1.0, 'default': 0.5},
}


def create_genes(traits_config: dict = None) -> Dict[str, float]:
    """
    Genere un jeu de genes aleatoire.
    Chaque gene est tire uniformement dans ses bornes.
    """
    traits = traits_config or DEFAULT_TRAITS
    genes = {}
    for name, bounds in traits.items():
        if isinstance(bounds, dict):
            lo = bounds.get('min', 0.0)
            hi = bounds.get('max', 1.0)
        else:
            lo, hi = 0.0, 1.0
        genes[name] = round(random.uniform(lo, hi), 3)
    return genes


def mutate(genes: Dict[str, float], rate: float = 0.01,
           traits_config: dict = None) -> Dict[str, float]:
    """
    Copie les genes avec des mutations potentielles.
    Chaque gene a une probabilite `rate` de muter.
    La mutation ajoute un bruit gaussien borne.
    """
    traits = traits_config or DEFAULT_TRAITS
    new_genes = {}
    for name, value in genes.items():
        if random.random() < rate:
            # Mutation : bruit gaussien (ecart-type = 10% de la plage)
            bounds = traits.get(name, {'min': 0.0, 'max': 2.0})
            lo = bounds.get('min', 0.0) if isinstance(bounds, dict) else 0.0
            hi = bounds.get('max', 2.0) if isinstance(bounds, dict) else 2.0
            noise = random.gauss(0, (hi - lo) * 0.1)
            new_genes[name] = round(max(lo, min(hi, value + noise)), 3)
        else:
            new_genes[name] = value
    return new_genes


def reproduce(parent1_genes: Dict[str, float], parent2_genes: Dict[str, float],
              mutation_rate: float = 0.01, traits_config: dict = None) -> Dict[str, float]:
    """
    Cree les genes d'un enfant par croisement + mutation.
    Chaque gene est pris aleatoirement d'un parent ou de l'autre,
    puis potentiellement mute.
    """
    child_genes = {}
    all_traits = set(parent1_genes.keys()) | set(parent2_genes.keys())

    for trait in all_traits:
        v1 = parent1_genes.get(trait, 0.5)
        v2 = parent2_genes.get(trait, 0.5)

        # Croisement : 50/50 ou blend
        if random.random() < 0.3:
            # Blend (moyenne ponderee aleatoire)
            alpha = random.random()
            child_genes[trait] = round(v1 * alpha + v2 * (1 - alpha), 3)
        else:
            # Selection d'un parent
            child_genes[trait] = v1 if random.random() < 0.5 else v2

    # Mutations
    child_genes = mutate(child_genes, mutation_rate, traits_config)
    return child_genes


def fitness_score(genes: Dict[str, float]) -> float:
    """Score de fitness simplifie (somme ponderee des traits)"""
    weights = {
        'speed': 1.0,
        'curiosity': 0.8,
        'efficiency': 1.5,
        'perception': 1.2,
        'resilience': 1.3,
        'intelligence': 1.4,
    }
    score = sum(genes.get(t, 0) * w for t, w in weights.items())
    return round(score, 2)
