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
from power_python.solvers.dcopf import run_dc_opf
from power_python.core.constants import *

def test_case9_dcopf():
    case = PowerCase()
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'json', 'case9.json'))
    
    print(f"Loading {json_path} for DC-OPF...")
    case.load_from_json(json_path)
    
    print("Running DC-OPF...")
    case, success = run_dc_opf(case, verbose=True)
    
    assert success
    
    print("\nDC-OPF Generator Results:")
    print(f"{'Gen':<5} {'Bus':<6} {'Pg (MW)':<10}")
    print("-" * 25)
    for i in range(len(case.gen)):
        bus_id = int(case.external_bus_ids[int(case.gen[i, GEN_BUS])])
        print(f"{i+1:<5} {bus_id:<6} {case.gen[i, PG]:<10.2f}")

    # Case 9 DC-OPF approximate results (cost should be around 5300-5500)
    # Total load is 315 MW.
    # Gen 1: ~72, Gen 2: ~163, Gen 3: ~80 (approx depending on losses/DC approximation)
    
    total_pg = np.sum(case.gen[:, PG])
    print(f"\nTotal Generation: {total_pg:.2f} MW")
    assert np.allclose(total_pg, 315.0, atol=1e-2) # DC has no losses, so Pg = Pd
    
    print("\nCase 9 DC-OPF verification passed!")

if __name__ == "__main__":
    try:
        test_case9_dcopf()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
