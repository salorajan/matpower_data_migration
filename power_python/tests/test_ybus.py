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
from power_python.core.constants import *
from power_python.network.admittance import make_ybus

def test_ybus_3bus():
    # Setup a small 3-bus case manually
    case = PowerCase(baseMVA=100.0)
    
    # Bus matrix: BUS_I, TYPE, PD, QD, GS, BS, AREA, VM, VA, BASE_KV, ZONE, VMAX, VMIN
    case.bus = np.array([
        [1, REF, 0, 0, 0, 0, 1, 1, 0, 138, 1, 1.1, 0.9],
        [2, PQ,  0, 0, 0, 0, 1, 1, 0, 138, 1, 1.1, 0.9],
        [3, PQ,  0, 0, 0, 0, 1, 1, 0, 138, 1, 1.1, 0.9]
    ])
    
    # Branch matrix: F_BUS, T_BUS, R, X, B, RATE_A, RATE_B, RATE_C, TAP, SHIFT, STATUS, ANGMIN, ANGMAX
    case.branch = np.array([
        [1, 2, 0.02, 0.06, 0.06, 250, 250, 250, 0, 0, 1, -360, 360],
        [2, 3, 0.01, 0.03, 0.02, 250, 250, 250, 0, 0, 1, -360, 360],
        [1, 3, 0.0125, 0.025, 0.04, 250, 250, 250, 0, 0, 1, -360, 360]
    ])
    
    # Initialize mapping
    case.bus_map = {1: 0, 2: 1, 3: 2}
    
    # Convert to internal
    case.to_internal()
    
    # Calculate Ybus
    Ybus, Yf, Yt = make_ybus(case.baseMVA, case.bus, case.branch)
    
    # Dense version for comparison
    Ydense = Ybus.toarray()
    
    print("Calculated Ybus (Dense):")
    print(Ydense)
    
    # Expected results from ybus_verification.py
    # Branch 1-2: z = 0.02 + 0.06j -> y = 5 - 15j, y_shunt = 0.03j
    # Branch 2-3: z = 0.01 + 0.03j -> y = 10 - 30j, y_shunt = 0.01j
    # Branch 1-3: z = 0.0125 + 0.025j -> y = 16 - 32j, y_shunt = 0.02j
    
    # Y11 = y12 + y1_shunt12 + y13 + y1_shunt13 = (5-15j) + 0.03j + (16-32j) + 0.02j = 21 - 46.95j
    # Y12 = -y12 = -5 + 15j
    # Y13 = -y13 = -16 + 32j
    # Y22 = y12 + y_shunt12 + y23 + y_shunt23 = (5-15j) + 0.03j + (10-30j) + 0.01j = 15 - 44.96j
    
    expected_Y11 = (5-15j) + 0.03j + (16-32j) + 0.02j
    assert np.allclose(Ydense[0, 0], expected_Y11)
    assert np.allclose(Ydense[0, 1], -(5-15j))
    assert np.allclose(Ydense[0, 2], -(16-32j))
    
    print("Ybus verification passed!")

if __name__ == "__main__":
    try:
        test_ybus_3bus()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
