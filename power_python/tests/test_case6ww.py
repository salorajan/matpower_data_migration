import sys
import os
import numpy as np
import pandas as pd
import unittest

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from power_python.core.case import PowerCase
from power_python.solvers.runpf import run_power_flow
from power_python.solvers.dcopf import run_dc_opf
from power_python.solvers.sc_opf import run_sc_opf
from power_python.solvers.contingency import run_contingency_analysis
from power_python.network.sensitivity import make_ptdf, make_lodf
from power_python.utils.reporter import print_pf_results
from power_python.core.constants import *

class TestCase6WW(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Load the case data once for all tests."""
        cls.case = PowerCase()
        cls.json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'outputs', 'json', 'case6ww.json'))
        if not os.path.exists(cls.json_path):
            raise FileNotFoundError(f"Case file not found: {cls.json_path}")
        cls.case.load_from_json(cls.json_path)

    def test_01_ac_power_flow(self):
        """Test AC Power Flow convergence and results."""
        print("\n--- Testing AC Power Flow (case6ww) ---")
        # Work on a copy to avoid side effects
        case_copy = PowerCase()
        case_copy.load_from_json(self.json_path)
        
        updated_case, converged = run_power_flow(case_copy, verbose=False)
        self.assertTrue(converged, "AC Power Flow failed to converge")
        
        # Verify specific bus voltages (approximate Wood & Wollenberg results)
        # Bus 1 is Slack (1.05 pu)
        self.assertAlmostEqual(updated_case.bus[0, VM], 1.05, places=3)
        print("AC Power Flow: Passed")

    def test_02_dc_opf(self):
        """Test DC Optimal Power Flow."""
        print("\n--- Testing DC-OPF (case6ww) ---")
        case_copy = PowerCase()
        case_copy.load_from_json(self.json_path)
        
        updated_case, success = run_dc_opf(case_copy, verbose=False)
        self.assertTrue(success, "DC-OPF failed to solve")
        
        total_pg = np.sum(updated_case.gen[:, PG])
        total_pd = np.sum(updated_case.bus[:, PD])
        self.assertAlmostEqual(total_pg, total_pd, places=2)
        print(f"DC-OPF: Passed (Total Gen: {total_pg:.2f} MW)")

    def test_03_sensitivity_factors(self):
        """Test PTDF and LODF calculation."""
        print("\n--- Testing PTDF/LODF (case6ww) ---")
        case_copy = PowerCase()
        case_copy.load_from_json(self.json_path)
        case_copy.to_internal()
        
        PTDF = make_ptdf(case_copy.baseMVA, case_copy.bus, case_copy.branch)
        self.assertEqual(PTDF.shape, (len(case_copy.branch), len(case_copy.bus)))
        
        LODF = make_lodf(case_copy.branch, PTDF)
        self.assertEqual(LODF.shape, (len(case_copy.branch), len(case_copy.branch)))
        
        # Diagonal of LODF for non-bridges should be -1
        diag = np.diag(LODF)
        for val in diag:
            if not np.isnan(val):
                self.assertAlmostEqual(val, -1.0, places=5)
        print("Sensitivity Factors: Passed")

    def test_04_contingency_analysis(self):
        """Test N-1 Contingency Analysis."""
        print("\n--- Testing N-1 Contingency (case6ww) ---")
        case_copy = PowerCase()
        case_copy.load_from_json(self.json_path)
        
        # Artificially tighten limits to find contingencies
        case_copy.branch[:, RATE_A] = 40.0
        
        df_violations = run_contingency_analysis(case_copy, verbose=False)
        self.assertIsInstance(df_violations, pd.DataFrame)
        print(f"Contingency Analysis: Passed ({len(df_violations)} violations found with tight limits)")

    def test_05_sc_opf(self):
        """Test Security-Constrained OPF."""
        print("\n--- Testing SC-OPF (case6ww) ---")
        case_copy = PowerCase()
        case_copy.load_from_json(self.json_path)
        
        # Relax limits to ensure feasibility
        case_copy.branch[:, RATE_A] = 100.0
        
        updated_case, success = run_sc_opf(case_copy, verbose=False)
        self.assertTrue(success, "SC-OPF failed to solve")
        print("SC-OPF: Passed")

if __name__ == "__main__":
    unittest.main()
