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

def run_sdp_opf(case, verbose=True):
    """
    Solves the AC Optimal Power Flow using Semidefinite Programming (SDP) Relaxation.
    Based on the method by Lavaei & Low (2012) and Molzahn's research.
    
    Relaxes the rank-1 constraint on W = V * V^H to W >= 0.
    """
    case.to_internal()
    nb = len(case.bus)
    ng = len(case.gen)
    baseMVA = case.baseMVA
    
    # 1. Setup Network Matrices
    Ybus, _, _ = make_ybus(baseMVA, case.bus, case.branch)
    
    # 2. Decision Variables
    W = cp.Variable((nb, nb), hermitian=True)
    Pg = cp.Variable(ng)
    Qg = cp.Variable(ng)
    
    # 3. Objective
    costs = []
    has_cost = len(case.gencost) >= ng
    for i in range(ng):
        if has_cost:
            model = int(case.gencost[i, MODEL])
            ncost = int(case.gencost[i, NCOST])
            if model == POLYNOMIAL:
                # Use linear cost coefficient for the SDP demonstration
                c1 = case.gencost[i, COST + ncost - 2]
                costs.append(c1 * Pg[i] * baseMVA)
        else:
            costs.append(Pg[i])
            
    objective = cp.Minimize(cp.sum(costs))
    
    # 4. Constraints
    constraints = [W >> 0]
    
    bus_gen_indices = [[] for _ in range(nb)]
    for i in range(ng):
        bus_gen_indices[int(case.gen[i, GEN_BUS])].append(i)
        
    for i in range(nb):
        # Power injections
        # P_inj = Re((Ybus @ W)[i, i]) = Re(Ybus[i, :] @ W[:, i])
        # Q_inj = Im((Ybus @ W)[i, i]) = Im(Ybus[i, :] @ W[:, i])
        V_inj = Ybus[i, :] @ W[:, i]
        
        bus_pg = cp.sum([Pg[g] for g in bus_gen_indices[i]]) if bus_gen_indices[i] else 0
        constraints.append(cp.real(V_inj) == bus_pg - case.bus[i, PD] / baseMVA)
        
        bus_qg = cp.sum([Qg[g] for g in bus_gen_indices[i]]) if bus_gen_indices[i] else 0
        constraints.append(cp.imag(V_inj) == bus_qg - case.bus[i, QD] / baseMVA)
        
        # Use cp.real for voltage limits to avoid CVXPY complex inequality error
        constraints.append(cp.real(W[i, i]) >= case.bus[i, VMIN]**2)
        constraints.append(cp.real(W[i, i]) <= case.bus[i, VMAX]**2)
        
    constraints.append(Pg >= case.gen[:, PMIN] / baseMVA)
    constraints.append(Pg <= case.gen[:, PMAX] / baseMVA)
    constraints.append(Qg >= case.gen[:, QMIN] / baseMVA)
    constraints.append(Qg <= case.gen[:, QMAX] / baseMVA)
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'SDP-RELAXATION OPF (MOLZAHN METHOD)':^80}")
        print("="*80)
        
    prob = cp.Problem(objective, constraints)
    try:
        prob.solve(solver=cp.SCS, verbose=verbose)
    except Exception as e:
        if verbose: print(f"Solver Error: {e}")
        return case, False
    
    if prob.status in ["optimal", "feasible"]:
        if verbose:
            print(f"SDP-OPF Solved. Lower Bound Cost: ${prob.value:,.2f}")
        
        # Verify rank-1
        eigs = np.linalg.eigvalsh(W.value)
        eigs = np.sort(eigs)[::-1]
        gap = eigs[0] / (eigs[1] + 1e-12) if len(eigs) > 1 else float('inf')
        
        if verbose:
            print(f"Rank-1 Ratio: {gap:.2e}")
                
        u, s, vh = np.linalg.svd(W.value)
        V_rec = np.sqrt(s[0]) * u[:, 0]
        
        case.bus[:, VM], case.bus[:, VA] = np.abs(V_rec), np.angle(V_rec) * 180 / np.pi
        case.gen[:, PG], case.gen[:, QG] = Pg.value * baseMVA, Qg.value * baseMVA
        return case, True
    else:
        return case, False
