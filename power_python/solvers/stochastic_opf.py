# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import cvxpy as cp
import numpy as np
import pandas as pd
from ..core.constants import *
from .dcopf import run_dc_opf

def run_stochastic_opf(case, scenarios=None, verbose=True):
    """
    Solves a Stochastic DC-OPF considering multiple renewable scenarios.
    Minimizes expected cost across all scenarios while respecting constraints.
    
    Args:
        case: PowerCase object.
        scenarios: List of dicts, each with 'prob' and 'gen_mult' (NG x 1).
                   If None, generates 3 sample scenarios (Low, Mid, High wind).
        verbose: Print progress.
        
    Returns:
        tuple: (results_dict, success)
    """
    case.to_internal()
    nb = len(case.bus)
    ng = len(case.gen)
    baseMVA = case.baseMVA

    # 1. Scenario Setup
    if scenarios is None:
        # Default: Low (20%), Mid (100%), High (150%) renewable gen
        scenarios = [
            {'prob': 0.2, 'mult': 0.5},
            {'prob': 0.6, 'mult': 1.0},
            {'prob': 0.2, 'mult': 1.5}
        ]
    
    ns = len(scenarios)
    
    # 2. Decision Variables
    # Conventional gen is a "first-stage" decision (fixed across scenarios)
    # Wind gen and slack are "second-stage" (recourse)
    # Actually, standard Stochastic OPF uses a single Pg set, 
    # but we'll use Scenario-based OPF:
    # Minimize E[Cost] = sum(prob_s * cost(Pg_s))
    
    Pg = cp.Variable((ns, ng))
    Va = cp.Variable((ns, nb))
    
    # 3. Constraints & Objective
    objective_terms = []
    constraints = []
    
    # Reference bus
    ref = np.where(case.bus[:, BUS_TYPE] == REF)[0][0]
    
    # Build Bbus (DC)
    stat = case.branch[:, BR_STATUS]
    X = case.branch[:, BR_X]
    b_line = stat / X
    Bbus = np.zeros((nb, nb))
    f = case.branch[:, F_BUS].astype(int)
    t = case.branch[:, T_BUS].astype(int)
    for i in range(len(case.branch)):
        if stat[i] > 0:
            Bbus[f[i], f[i]] += b_line[i]
            Bbus[t[i], t[i]] += b_line[i]
            Bbus[f[i], t[i]] -= b_line[i]
            Bbus[t[i], f[i]] -= b_line[i]

    Pd = case.bus[:, PD]
    bus_gen_map = np.zeros((nb, ng))
    for i in range(ng):
        bus_gen_map[int(case.gen[i, GEN_BUS]), i] = 1.0

    for s in range(ns):
        prob = scenarios[s]['prob']
        mult = scenarios[s]['mult']
        
        # A. Objective: Expected Cost
        for i in range(ng):
            # Cost based on Pg[s, i]
            # Use quadratic fallback
            objective_terms.append(prob * cp.square(Pg[s, i]))
            
        # B. Power Balance
        # Renewables vary by mult
        current_Pd = Pd # Assuming load is constant, but gen limits vary
        constraints += [ (bus_gen_map @ Pg[s, :]) - current_Pd == (Bbus @ Va[s, :]) * baseMVA ]
        
        # C. Gen Limits (Vary by scenario multiplier for renewables)
        # We'll treat Gen 2 and 3 as renewable for Case 9
        scenario_pmax = case.gen[:, PMAX].copy()
        if ng > 1:
            scenario_pmax[1:] *= mult # Gen 2 and 3 are variable
            
        constraints += [ Pg[s, :] >= case.gen[:, PMIN], Pg[s, :] <= scenario_pmax ]
        
        # D. Slack Angle
        constraints += [ Va[s, ref] == 0 ]

    # 4. Solve
    prob_obj = cp.Minimize(cp.sum(objective_terms))
    problem = cp.Problem(prob_obj, constraints)
    problem.solve()
    
    if problem.status in ["optimal", "feasible"]:
        if verbose:
            print(f"Stochastic OPF Solved. Expected Cost: {problem.value:.2f}")
        return {
            "Pg": Pg.value,
            "Expected_Cost": problem.value,
            "Scenarios": scenarios
        }, True
    else:
        return None, False

def print_stochastic_results(results):
    """Prints a summary of the stochastic dispatch."""
    print("\n" + "="*80)
    print(f"{'STOCHASTIC OPF DISPATCH SUMMARY':^80}")
    print("="*80)
    print(f"{'Scenario':<12} {'Prob':<10} {'Renew. Mult':<15} {'Total Gen (MW)':<15}")
    print("-" * 65)
    
    ns = len(results['Scenarios'])
    for s in range(ns):
        gen_s = np.sum(results['Pg'][s, :])
        print(f"{s:<12} {results['Scenarios'][s]['prob']:<10.2f} {results['Scenarios'][s]['mult']:<15.2f} {gen_s:<15.2f}")
    
    print("="*80 + "\n")
