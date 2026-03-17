#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script to verify Daedalus integration"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
print("Testing imports...")
try:
    from nexos_life.daedalus import Daedalus
    print("[OK] Daedalus import successful")
except Exception as e:
    print(f"[FAIL] Daedalus import failed: {e}")
    sys.exit(1)

try:
    from nexos_life.population import Population
    print("[OK] Population import successful")
except Exception as e:
    print(f"[FAIL] Population import failed: {e}")
    sys.exit(1)

try:
    from nexos_core.config import load_config
    print("[OK] Config import successful")
except Exception as e:
    print(f"[FAIL] Config import failed: {e}")
    sys.exit(1)

# Test Daedalus initialization
print("\nTesting Daedalus initialization...")
config = load_config()
try:
    daedalus = Daedalus(config=config)
    print(f"[OK] Daedalus created at ({daedalus.x}, {daedalus.z})")
    print(f"  - enabled: {daedalus.enabled}")
    print(f"  - influence_radius: {daedalus.influence_radius}")
    print(f"  - action_rate: {daedalus.action_rate}")
except Exception as e:
    print(f"[FAIL] Daedalus initialization failed: {e}")
    sys.exit(1)

# Test state serialization
print("\nTesting Daedalus state serialization...")
try:
    state = daedalus.get_state()
    print("[OK] State serialization successful")
    for key, val in state.items():
        print(f"  - {key}: {val}")
except Exception as e:
    print(f"[FAIL] State serialization failed: {e}")
    sys.exit(1)

# Test Population integration
print("\nTesting Population integration...")
try:
    from nexos_core.grid import Grid
    population = Population(config=config)
    grid = Grid(config=config)

    if population.daedalus:
        print(f"[OK] Daedalus integrated in Population")
        print(f"  - daedalus_enabled: {population.daedalus_enabled}")
        print(f"  - Position: ({population.daedalus.x}, {population.daedalus.z})")
    else:
        print("[FAIL] Daedalus not found in Population")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] Population integration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[SUCCESS] All tests passed!")
print("Daedalus is successfully integrated into NexOS.")
