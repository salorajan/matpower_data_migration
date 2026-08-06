# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import cvxpy as cp
import numpy as np
from ..core.constants import *
from ..network.admittance import make_ybus

def run_mp_opf(case, nt=6, verbose=True):
    """
    Solves a Multi-period DC Optimal Power Flow with Energy Storage and Ramping.
    Defaulting to nt=6 steps for a quick demonstration.
    
    Args:
        case: PowerCase object.
        nt: Number of time periods.
        verbose: Print progress.
        
    Returns:
        tuple: (results_dict, success)
    """
    case.to_internal()
    nb = len(case.bus)
    ng = len(case.gen)
    nl = len(case.branch)
    baseMVA = case.baseMVA

    # 1. Setup Network Matrices (DC)
    Ybus, _, _ = make_ybus(baseMVA, case.bus, case.branch)
    Bbus = Ybus.imag
    
    # 2. Extract Data
    Pd_base = case.bus[:, PD]
    stat = case.branch[:, BR_STATUS]
    f = case.branch[:, F_BUS].astype(int)
    t = case.branch[:, T_BUS].astype(int)
    b_line = 1.0 / case.branch[:, BR_X]
    
    # 3. Decision Variables
    Pg = cp.Variable((nt, ng))  # Gen real power (MW)
    Va = cp.Variable((nt, nb))  # Bus angles (radians)
    
    # Storage Variables
    ns = len(case.storage.get('idx', []))
    if ns > 0:
        Soc = cp.Variable((nt, ns))
        Pch = cp.Variable((nt, ns))
        Pdis = cp.Variable((nt, ns))
    
    # 4. Objective: Minimize Total cost over all time steps
    total_costs = []
    
    # Base load profile (if not provided, assume flat 1.0)
    profile = case.profiles.get('load', np.ones(nt))
    
    for t_step in range(nt):
        # Generation Costs
        for i in range(ng):
            if len(case.gencost) > i:
                model = case.gencost[i, MODEL]
                ncost = int(case.gencost[i, NCOST])
                if model == POLYNOMIAL and ncost == 3:
                    c2, c1, c0 = case.gencost[i, COST:COST+3]
                    total_costs.append(c2 * cp.square(Pg[t_step, i]) + c1 * Pg[t_step, i] + c0)
                elif model == POLYNOMIAL and ncost == 2:
                    c1, c0 = case.gencost[i, COST:COST+2]
                    total_costs.append(c1 * Pg[t_step, i] + c0)
            else:
                total_costs.append(cp.square(Pg[t_step, i]))
                
        if ns > 0:
            total_costs.append(0.01 * cp.sum(Pch[t_step, :] + Pdis[t_step, :]))

    objective = cp.Minimize(cp.sum(total_costs))
    
    # 5. Constraints
    constraints = []
    
    # Gen Connection Matrix (nb x ng)
    Cg = np.zeros((nb, ng))
    for i in range(ng):
        Cg[int(case.gen[i, GEN_BUS]), i] = 1.0

    # Storage Connection Matrix (nb x ns)
    if ns > 0:
        Cs = np.zeros((nb, ns))
        for i, gen_idx in enumerate(case.storage['idx']):
            Cs[int(case.gen[gen_idx, GEN_BUS]), i] = 1.0

    for t_idx in range(nt):
        # --- A. Nodal Power Balance ---
        bus_gen_inj = Cg @ Pg[t_idx, :]
        
        if ns > 0:
            bus_inj = bus_gen_inj + Cs @ (Pdis[t_idx, :] - Pch[t_idx, :])
        else:
            bus_inj = bus_gen_inj
                
        current_Pd = Pd_base * profile[t_idx]
        constraints += [ (Bbus @ Va[t_idx, :]) * baseMVA == bus_inj - current_Pd ]
        
        # --- B. Line Flow Limits ---
        for i in range(nl):
            if stat[i] > 0 and case.branch[i, RATE_A] > 0:
                flow = (Va[t_idx, f[i]] - Va[t_idx, t[i]]) * b_line[i] * baseMVA
                constraints += [ flow <= case.branch[i, RATE_A], flow >= -case.branch[i, RATE_A] ]
                
        # --- C. Gen Limits ---
        constraints += [ Pg[t_idx, :] >= case.gen[:, PMIN], Pg[t_idx, :] <= case.gen[:, PMAX] ]
        
        # --- D. Reference Bus ---
        ref = np.where(case.bus[:, BUS_TYPE] == REF)[0][0]
        constraints += [ Va[t_idx, ref] == 0 ]
        
        # --- E. Ramping Constraints ---
        if t_idx > 0:
            ramp_lim = case.gen[:, PMAX] * 0.3 # 30% ramping per step
            constraints += [ Pg[t_idx, :] - Pg[t_idx-1, :] <= ramp_lim ]
            constraints += [ Pg[t_idx-1, :] - Pg[t_idx, :] <= ramp_lim ]
            
        # --- F. Storage Dynamics ---
        if ns > 0:
            constraints += [ Pch[t_idx, :] >= 0, Pdis[t_idx, :] >= 0 ]
            constraints += [ Pch[t_idx, :] <= case.storage['MaxCharge'] ]
            constraints += [ Pdis[t_idx, :] <= case.storage['MaxDischarge'] ]
            
            eff_in = np.array(case.storage['InEff'])
            eff_out = np.array(case.storage['OutEff'])
            
            if t_idx == 0:
                prev_soc = np.array(case.storage['InitialSOC'])
            else:
                prev_soc = Soc[t_idx-1, :]
                
            constraints += [ Soc[t_idx, :] == prev_soc + cp.multiply(Pch[t_idx, :], eff_in) - cp.multiply(Pdis[t_idx, :], 1.0/eff_out) ]
            constraints += [ Soc[t_idx, :] >= case.storage['MinSOC'], Soc[t_idx, :] <= case.storage['MaxSOC'] ]

    # 6. Solve
    prob = cp.Problem(objective, constraints)
    prob.solve()
    
    if prob.status in ["optimal", "feasible"]:
        results = {
            "Pg": Pg.value,
            "Va": Va.value * 180 / np.pi,
            "Cost": prob.value,
            "profile": profile,
            "total_load": np.sum(Pd_base)
        }
        if ns > 0:
            results["Soc"] = Soc.value
            results["Pch"] = Pch.value
            results["Pdis"] = Pdis.value
        return results, True
    else:
        return None, False

def print_mp_results(results, nt, ns=0):
    """Prints a summary of the multi-period dispatch."""
    print("\n" + "="*90)
    print(f"{'MULTI-PERIOD DISPATCH SUMMARY':^90}")
    print("="*90)
    print(f"{'Step':<6} {'Load Mult':<10} {'Total Gen (MW)':<15} {'Total Load (MW)':<15}", end="")
    if ns > 0:
        print(f" {'Total SOC (MWh)':<15}")
    else:
        print("")
    print("-" * 75)
    
    for t in range(nt):
        mult = results['profile'][t]
        gen_t = np.sum(results['Pg'][t, :])
        load_t = results['total_load'] * mult
        print(f"{t:<6} {mult:<10.2f} {gen_t:<15.2f} {load_t:<15.2f}", end="")
        if ns > 0:
            soc_t = np.sum(results['Soc'][t, :])
            print(f" {soc_t:<15.2f}")
        else:
            print("")
    print("="*90 + "\n")
