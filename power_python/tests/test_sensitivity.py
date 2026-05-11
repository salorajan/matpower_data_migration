import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from power_python.core.case import PowerCase
from power_python.network.sensitivity import make_ptdf, make_lodf
from power_python.core.constants import *

def test_sensitivity_case9():
    case = PowerCase()
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'outputs', 'json', 'case9.json'))
    
    print(f"Loading {json_path} for Sensitivity Analysis...")
    case.load_from_json(json_path)
    case.to_internal()
    
    # 1. Calculate PTDF
    print("Calculating PTDF matrix...")
    PTDF = make_ptdf(case.baseMVA, case.bus, case.branch)
    
    print(f"PTDF Dimensions: {PTDF.shape}")
    # Verify some properties
    # Sum of columns should be zero (approximately, except for slack effects)
    # More specifically, for a transfer from bus i to bus j, 
    # the flow change on line k is PTDF(k, i) - PTDF(k, j)
    
    # Check PTDF for Bus 1 (Slack)
    assert np.all(PTDF[:, 0] == 0) # Slack column is zero
    
    # 2. Calculate LODF
    print("Calculating LODF matrix...")
    LODF = make_lodf(case.branch, PTDF)
    print(f"LODF Dimensions: {LODF.shape}")
    
    # Check diagonals of H (h vector in make_lodf)
    # H = PTDF * Cft
    # h = diag(H)
    # If h[j] = 1, then line j is a bridge.
    
    # Manual check for Case 9
    f = case.branch[:, F_BUS].astype(int)
    t = case.branch[:, T_BUS].astype(int)
    row = np.concatenate([f, t])
    col = np.concatenate([np.arange(len(f)), np.arange(len(f))])
    data = np.concatenate([np.ones(len(f)), -np.ones(len(f))])
    from scipy.sparse import csr_matrix
    Cft = csr_matrix((data, (row, col)), shape=(9, 9)).toarray()
    H = PTDF @ Cft
    h = np.diag(H)
    print(f"Diagonals of H (h): {h}")
    
    # Example: Outage of Branch 1 (1-4)
    # Distribution factors to other branches
    print("\nLODF for Outage of Branch 1 (1-4):")
    for i in range(len(LODF)):
        if i == 0: continue
        f_bus = int(case.external_bus_ids[int(case.branch[i, F_BUS])])
        t_bus = int(case.external_bus_ids[int(case.branch[i, T_BUS])])
        print(f"  Branch {i+1} ({f_bus}-{t_bus}): {LODF[i, 0]:.4f}")

    # Basic validity check: diag is -1
    assert np.allclose(np.diag(LODF), -1.0)
    
    print("\nSensitivity Analysis (PTDF/LODF) verification passed!")

if __name__ == "__main__":
    try:
        test_sensitivity_case9()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
