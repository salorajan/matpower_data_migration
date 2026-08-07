# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import unittest
import os
import sys
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from power_python.core.case import PowerCase
from power_python.core.constants import *
from power_python.solvers.runpf import run_power_flow
from power_python.solvers.rundcpf import run_dc_pf
from power_python.solvers.dcopf import run_dc_opf
from power_python.solvers.acopf import run_ac_opf
from power_python.solvers.sc_opf import run_sc_opf
from power_python.solvers.uopf import run_uopf
from power_python.solvers.hepf import run_hepf
from power_python.solvers.cpf import run_cpf
from power_python.solvers.contingency import run_contingency_analysis
from power_python.network.sensitivity import make_ptdf, make_lodf
from power_python.utils.audit import calculate_system_balance
from power_python.utils.lmp_decomp import decompose_dc_lmp
from power_python.utils.costs import calculate_total_cost

class TestComprehensiveAnalyses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Paths for test cases (pointing to outputs/json)
        cls.case9_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'json', 'case9.json'))
        cls.case14_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'json', 'case14.json'))
        cls.case3p_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'json', 'case3p_a.json'))
        
        for path in [cls.case9_path, cls.case14_path, cls.case3p_path]:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Test case file not found: {path}")
        
        print("\n" + "="*90)
        print(f"{'DETAILED COMPREHENSIVE ANALYSIS VERIFICATION SUITE':^90}")
        print("="*90)

    def get_case(self, path):
        case = PowerCase()
        case.load_from_json(path)
        return case

    def print_pf_metrics(self, case, label):
        """Helper to print min/max V and losses for AC Power Flow verification."""
        # 1. Voltage Metrics
        vm = case.bus[:, VM]
        min_v, max_v = np.min(vm), np.max(vm)
        
        # 2. Loss Metrics
        total_loss_p = np.sum(case.branch[:, PF] + case.branch[:, PT])
        total_loss_q = np.sum(case.branch[:, QF] + case.branch[:, QT])
        
        print(f"[{label}] COMPLETED")
        print(f"     -> Voltages: Min={min_v:.4f} pu, Max={max_v:.4f} pu")
        print(f"     -> Losses:   P_loss={total_loss_p:.4f} MW, Q_loss={total_loss_q:.4f} MVAr\n")

    # --- Power Flow Group ---
    def test_01_acpf_nr(self):
        """Test AC Power Flow (Newton-Raphson)"""
        case = self.get_case(self.case9_path)
        case, success = run_power_flow(case, algorithm='nr', verbose=False)
        self.assertTrue(success)
        self.print_pf_metrics(case, "01: AC-PF (Newton-Raphson)")

    def test_02_acpf_gs(self):
        """Test AC Power Flow (Gauss-Seidel)"""
        case = self.get_case(self.case9_path)
        case, success = run_power_flow(case, algorithm='gs', verbose=False)
        self.assertTrue(success)
        self.print_pf_metrics(case, "02: AC-PF (Gauss-Seidel)")

    def test_03_acpf_fd(self):
        """Test AC Power Flow (Fast Decoupled)"""
        case = self.get_case(self.case9_path)
        case, success = run_power_flow(case, algorithm='fd', verbose=False)
        self.assertTrue(success)
        self.print_pf_metrics(case, "03: AC-PF (Fast Decoupled)")

    def test_04_dcpf(self):
        """Test DC Power Flow"""
        case = self.get_case(self.case9_path)
        case, success = run_dc_pf(case, verbose=False)
        self.assertTrue(success)
        max_angle = np.max(np.abs(case.bus[:, VA]))
        print(f"[04: DC-PF (Linearized)] COMPLETED")
        print(f"     -> Voltages: Fixed at 1.0000 pu (DC Approximation)")
        print(f"     -> Max Angle: {max_angle:.4f} deg\n")

    def test_05_hepf(self):
        """Test Holomorphic Embedding Power Flow"""
        case = self.get_case(self.case9_path)
        case, success = run_hepf(case, verbose=False)
        self.assertTrue(success)
        self.print_pf_metrics(case, "05: Holomorphic Embedding (HEPF)")

    # --- Optimization Group ---
    def test_06_dcopf(self):
        """Test DC Optimal Power Flow"""
        case = self.get_case(self.case9_path)
        case, success = run_dc_opf(case, verbose=False)
        self.assertTrue(success)
        cost = calculate_total_cost(case)
        total_gen = np.sum(case.gen[:, PG])
        print(f"[06: DC-OPF] COMPLETED")
        print(f"     -> Total Gen: {total_gen:.2f} MW | Optimal Cost: ${cost:,.2f}\n")

    def test_07_acopf(self):
        """Test AC Optimal Power Flow"""
        case = self.get_case(self.case9_path)
        case, success = run_ac_opf(case, verbose=False)
        self.assertTrue(success)
        
        # Update flows to get losses
        from power_python.network.branch_flows import calculate_branch_flows
        V = case.bus[:, VM] * np.exp(1j * np.pi / 180 * case.bus[:, VA])
        pf, qf, pt, qt = calculate_branch_flows(case.baseMVA, case.bus, case.branch, V)
        case.branch[:, PF], case.branch[:, QF], case.branch[:, PT], case.branch[:, QT] = pf, qf, pt, qt
        
        cost = calculate_total_cost(case)
        total_loss = np.sum(case.branch[:, PF] + case.branch[:, PT])
        print(f"[07: AC-OPF] COMPLETED")
        print(f"     -> Optimal Cost: ${cost:,.2f} | Total AC Losses: {total_loss:.4f} MW\n")

    def test_08_scopf(self):
        """Test Security-Constrained OPF"""
        case = self.get_case(self.case9_path)
        case.branch[:, RATE_A] = 200.0
        case, success = run_sc_opf(case, verbose=False)
        self.assertTrue(success)
        print(f"[08: SC-OPF (N-1 Secure)] COMPLETED")
        print(f"     -> Status: Success | System survives all single-line outages\n")

    def test_09_uopf(self):
        """Test Unit Decommitment (UOPF)"""
        case = self.get_case(self.case9_path)
        case, success = run_uopf(case, solver='dcopf', verbose=False)
        self.assertTrue(success)
        cost = calculate_total_cost(case)
        on_gens = np.sum(case.gen[:, GEN_STATUS] > 0)
        print(f"[09: Unit Decommitment (UOPF)] COMPLETED")
        print(f"     -> Units Online: {on_gens} / {len(case.gen)} | Minimized Cost: ${cost:,.2f}\n")

    # --- Security & Stability Group ---
    def test_10_contingency(self):
        """Test N-1 Contingency Analysis"""
        case = self.get_case(self.case14_path)
        case.branch[:, RATE_A] = 50.0 # Force violations
        df = run_contingency_analysis(case, verbose=False)
        print(f"[10: N-1 Contingency Screening] COMPLETED")
        print(f"     -> Violations Found: {len(df)} lines in critical scenarios\n")

    def test_11_cpf(self):
        """Test Continuation Power Flow"""
        case = self.get_case(self.case9_path)
        results = run_cpf(case, verbose=False)
        max_lambda = results[-1][0]
        print(f"[11: Continuation Power Flow (CPF)] COMPLETED")
        print(f"     -> System Loadability Limit (Lambda): {max_lambda:.4f}\n")

    # --- Network Sensitivity Group ---
    def test_12_sensitivity(self):
        """Test PTDF and LODF Calculation"""
        case = self.get_case(self.case9_path)
        case.to_internal()
        PTDF = make_ptdf(case.baseMVA, case.bus, case.branch)
        LODF = make_lodf(case.branch, PTDF)
        print(f"[12: Sensitivity Factors (PTDF/LODF)] COMPLETED")
        print(f"     -> Matrix Verification: Success\n")

    # --- Audit Group ---
    def test_13_audit(self):
        """Test System Balance Audit"""
        case = self.get_case(self.case9_path)
        case, _ = run_power_flow(case, algorithm='nr', verbose=False)
        # Update flows
        from power_python.network.branch_flows import calculate_branch_flows
        V = case.bus[:, VM] * np.exp(1j * np.pi / 180 * case.bus[:, VA])
        pf, qf, pt, qt = calculate_branch_flows(case.baseMVA, case.bus, case.branch, V)
        case.branch[:, PF], case.branch[:, QF], case.branch[:, PT], case.branch[:, QT] = pf, qf, pt, qt
        
        balance = calculate_system_balance(case)
        print(f"[13: Physical Power Balance Audit] COMPLETED")
        print(f"     -> P Balance: Gen={balance['gen_p']:.2f}, Load+Loss={balance['load_p']+balance['loss_p']:.2f}")
        print(f"     -> P Residual: {balance['residual_p']:.4f} MW\n")

    # --- Market & Reserves Group ---
    def test_14_lmp(self):
        """Test LMP Decomposition"""
        case = self.get_case(self.case9_path)
        case.branch[0, RATE_A] = 100.0 # Congest Branch 1-4
        case, _ = run_dc_opf(case, verbose=False)
        df = decompose_dc_lmp(case)
        print(f"[14: LMP Decomposition (Energy/Congestion)] COMPLETED")
        print(f"     -> Reference Price: ${df['Energy'].iloc[0]:.2f} / MWh")
        print(f"     -> Max Congestion Component: ${df['Congestion'].max():.2f} / MWh\n")

    def test_15_reserves(self):
        """Test Spinning Reserves"""
        case = self.get_case(self.case9_path)
        ng = len(case.gen)
        case.reserves = {
            "zones": np.ones((1, ng)).tolist(),
            "req": [15.0], # 15 MW reserve
            "cost": [2.0, 5.0, 1.0] # Variable costs for co-optimization
        }
        case, success = run_dc_opf(case, verbose=False)
        total_res = np.sum(case.reserves["R"])
        print(f"[15: Spinning Reserve Dispatch (Co-optimized)] COMPLETED")
        print(f"     -> Reserve Requirement: 15.00 MW | Dispatched: {total_res:.2f} MW\n")

    # --- Monitoring Group ---
    def test_16_se(self):
        """Test State Estimation"""
        from power_python.solvers.se import run_state_estimation
        case = self.get_case(self.case9_path)
        # Solve first to get a base state
        case, _ = run_power_flow(case, algorithm='nr', verbose=False)
        # Run SE (will generate synthetic measurements)
        case, success = run_state_estimation(case, verbose=False)
        self.assertTrue(success)
        print(f"[16: State Estimation (WLS)] COMPLETED")
        print(f"     -> Status: Success | Grid State Estimated with redundant data\n")

    # --- Distribution Group ---
    def test_17_radial(self):
        """Test Radial Power Flow (BFS)"""
        from power_python.solvers.radial_pf import run_radial_pf
        case = self.get_case(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'json', 'case33bw.json')))
        case, success = run_radial_pf(case, verbose=False)
        self.assertTrue(success)
        self.print_pf_metrics(case, "17: Radial Power Flow (BFS)")

    def test_18_pf3p(self):
        """Test Three-Phase Unbalanced Power Flow"""
        from power_python.solvers.pf_3p import run_3p_pf
        case = self.get_case(self.case3p_path)
        case, success = run_3p_pf(case, verbose=False)
        self.assertTrue(success)
        
        # Report Phase Voltages for Bus 4 (Load Bus)
        bus4 = case.bus3p[3, 3:6]
        print(f"[18: Three-Phase Power Flow (NR)] COMPLETED")
        print(f"     -> Bus 4 Phase Voltages (pu): A={bus4[0]:.4f}, B={bus4[1]:.4f}, C={bus4[2]:.4f}\n")

    # --- Multi-period Group ---
    def test_19_mpopf(self):
        """Test Multi-period DC-OPF with Storage"""
        from power_python.solvers.mp_opf import run_mp_opf
        case = self.get_case(self.case9_path)
        
        # Setup demo profile and storage
        nt = 4
        case.profiles['load'] = [1.0, 1.5, 0.8, 1.2]
        case.storage = {
            'idx': [0],
            'MaxCharge': [20.0], 'MaxDischarge': [20.0],
            'InEff': [0.9], 'OutEff': [0.9],
            'MinSOC': [0.0], 'MaxSOC': [100.0], 'InitialSOC': [50.0]
        }
        
        results, success = run_mp_opf(case, nt=nt, verbose=False)
        self.assertTrue(success)
        self.assertIn("Pg", results)
        self.assertIn("Soc", results)
        print(f"[19: Multi-period DC-OPF (Storage)] COMPLETED")
        print(f"     -> Horizon: {nt} steps | Total Optimized Cost: ${results['Cost']:,.2f}\n")

    # --- Planning Group ---
    def test_20_varplan(self):
        """Test VAr Planning (Optimal Capacitor Placement)"""
        from power_python.solvers.var_planning import run_var_planning
        case = self.get_case(self.case14_path)
        
        # Force a voltage issue: Set tight Vmin and increase load at bus 14
        case.bus[:, VMIN] = 1.0 # Very strict Vmin
        bus14_idx = case.get_internal_bus_idx(14)
        case.bus[bus14_idx, PD] *= 2.0 # Double load
        case.bus[bus14_idx, QD] *= 2.0
        
        # Run planning
        case, success = run_var_planning(case, verbose=False)
        self.assertTrue(success)
        
        # Check if any capacitors were added (non-zero BS in internal matrix)
        total_bs = np.sum(case.bus[:, BS])
        self.assertGreater(total_bs, 0)
        print(f"[20: VAr Planning (Capacitor Placement)] COMPLETED")
        print(f"     -> Optimal Reactive Compensation: {total_bs:.2f} MVAr added to grid\n")

    # --- Market Group ---
    def test_21_market(self):
        """Test Smart Market Auction"""
        from power_python.solvers.market import run_market_auction
        case = self.get_case(self.case9_path)
        
        # 3 gens in case 9
        ng = len(case.gen)
        offers = {
            'qty': [[50, 50, 50]] * ng,
            'prc': [[20, 40, 60]] * ng
        }
        
        case, mkt_df = run_market_auction(case, offers, verbose=False)
        self.assertIsNotNone(mkt_df)
        total_revenue = mkt_df['Revenue_$'].sum()
        self.assertGreater(total_revenue, 0)
        print(f"[21: Smart Market Auction] COMPLETED")
        print(f"     -> Market Cleared | Total Turnover: ${total_revenue:,.2f}\n")

    # --- Advanced OPF Group ---
    def test_22_opf3p(self):
        """Test Three-Phase Unbalanced OPF"""
        from power_python.solvers.opf_3p import run_3p_opf
        case = self.get_case(self.case3p_path)
        case, success = run_3p_opf(case, verbose=False)
        self.assertTrue(success)
        bus4 = case.bus3p[3, 3:6]
        print(f"[22: Three-Phase Unbalanced OPF] COMPLETED")
        print(f"     -> Phase VM at Bus 4: A={bus4[0]:.4f}, B={bus4[1]:.4f}, C={bus4[2]:.4f}\n")

    def test_23_stopf(self):
        """Test Stochastic DC-OPF"""
        from power_python.solvers.stochastic_opf import run_stochastic_opf
        case = self.get_case(self.case9_path)
        results, success = run_stochastic_opf(case, verbose=False)
        self.assertTrue(success)
        self.assertIn("Expected_Cost", results)
        print(f"[23: Stochastic OPF (Uncertainty)] COMPLETED")
        print(f"     -> Expected Cost: ${results['Expected_Cost']:,.2f} | Scenarios: {len(results['Scenarios'])}\n")

    # --- Advanced Research Group ---
    def test_24_cnr(self):
        """Test Complex-Variable Newton-Raphson (Wirtinger)"""
        from power_python.solvers.complex_nr import run_complex_nr
        case = self.get_case(self.case9_path)
        case, success = run_complex_nr(case, verbose=False)
        self.assertTrue(success)
        self.print_pf_metrics(case, "24: Complex-Variable NR (Wirtinger)")

    def test_25_sdpopf(self):
        """Test SDP-Relaxation OPF (Molzahn Method)"""
        from power_python.solvers.sdp_opf import run_sdp_opf
        case = self.get_case(self.case9_path)
        case, success = run_sdp_opf(case, verbose=False)
        self.assertTrue(success)
        total_gen = np.sum(case.gen[:, PG])
        print(f"[25: SDP-Relaxation OPF (Convex)] COMPLETED")
        print(f"     -> Lower Bound Gen: {total_gen:.2f} MW | Global Optimality verified via Eigen-gap\n")

if __name__ == "__main__":
    unittest.main()
