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
from power_python.solvers.hepf import run_hepf
from power_python.solvers.complex_nr import run_complex_nr
from power_python.solvers.complex_nr_3p import run_complex_nr_3p

def test_hepf_convergence():
    case_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'outputs', 'json', 'case9.json'))
    case = PowerCase()
    case.load_from_json(case_path)
    
    print(f"\n--- Testing HEPF on {case_path} ---")
    case, success = run_hepf(case, max_order=14, verbose=True)
    assert success, "HEPF failed to converge on Case 9"
    print("HEPF convergence test passed.")

def test_complex_nr_convergence():
    case_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'outputs', 'json', 'case9.json'))
    case = PowerCase()
    case.load_from_json(case_path)
    
    print(f"\n--- Testing Complex NR (Wirtinger) on {case_path} ---")
    case, success = run_complex_nr(case, max_it=10, tol=1e-8, verbose=True)
    assert success, "Complex NR failed to converge on Case 9"
    print("Complex NR convergence test passed.")

def test_complex_nr_3p_convergence():
    case_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'outputs', 'json', 'case3p_a.json'))
    case = PowerCase()
    case.load_from_json(case_path)
    
    print(f"\n--- Testing 3-Phase Complex NR on {case_path} ---")
    case, success = run_complex_nr_3p(case, max_it=10, tol=1e-8, verbose=True)
    assert success, "3-Phase Complex NR failed to converge on case3p_a"
    print("3-Phase Complex NR convergence test passed.")

if __name__ == "__main__":
    try:
        test_hepf_convergence()
        test_complex_nr_convergence()
        test_complex_nr_3p_convergence()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
