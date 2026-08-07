# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from power_python.core.case import PowerCase
from power_python.solvers.sc_opf import run_sc_opf
from power_python.core.constants import *

def test_sc_opf_case9():
    case = PowerCase()
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'json', 'case9.json'))
    
    print(f"Loading {json_path} for SC-OPF...")
    case.load_from_json(json_path)
    
    # Original limits in Case 9 range from 150 to 300 MW.
    # Let's set them all to 200 MW to make some constraints potentially active 
    # without making the base case infeasible (max flow was ~163 MW).
    case.branch[:, RATE_A] = 200.0 
    
    print("Running Security-Constrained OPF (SC-OPF)...")
    case, success = run_sc_opf(case, verbose=True)
    
    assert success
    
    print("\nSC-OPF Generator Results:")
    print(f"{'Gen':<5} {'Bus':<6} {'Pg (MW)':<10}")
    print("-" * 25)
    for i in range(len(case.gen)):
        bus_id = int(case.external_bus_ids[int(case.gen[i, GEN_BUS])])
        print(f"{i+1:<5} {bus_id:<6} {case.gen[i, PG]:<10.2f}")

    print("\nCase 9 SC-OPF verification complete!")

if __name__ == "__main__":
    try:
        test_sc_opf_case9()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
