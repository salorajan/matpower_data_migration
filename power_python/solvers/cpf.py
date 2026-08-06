# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from ..core.constants import *
from ..network.admittance import make_ybus
from .newtonpf import newtonpf

def run_cpf(case, verbose=True):
    """
    Solves a Continuation Power Flow (CPF).
    Increases load until it hits the nose point (maximum loadability).
    """
    case.to_internal()
    nb = len(case.bus)
    baseMVA = case.baseMVA
    
    # 1. Base Case
    Pload_base = case.bus[:, PD].copy()
    Qload_base = case.bus[:, QD].copy()
    
    # Target direction: Increase all loads proportionally
    # Or we can specify a specific load increase pattern.
    P_inc = Pload_base.copy()
    Q_inc = Qload_base.copy()
    
    # Indices
    ref = np.where(case.bus[:, BUS_TYPE] == REF)[0]
    pv = np.where(case.bus[:, BUS_TYPE] == PV)[0]
    pq = np.where(case.bus[:, BUS_TYPE] == PQ)[0]
    
    lam = 0.0
    step = 0.1
    max_lam = 5.0
    
    results = [] # Store (lam, Vm_avg)
    
    if verbose:
        print(f"{'Lambda':<10} {'Status':<15} {'Avg Vm':<10}")
        print("-" * 35)

    current_case = case
    
    while lam <= max_lam:
        # Update load
        current_case.bus[:, PD] = Pload_base + lam * P_inc
        current_case.bus[:, QD] = Qload_base + lam * Q_inc
        
        # Solve AC PF
        # We use a copy to avoid corrupting the initial case if it fails
        case_temp = current_case # In-place is fine for this simple loop
        Ybus, _, _ = make_ybus(baseMVA, case_temp.bus, case_temp.branch)
        # Sbus update needed for new load
        from ..network.power_balance import make_sbus
        Sbus = make_sbus(baseMVA, case_temp.bus, case_temp.gen)
        
        # We reuse the previous solution as initial guess
        V0 = case_temp.bus[:, VM] * np.exp(1j * np.pi / 180 * case_temp.bus[:, VA])
        
        V, converged, it = newtonpf(Ybus, Sbus, V0, pv, pq, ref, verbose=False)
        
        if not converged:
            if verbose:
                print(f"{lam:<10.3f} {'Failed':<15}")
            break
            
        # Success
        vm_avg = np.mean(np.abs(V))
        if verbose:
            print(f"{lam:<10.3f} {'Converged':<15} {vm_avg:<10.4f}")
            
        results.append((lam, vm_avg))
        
        # Update case for next step
        current_case.bus[:, VM] = np.abs(V)
        current_case.bus[:, VA] = np.angle(V) * 180 / np.pi
        
        lam += step
        
    if verbose:
        print(f"\nMax Loadability Factor (approx): {results[-1][0]:.2f}")
        
    return results
