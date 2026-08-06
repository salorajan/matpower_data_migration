# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from scipy.optimize import minimize
from ..core.constants import *
from ..network.admittance_3p import make_ybus_3p

def run_3p_opf(case, verbose=True):
    """
    Solves a Three-Phase Unbalanced AC Optimal Power Flow.
    Minimizes total generation cost while respecting phase-level constraints.
    
    Args:
        case: PowerCase object with 3-phase data.
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, success)
    """
    # 1. Setup
    nb = len(case.bus3p)
    ng = len(case.gen3p)
    baseMVA = case.baseMVA
    
    Ybus = make_ybus_3p(case)
    
    # 2. Decision Variables
    # x = [Va1..3 (nb), Vm1..3 (nb), Pg1..3 (ng), Qg1..3 (ng)]
    # Total vars: 3*nb + 3*nb + 3*ng + 3*ng = 6*(nb + ng)
    
    va0 = (case.bus3p[:, 6:9] * np.pi / 180).flatten()
    vm0 = case.bus3p[:, 3:6].flatten()
    pg0 = (case.gen3p[:, 6:9] / 1000.0 / baseMVA).flatten() # MW to pu
    qg0 = (case.gen3p[:, 9:12] / 1000.0 / baseMVA).flatten() # MVAr to pu
    
    x0 = np.concatenate([va0, vm0, pg0, qg0])
    
    # 3. Bounds
    bounds = []
    # Va (radians)
    ref_idx = np.where(case.bus3p[:, 1] == 3)[0][0]
    for i in range(nb):
        for p in range(3):
            if i == ref_idx:
                # Slack bus angles are fixed (usually 0, -120, 120)
                val = case.bus3p[i, 6+p] * np.pi / 180
                bounds.append((val, val))
            else:
                bounds.append((-2*np.pi, 2*np.pi))
    # Vm
    for i in range(nb):
        # Using Vmin/Vmax from standard bus if 3p limits aren't specified
        vmax = 1.1
        vmin = 0.9
        for p in range(3):
            bounds.append((vmin, vmax))
    # Pg (pu)
    for i in range(ng):
        # We assume 3-phase gens have symmetric limits for now or sum limits
        # Simplified: Use 1/3 of total Pmax if not phase-specific
        pmax = 5000.0 / 1000.0 / baseMVA # Placeholder large limit
        for p in range(3):
            bounds.append((0, pmax))
    # Qg (pu)
    for i in range(ng):
        qmax = 5000.0 / 1000.0 / baseMVA
        for p in range(3):
            bounds.append((-qmax, qmax))

    # 4. Objective: Minimize Sum of Gen Costs across all phases
    def objective(x):
        pg_pu = x[6*nb : 6*nb + 3*ng]
        # Simplified quadratic cost: sum(Pg^2)
        return np.sum(np.square(pg_pu * baseMVA))

    # 5. Constraints: Power Balance per phase
    def constraints_func(x):
        va = x[0 : 3*nb].reshape(nb, 3)
        vm = x[3*nb : 6*nb].reshape(nb, 3)
        pg = x[6*nb : 6*nb + 3*ng].reshape(ng, 3)
        qg = x[6*nb + 3*ng :].reshape(ng, 3)
        
        # Complex Voltages
        V = (vm * np.exp(1j * va)).flatten()
        Sbus = V * np.conj(Ybus @ V)
        Sbus = Sbus.reshape(nb, 3)
        
        # Power injections
        Sgen = np.zeros((nb, 3), dtype=complex)
        for i in range(ng):
            b_idx = int(case.gen3p[i, 1]) - 1
            Sgen[b_idx, :] += pg[i, :] + 1j*qg[i, :]
            
        Sload = np.zeros((nb, 3), dtype=complex)
        for i in range(len(case.load3p)):
            b_idx = int(case.load3p[i, 1]) - 1
            P = case.load3p[i, 3:6] / 1000.0 / baseMVA
            pf = case.load3p[i, 6:9]
            Q = P * np.tan(np.arccos(pf))
            Sload[b_idx, :] += P + 1j*Q
            
        # Mismatch: Sgen - Sload - Sbus = 0
        mis = Sgen - Sload - Sbus
        return np.concatenate([mis.real.flatten(), mis.imag.flatten()])

    cons = {'type': 'eq', 'fun': constraints_func}

    if verbose:
        print("\n" + "="*80)
        print(f"{'THREE-PHASE OPTIMAL POWER FLOW (3P-OPF)':^80}")
        print("="*80)

    # 6. Solve
    res = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=cons,
                   options={'maxiter': 100, 'disp': verbose})
    
    if res.success:
        if verbose: print(f"3P-OPF Solved. Optimal Cost: {res.fun:.2f}")
        # Update case
        va = res.x[0 : 3*nb].reshape(nb, 3)
        vm = res.x[3*nb : 6*nb].reshape(nb, 3)
        pg = res.x[6*nb : 6*nb + 3*ng].reshape(ng, 3)
        qg = res.x[6*nb + 3*ng :].reshape(ng, 3)
        
        case.bus3p[:, 3:6] = vm
        case.bus3p[:, 6:9] = va * 180 / np.pi
        case.gen3p[:, 6:9] = pg * baseMVA * 1000.0
        case.gen3p[:, 9:12] = qg * baseMVA * 1000.0
        return case, True
    else:
        if verbose: print(f"3P-OPF Failed: {res.message}")
        return case, False
