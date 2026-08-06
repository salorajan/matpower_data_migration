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

def run_dc_opf(case, verbose=True):
    """
    Solves a DC Optimal Power Flow using CVXPY.
    """
    case.to_internal()
    nb = len(case.bus)
    ng = len(case.gen)
    nl = len(case.branch)
    baseMVA = case.baseMVA
    
    # 1. Constants and Indices
    ref_idx = np.where(case.bus[:, BUS_TYPE] == REF)[0][0]
    
    # 2. Build DC Network Matrices
    stat = case.branch[:, BR_STATUS]
    X = case.branch[:, BR_X]
    tap = case.branch[:, TAP]
    tap[tap == 0] = 1.0
    b_line = stat / (X * tap)
    
    Bbus = np.zeros((nb, nb))
    f = case.branch[:, F_BUS].astype(int)
    t = case.branch[:, T_BUS].astype(int)
    for i in range(nl):
        if stat[i] > 0:
            Bbus[f[i], f[i]] += b_line[i]
            Bbus[t[i], t[i]] += b_line[i]
            Bbus[f[i], t[i]] -= b_line[i]
            Bbus[t[i], f[i]] -= b_line[i]
            
    # 3. Decision Variables
    Pg = cp.Variable(ng)
    Va = cp.Variable(nb)
    
    has_reserves = bool(case.reserves)
    if has_reserves:
        R = cp.Variable(ng)
    
    # 4. Objective Function & Constraints
    costs = []
    constraints = []
    has_cost = len(case.gencost) >= ng
    
    for i in range(ng):
        if has_cost:
            model = int(case.gencost[i, MODEL])
            ncost = int(case.gencost[i, NCOST])
            if model == POLYNOMIAL:
                cost_params = case.gencost[i, COST:COST+ncost]
                if ncost == 3:
                    c2, c1, c0 = cost_params
                    costs.append(c2 * cp.square(Pg[i]) + c1 * Pg[i] + c0)
                elif ncost == 2:
                    c1, c0 = cost_params
                    costs.append(c1 * Pg[i] + c0)
            elif model == PW_LINEAR:
                pts = case.gencost[i, COST : COST + 2*ncost].reshape(-1, 2)
                t_var = cp.Variable()
                for j in range(len(pts) - 1):
                    x1, y1 = pts[j]
                    x2, y2 = pts[j+1]
                    if x2 > x1:
                        slope = (y2 - y1) / (x2 - x1)
                        constraints.append(t_var >= slope * (Pg[i] - x1) + y1)
                costs.append(t_var)
        else:
            costs.append(cp.square(Pg[i]))
            
    if has_reserves:
        res_costs = np.array(case.reserves.get("cost", np.zeros(ng)))
        costs.append(res_costs @ R)
    
    objective = cp.Minimize(cp.sum(costs))
    
    # 5. Constraints Continued
    if has_reserves:
        constraints += [Pg >= case.gen[:, PMIN], Pg + R <= case.gen[:, PMAX], R >= 0]
        if "qty" in case.reserves:
            constraints += [R <= np.array(case.reserves["qty"])]
        zones = np.array(case.reserves["zones"])
        req = np.array(case.reserves["req"])
        constraints += [zones @ R >= req]
    else:
        constraints += [Pg >= case.gen[:, PMIN], Pg <= case.gen[:, PMAX]]
    
    constraints += [Va[ref_idx] == 0]
    
    Pd = case.bus[:, PD]
    bus_gen_map = np.zeros((nb, ng))
    for i in range(ng):
        bus_gen_map[int(case.gen[i, GEN_BUS]), i] = 1.0
        
    bus_gen_injections = bus_gen_map @ Pg
    bal_cons = bus_gen_injections - Pd == (Bbus @ Va) * baseMVA
    constraints += [bal_cons]
    
    flow_cons_pos = []
    flow_cons_neg = []
    flow_indices = []
    for i in range(nl):
        if stat[i] > 0 and case.branch[i, RATE_A] > 0:
            flow = (Va[f[i]] - Va[t[i]]) * b_line[i] * baseMVA
            p_con = flow <= case.branch[i, RATE_A]
            n_con = flow >= -case.branch[i, RATE_A]
            constraints += [p_con, n_con]
            flow_cons_pos.append(p_con)
            flow_cons_neg.append(n_con)
            flow_indices.append(i)
            
    # 6. Solve
    prob = cp.Problem(objective, constraints)
    prob.solve(verbose=verbose)
    
    if prob.status in ["optimal", "feasible"]:
        if verbose:
            print(f"DC-OPF Solved. Optimal Cost: {prob.value:.2f}")
        case.gen[:, PG] = Pg.value
        case.bus[:, VA] = Va.value * 180 / np.pi
        case.bus[:, VM] = 1.0
        case.bus[:, LAM_P] = -bal_cons.dual_value
        
        case.branch[:, MU_SF] = 0.0
        case.branch[:, MU_ST] = 0.0
        for i, idx in enumerate(flow_indices):
            case.branch[idx, MU_SF] = flow_cons_pos[i].dual_value
            case.branch[idx, MU_ST] = flow_cons_neg[i].dual_value
            
        if has_reserves:
            case.reserves["R"] = R.value
        return case, True
    else:
        if verbose:
            print(f"DC-OPF Failed: {prob.status}")
        return case, False
