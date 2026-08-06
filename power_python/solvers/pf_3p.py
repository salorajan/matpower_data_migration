# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from ..core.constants import *
from ..network.admittance_3p import make_ybus_3p

def run_3p_pf(case, max_it=20, tol=1e-6, verbose=True):
    """
    Solves a 3-Phase Unbalanced AC Power Flow using the Z-bus Iterative Method.
    (Appropriate for distribution systems).
    
    Args:
        case: PowerCase object with 3-phase data.
        max_it: Max iterations.
        tol: Mismatch tolerance (pu).
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, success)
    """
    # 1. Setup
    nb = len(case.bus3p)
    baseMVA = case.baseMVA
    
    Ybus = make_ybus_3p(case)
    
    # Identify slack bus (Bus type 3 in bus3p)
    ref_idx = np.where(case.bus3p[:, 1] == 3)[0]
    if len(ref_idx) == 0: ref = 0
    else: ref = ref_idx[0]
    
    load_indices = np.setdiff1d(np.arange(nb), [ref])
    
    # Partition Ybus
    # Y = [ Yss Ysl ; Yls Yll ]
    # For Z-bus method, we need Yll_inv
    # Build indices for all phases
    s_idx = np.arange(3*ref, 3*ref+3)
    l_idx = []
    for i in load_indices:
        l_idx.extend([3*i, 3*i+1, 3*i+2])
    l_idx = np.array(l_idx)
    
    Yss = Ybus[np.ix_(s_idx, s_idx)]
    Ysl = Ybus[np.ix_(s_idx, l_idx)]
    Yls = Ybus[np.ix_(l_idx, s_idx)]
    Yll = Ybus[np.ix_(l_idx, l_idx)]
    
    # Initialize Voltages
    V = np.zeros(3*nb, dtype=complex)
    for i in range(nb):
        vmag = case.bus3p[i, 3:6]
        vang = case.bus3p[i, 6:9] * np.pi / 180
        V[3*i : 3*i+3] = vmag * np.exp(1j * vang)
        
    V_slack = V[s_idx]
    
    # Scheduled S injections (all phases)
    S_sched = np.zeros(3*nb, dtype=complex)
    
    # Loads
    for i in range(len(case.load3p)):
        bus_idx = int(case.load3p[i, 1]) - 1
        P = case.load3p[i, 3:6] / 1000.0 # Convert to MW
        pf = case.load3p[i, 6:9]
        Q = P * np.tan(np.arccos(pf))
        S_sched[3*bus_idx : 3*bus_idx+3] -= (P + 1j*Q) / baseMVA
        
    # Generators (except slack)
    for i in range(len(case.gen3p)):
        bus_idx = int(case.gen3p[i, 1]) - 1
        if bus_idx == ref: continue
        P = case.gen3p[i, 6:9] / 1000.0
        Q = case.gen3p[i, 9:12] / 1000.0
        S_sched[3*bus_idx : 3*bus_idx+3] += (P + 1j*Q) / baseMVA

    if verbose:
        print("\n" + "="*80)
        print(f"{'THREE-PHASE Z-BUS POWER FLOW':^80}")
        print("="*80)

    # 2. Solver Loop (Z-bus)
    success = False
    V_load = V[l_idx]
    S_load_sched = S_sched[l_idx]
    
    # Pre-calculate Constant Vector from Slack
    V_zero_load = -np.linalg.solve(Yll, Yls @ V_slack)
    
    Yll_inv = np.linalg.inv(Yll)

    for it in range(max_it):
        # 1. Injection Currents: I = conj(S/V)
        I_inj = np.conj(S_load_sched / V_load)
        
        # 2. Solve for new voltages
        V_load_new = V_zero_load + Yll_inv @ I_inj
        
        # 3. Check Mismatch
        diff = np.max(np.abs(V_load_new - V_load))
        if verbose:
            print(f"Iteration {it+1}: Max Voltage Change = {diff:.4e}")
            
        V_load = V_load_new
        if diff < tol:
            success = True
            break
            
    if success:
        if verbose: print(f"3-Phase PF Converged in {it+1} iterations.")
        V[l_idx] = V_load
        # Update case
        case.bus3p[:, 3:6] = np.abs(V).reshape(-1, 3)
        case.bus3p[:, 6:9] = (np.angle(V) * 180 / np.pi).reshape(-1, 3)
    else:
        if verbose: print("3-Phase PF failed to converge.")
        
    return case, success
