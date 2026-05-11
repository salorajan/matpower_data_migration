import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from power_python.core.case import PowerCase
from power_python.core.constants import *

def test_case9_loading():
    case = PowerCase()
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'outputs', 'json', 'case9.json'))
    
    print(f"Loading {json_path}...")
    case.load_from_json(json_path)
    
    print(case)
    
    # Basic assertions
    assert case.baseMVA == 100.0
    assert len(case.bus) == 9
    assert len(case.gen) == 3
    assert len(case.branch) == 9
    
    # Check data access using constants
    # Bus 5 (internal index 4) should have Pd = 90
    bus5_idx = case.get_internal_bus_idx(5)
    print(f"Internal index for Bus 5: {bus5_idx}")
    assert bus5_idx == 4
    assert case.bus[bus5_idx, PD] == 90.0
    
    print("Test passed!")

if __name__ == "__main__":
    try:
        test_case9_loading()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
