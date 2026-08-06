# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from ..core.constants import *
from ..network.branch_flows import calculate_branch_flows

def run_radial_pf(case, max_it=20, tol=1e-6, verbose=True):
    """
    Solves Power Flow for radial distribution systems using the 
    Backward-Forward Sweep (BFS) method.
    
    Args:
        case: PowerCase object.
        max_it: Maximum iterations.
        tol: Convergence tolerance (MW mismatch).
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, success)
    """
    case.to_internal()
    nb = len(case.bus)
    nl = len(case.branch)
    baseMVA = case.baseMVA
    
    # 1. Setup Topology
    # BFS requires a radial structure. We assume bus 0 (slack) is the root.
    # Build adjacency list
    adj = [[] for _ in range(nb)]
    for i in range(nl):
        if case.branch[i, BR_STATUS] > 0:
            f = int(case.branch[i, F_BUS])
            t = int(case.branch[i, T_BUS])
            adj[f].append((t, i)) # (to_bus, branch_idx)
            
    # Determine levels (BFS tree)
    root = np.where(case.bus[:, BUS_TYPE] == REF)[0][0]
    levels = []
    parent = [-1] * nb
    branch_to_parent = [-1] * nb
    
    queue = [root]
    visited = {root}
    while queue:
        levels.append(queue[:])
        next_queue = []
        for u in queue:
            for v, br_idx in adj[u]:
                if v not in visited:
                    visited.add(v)
                    parent[v] = u
                    branch_to_parent[v] = br_idx
                    next_queue.append(v)
        queue = next_queue
        
    if len(visited) < nb:
        if verbose: print("Warning: System is not fully connected or not radial from root.")

    # 2. Initialization
    V = np.ones(nb, dtype=complex) * (case.bus[:, VM] * np.exp(1j * np.pi/180 * case.bus[:, VA]))
    # For BFS, we usually start with flat start 1.0 pu at all buses, 
    # except the slack bus which is fixed.
    V_slack = V[root]
    
    S_load = (case.bus[:, PD] + 1j * case.bus[:, QD]) / baseMVA
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'RADIAL POWER FLOW (BFS)':^80}")
        print("="*80)

    success = False
    for it in range(max_it):
        # --- A. Backward Sweep: Calculate branch currents/powers ---
        # Start from the leaves and move to the root
        S_branch = np.zeros(nl, dtype=complex)
        I_bus = np.zeros(nb, dtype=complex)
        
        # Power injections at buses (Loads)
        # S = V * conj(I) => I = conj(S/V)
        I_inj = np.conj(S_load / V)
        
        # Traverse levels in reverse
        for level in reversed(levels):
            for v in level:
                if v == root: continue
                
                # Total current at bus v = Injection + currents to children
                # (For radial, I_branch_to_parent = I_inj_v + sum(I_child_branches))
                I_v = I_inj[v]
                # Add currents from children
                for child, _ in adj[v]:
                    if parent[child] == v:
                        br_idx = branch_to_parent[child]
                        # Current from branch (v->child) at bus v
                        # Simplified: I_branch = I_inj_child + sum(I_grandchild_branches)
                        # We'll accumulate this
                        pass 
                
                # Actually, BFS for power is easier:
                # S_to_parent = S_at_bus_v + Losses_in_branch_to_parent
                pass
                
        # Re-implementing with current summation (Standard BFS)
        I_br = np.zeros(nl, dtype=complex)
        I_node = I_inj.copy()
        
        for level in reversed(levels[1:]): # Exclude root
            for v in level:
                br_idx = branch_to_parent[v]
                I_br[br_idx] = I_node[v]
                u = parent[v]
                I_node[u] += I_node[v] # Add current to parent's accumulation
                
        # --- B. Forward Sweep: Calculate bus voltages ---
        # Start from root and move to leaves
        max_v_diff = 0
        V_old = V.copy()
        
        for level in levels:
            for u in level:
                for v, br_idx in adj[u]:
                    if parent[v] == u:
                        # Vv = Vu - I_br * Z_br
                        r = case.branch[br_idx, BR_R]
                        x = case.branch[br_idx, BR_X]
                        z = r + 1j*x
                        V[v] = V[u] - I_br[br_idx] * z
                        
        # Check Convergence
        mismatch = np.max(np.abs(V - V_old))
        if verbose:
            print(f"Iteration {it+1}: Max Voltage Update = {mismatch:.4e}")
            
        if mismatch < tol:
            success = True
            break
            
    if success:
        case.bus[:, VM] = np.abs(V)
        case.bus[:, VA] = np.angle(V) * 180 / np.pi
        
        # Calculate Slack Generation
        # S_slack = V_slack * conj(sum(I_from_slack))
        I_from_slack = 0j
        for v, br_idx in adj[root]:
            if parent[v] == root:
                I_from_slack += I_br[br_idx]
        
        S_slack = V[root] * np.conj(I_from_slack) * baseMVA
        
        # Update slack gen in case.gen
        slack_gen_idx = np.where(case.gen[:, GEN_BUS] == root)[0]
        if len(slack_gen_idx) > 0:
            case.gen[slack_gen_idx[0], PG] = S_slack.real
            case.gen[slack_gen_idx[0], QG] = S_slack.imag

        # Update branch flows
        pf, qf, pt, qt = calculate_branch_flows(baseMVA, case.bus, case.branch, V)
        case.branch[:, PF], case.branch[:, QF] = pf, qf
        case.branch[:, PT], case.branch[:, QT] = pt, qt
        if verbose: print(f"Radial PF Converged in {it+1} iterations.")
    else:
        if verbose: print("Radial PF failed to converge.")
        
    return case, success
