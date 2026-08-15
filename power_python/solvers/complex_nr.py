# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from scipy.sparse import csr_matrix, bmat, diags
from scipy.sparse.linalg import spsolve
from ..core.constants import *
from ..network.admittance import make_ybus
from ..network.power_balance import make_sbus

def run_complex_nr(case, max_it=10, tol=1e-8, verbose=True):
    """
    Solves Power Flow using the Complex-Variable Newton-Raphson (CVNR) method, 
    based on Wirtinger Calculus. 
    """
    case.to_internal()
    nb = len(case.bus)
    baseMVA = case.baseMVA
    
    # 0. Apply generator setpoints
    for i in range(len(case.gen)):
        if case.gen[i, GEN_STATUS] > 0:
            bus_idx = int(case.gen[i, GEN_BUS])
            if case.bus[bus_idx, BUS_TYPE] in [PV, REF]:
                case.bus[bus_idx, VM] = case.gen[i, VG]

    # 1. Network Setup
    Ybus, _, _ = make_ybus(baseMVA, case.bus, case.branch)
    Sbus = make_sbus(baseMVA, case.bus, case.gen)
    
    ref = np.where(case.bus[:, BUS_TYPE] == REF)[0]
    pv = np.where(case.bus[:, BUS_TYPE] == PV)[0]
    pq = np.where(case.bus[:, BUS_TYPE] == PQ)[0]
    
    V = case.bus[:, VM] * np.exp(1j * np.pi / 180 * case.bus[:, VA])
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'COMPLEX-VARIABLE NEWTON-RAPHSON (WIRTINGER)':^80}")
        print("="*80)
        print(f"{'Iter':<10} {'Max Mismatch (pu)':<20}")
        print("-" * 40)

    success = False
    for it in range(max_it):
        I = Ybus @ V
        mis = V * np.conj(I) - Sbus
        
        # Mismatches
        norm_pq = np.abs(mis[pq])
        norm_pv = np.abs(mis[pv].real)
        norm_v = np.abs(np.abs(V[pv])**2 - case.bus[pv, VM]**2)
        
        max_mis = np.max(np.concatenate([norm_pq, norm_pv, norm_v])) if len(pq)+len(pv) > 0 else 0
        if verbose: print(f"{it:<10} {max_mis:.4e}")
        if max_mis < tol:
            success = True
            break
            
        # 3. Wirtinger Derivatives
        A = diags(np.conj(I)).tocsr()
        B = (diags(V).tocsr() @ np.conj(Ybus)).tocsr()
        
        n_pq, n_pv = len(pq), len(pv)
        
        # Slices of A and B
        A_pq_pq = A[pq, :][:, pq]
        A_pq_pv = A[pq, :][:, pv]
        B_pq_pq = B[pq, :][:, pq]
        B_pq_pv = B[pq, :][:, pv]
        
        A_pv_pq = A[pv, :][:, pq]
        A_pv_pv = A[pv, :][:, pv]
        B_pv_pq = B[pv, :][:, pq]
        B_pv_pv = B[pv, :][:, pv]
        
        # Build block matrix J
        Z_pv_pq = csr_matrix((n_pv, n_pq))
        D_conj_V = diags(np.conj(V[pv]))
        D_V = diags(V[pv])
        
        J = bmat([
            [A_pq_pq, B_pq_pq, A_pq_pv, B_pq_pv],
            [np.conj(B_pq_pq), np.conj(A_pq_pq), np.conj(B_pq_pv), np.conj(A_pq_pv)],
            [0.5 * (A_pv_pq + np.conj(B_pv_pq)), 0.5 * (B_pv_pq + np.conj(A_pv_pq)), 0.5 * (A_pv_pv + np.conj(B_pv_pv)), 0.5 * (B_pv_pv + np.conj(A_pv_pv))],
            [Z_pv_pq, Z_pv_pq, D_conj_V, D_V]
        ], format='csr')
        
        # Residual mismatch vector R
        R = np.concatenate([
            -mis[pq],
            -np.conj(mis[pq]),
            -mis[pv].real,
            -(np.abs(V[pv])**2 - case.bus[pv, VM]**2)
        ])
        
        # 4. Solve using sparse solver
        dx = spsolve(J, R)
        
        # 5. Update
        V[pq] += dx[0:n_pq]
        V[pv] += dx[2*n_pq : 2*n_pq + n_pv]
        
    if success:
        if verbose: print(f"Complex NR Converged in {it+1} iterations.")
        case.bus[:, VM], case.bus[:, VA] = np.abs(V), np.angle(V) * 180 / np.pi
        from ..network.branch_flows import calculate_branch_flows
        pf, qf, pt, qt = calculate_branch_flows(baseMVA, case.bus, case.branch, V)
        case.branch[:, PF], case.branch[:, QF] = pf, qf
        case.branch[:, PT], case.branch[:, QT] = pt, qt
        case.update_generator_power()
    return case, success
