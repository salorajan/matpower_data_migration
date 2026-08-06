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
from power_python.solvers.contingency import run_contingency_analysis
from power_python.core.constants import *

def test_contingency_case14():
    case = PowerCase()
    # Using case 14 which is more likely to have interesting contingencies than case 9
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'outputs', 'json', 'case14.json'))
    
    print(f"Loading {json_path} for Contingency Analysis...")
    case.load_from_json(json_path)
    
    # Artificially lower some ratings to trigger violations for testing
    case.branch[:, RATE_A] = 50.0 # Set a low limit of 50 MW for all lines
    
    print("Running N-1 Contingency Analysis...")
    df_violations = run_contingency_analysis(case, verbose=True)
    
    if not df_violations.empty:
        print(f"\nTotal violations found: {len(df_violations)}")
    else:
        print("\nNo violations found (even with lowered limits).")

    print("\nContingency Analysis verification complete!")

if __name__ == "__main__":
    try:
        test_contingency_case14()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
