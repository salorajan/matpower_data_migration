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
from power_python.solvers.runpf import run_power_flow
from power_python.core.constants import *

from power_python.utils.reporter import print_pf_results

def test_case9_pf():
    case = PowerCase()
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'json', 'case9.json'))
    
    print(f"Loading {json_path}...")
    case.load_from_json(json_path)
    
    print("Running Power Flow...")
    case, converged = run_power_flow(case)
    
    assert converged
    
    # Use the new reporter utility
    print_pf_results(case)

    # Expected values for Case 9 (approximate)
    # Bus 1: 1.0400, 0.0000
    # Bus 2: 1.0250, 9.2807
    # Bus 3: 1.0250, 4.6648
    
    assert np.allclose(case.bus[0, VM], 1.0400, atol=1e-4)
    assert np.allclose(case.bus[1, VM], 1.0250, atol=1e-4)
    assert np.allclose(case.bus[2, VM], 1.0250, atol=1e-4)
    
    print("\nCase 9 Power Flow verification passed!")

if __name__ == "__main__":
    try:
        test_case9_pf()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
