# PowerPython Dynamics Unit Tests
# Copyright (c) 2026 PowerPython contributors
# Licensed under the 3-clause BSD License (see LICENSE file for details).

import unittest
import os
import sys
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from power_python.core.case import PowerCase
from power_python.dynamics.parser import DYRParser
from power_python.dynamics.solver import DynamicCase, run_simulation
from power_python.dynamics.models import GENCLS, GENSAL, SEXS, TGOV1

class TestDynamics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case9_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'json', 'case9.json'))
        cls.dyr_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'case9_test.dyr'))
        
        if not os.path.exists(cls.case9_path):
            raise FileNotFoundError(f"Case 9 JSON file not found: {cls.case9_path}")
        if not os.path.exists(cls.dyr_path):
            raise FileNotFoundError(f"DYR test file not found: {cls.dyr_path}")

    def test_01_parser(self):
        """Test .dyr file parsing."""
        parser = DYRParser()
        records = parser.parse_file(self.dyr_path)
        
        # Verify number of records
        self.assertEqual(len(records), 5)
        
        # Verify first record
        rec0 = records[0]
        self.assertEqual(rec0['bus_id'], 1)
        self.assertEqual(rec0['model_name'], 'GENCLS')
        self.assertEqual(rec0['gen_id'], '1')
        self.assertEqual(rec0['params'][0], 23.64)  # H
        self.assertEqual(rec0['params'][3], 0.0608)  # Xd_prime

        # Verify salient pole generator record
        rec1 = records[1]
        self.assertEqual(rec1['bus_id'], 2)
        self.assertEqual(rec1['model_name'], 'GENSAL')
        self.assertEqual(rec1['params'][2], 8.96)  # Td0_prime
        
        # Verify controller models
        rec2 = records[2]
        self.assertEqual(rec2['model_name'], 'SEXS')
        self.assertEqual(rec2['params'][2], 100.0)  # K
        
        rec3 = records[3]
        self.assertEqual(rec3['model_name'], 'TGOV1')
        self.assertEqual(rec3['params'][0], 0.05)  # R

    def test_02_simulation_run(self):
        """Test dynamic simulation run with fault and line clearing."""
        # 1. Load PowerCase
        case = PowerCase()
        case.load_from_json(self.case9_path)
        
        # 2. Parse DYR file
        parser = DYRParser()
        dyr_records = parser.parse_file(self.dyr_path)
        
        # 3. Run transient stability simulation
        # Apply fault at bus 7 at t=0.1s, clear it at t=0.2s by tripping line 7-8
        t_end = 1.0
        dt = 0.005
        
        history = run_simulation(
            power_case=case,
            dyr_records=dyr_records,
            fault_bus=7,
            fault_time=0.1,
            clear_time=0.2,
            t_end=t_end,
            dt=dt,
            trip_branch=(7, 8),
            verbose=True
        )
        
        # 4. Verify results structure
        self.assertIn('time', history)
        self.assertIn('bus_voltages', history)
        self.assertIn('rotor_angles', history)
        self.assertIn('speeds', history)
        
        steps = int(t_end / dt)
        self.assertEqual(len(history['time']), steps)
        self.assertEqual(history['bus_voltages'].shape, (steps, len(case.bus)))
        
        # Verify rotor angles exist for all 3 generators
        self.assertEqual(len(history['rotor_angles']), 3)
        
        # Check angle dynamics: generators should swing
        # Gen at bus 2 (idx 1) rotor angle should change after fault at t=0.1
        angles_gen2 = history['rotor_angles'][1]
        initial_angle = angles_gen2[0]
        fault_angle = angles_gen2[int(0.15 / dt)]
        post_fault_angle = angles_gen2[-1]
        
        print("Dynamic Verification Swing Angles (Gen 2):")
        print(f"     -> t=0.0s (Initial):  {np.degrees(initial_angle):.4f} deg")
        print(f"     -> t=0.15s (In-Fault): {np.degrees(fault_angle):.4f} deg")
        print(f"     -> t=1.0s (Post-Fault): {np.degrees(post_fault_angle):.4f} deg\n")
        
        self.assertNotEqual(initial_angle, fault_angle)
        self.assertNotEqual(fault_angle, post_fault_angle)

if __name__ == '__main__':
    unittest.main()
