# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
import copy
from ..core.constants import *
from .dcopf import run_dc_opf
from ..utils.costs import calculate_total_cost

def run_uopf(case, solver='dcopf', verbose=True):
    """
    Solves combined unit decommitment and optimal power flow.
    Uses a heuristic algorithm similar to MATPOWER's uopf.m.
    
    Args:
        case: A PowerCase object.
        solver: The OPF solver to use ('dcopf' or 'acopf').
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, success)
    """
    if verbose:
        print("\n" + "="*80)
        print(f"{'UNIT DECOMMITMENT OPF':^80}")
        print("="*80)

    # 1. Initialization
    # Ensure all generators are correctly indexed
    case.to_internal()
    
    # 2. Check for sum(Pmin) > total load, decommit as necessary
    # Find generators that are in service and not dispatchable loads (Pmin > 0 usually)
    on_indices = np.where(case.gen[:, GEN_STATUS] > 0)[0]
    total_load = np.sum(case.bus[:, PD])
    
    while np.sum(case.gen[on_indices, PMIN]) > total_load:
        # Shut down most expensive unit at Pmin
        # Calculate average cost at Pmin: C(Pmin) / Pmin
        avg_costs = []
        for i in on_indices:
            pmin = case.gen[i, PMIN]
            if pmin > 0:
                # Temporary Pg set to Pmin for cost calculation
                original_pg = case.gen[i, PG]
                case.gen[i, PG] = pmin
                # Calculate cost for just this generator
                cost = calculate_generator_cost(case, i)
                avg_costs.append(cost / pmin)
                case.gen[i, PG] = original_pg
            else:
                avg_costs.append(0.0)
        
        # Find index of max avg cost among on_indices
        max_idx_in_on = np.argmax(avg_costs)
        gen_to_shutdown = on_indices[max_idx_in_on]
        
        if verbose:
            print(f"Shutting down generator {int(case.external_gen_ids[gen_to_shutdown])} to satisfy Pmin limits.")
            
        case.gen[gen_to_shutdown, [PG, QG, GEN_STATUS]] = 0
        on_indices = np.where(case.gen[:, GEN_STATUS] > 0)[0]
        
    if len(on_indices) == 0:
        if verbose:
            print("Infeasible: All generators shut down.")
        return case, False

    # 3. Run Initial OPF
    if verbose:
        print("Running initial OPF...")
    best_case, success = run_opf_by_type(case, solver, verbose=False)
    if not success:
        if verbose:
            print("Initial OPF failed.")
        return case, False
        
    best_cost = calculate_total_cost(best_case)
    if verbose:
        print(f"Initial Cost: {best_cost:.2f}")

    # 4. Iterative Decommitment Heuristic
    while True:
        # Get candidates for shutdown: On-generators with Pmin > 0
        on_indices = np.where(best_case.gen[:, GEN_STATUS] > 0)[0]
        candidates = [i for i in on_indices if best_case.gen[i, PMIN] > 0]
        
        if not candidates:
            break
            
        improved = False
        best_candidate_idx = -1
        
        for k in candidates:
            # Try shutting down candidate k
            test_case = copy.deepcopy(best_case)
            test_case.gen[k, [PG, QG, GEN_STATUS]] = 0
            
            # Check if remaining capacity can meet load
            if np.sum(test_case.gen[:, PMAX]) < total_load:
                continue
                
            # Run OPF
            test_results, test_success = run_opf_by_type(test_case, solver, verbose=False)
            
            if test_success:
                test_cost = calculate_total_cost(test_results)
                if test_cost < best_cost:
                    best_cost = test_cost
                    best_case = test_results
                    best_candidate_idx = k
                    improved = True
                    
        if improved:
            if verbose:
                print(f"Shutting down generator {int(best_case.external_gen_ids[best_candidate_idx])}. New Cost: {best_cost:.2f}")
        else:
            # No further improvement
            break
            
    if verbose:
        print(f"\nFinal Unit Decommitment Results:")
        print(f"Total Cost: {best_cost:.2f}")
        print("="*80)
        
    return best_case, True

def run_opf_by_type(case, solver, verbose=False):
    """Helper to run either DC or AC OPF."""
    if solver == 'dcopf':
        return run_dc_opf(case, verbose=verbose)
    elif solver == 'acopf':
        from .acopf import run_ac_opf
        return run_ac_opf(case, verbose=verbose)
    else:
        raise ValueError(f"Unknown solver: {solver}")

def calculate_generator_cost(case, gen_idx):
    """Calculates cost for a single generator."""
    if len(case.gencost) <= gen_idx:
        return case.gen[gen_idx, PG] ** 2 # Default fallback
        
    model = int(case.gencost[gen_idx, MODEL])
    ncost = int(case.gencost[gen_idx, NCOST])
    pg = case.gen[gen_idx, PG]
    
    if model == POLYNOMIAL:
        cost_coeffs = case.gencost[gen_idx, COST:COST+ncost]
        cost = 0.0
        for j, coeff in enumerate(cost_coeffs):
            exponent = ncost - 1 - j
            cost += coeff * (pg ** exponent)
        return cost
    elif model == PW_LINEAR:
        # Simplified linear cost for single gen
        points = case.gencost[gen_idx, COST:COST+2*ncost].reshape(-1, 2)
        if pg <= points[0, 0]: return points[0, 1]
        if pg >= points[-1, 0]: return points[-1, 1]
        for j in range(len(points)-1):
            if points[j, 0] <= pg <= points[j+1, 0]:
                slope = (points[j+1, 1] - points[j, 1]) / (points[j+1, 0] - points[j, 0])
                return points[j, 1] + slope * (pg - points[j, 0])
    return 0.0
