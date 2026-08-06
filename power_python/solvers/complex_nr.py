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
        A = diags(np.conj(I)).toarray()
        B = (diags(V) @ np.conj(Ybus)).toarray()
        
        n_pq, n_pv = len(pq), len(pv)
        dim = 2*n_pq + 2*n_pv
        R = np.zeros(dim, dtype=complex)
        J = np.zeros((dim, dim), dtype=complex)
        
        # Mapping
        # Row 0..n_pq-1: PQ S mismatch
        # Row n_pq..2*n_pq-1: PQ S* mismatch
        # Row 2*n_pq..2*n_pq+n_pv-1: PV P mismatch
        # Row 2*n_pq+n_pv..dim-1: PV |V|^2 mismatch
        
        # Column 0..n_pq-1: dV_pq
        # Column n_pq..2*n_pq-1: dV*_pq
        # Column 2*n_pq..2*n_pq+n_pv-1: dV_pv
        # Column 2*n_pq+n_pv..dim-1: dV*_pv

        # PQ Equations
        for i, idx in enumerate(pq):
            R[i] = -mis[idx]
            R[n_pq + i] = -np.conj(mis[idx])
            # w.r.t PQ vars
            for j, jdx in enumerate(pq):
                J[i, j] = A[idx, jdx]
                J[i, n_pq+j] = B[idx, jdx]
                J[n_pq+i, j] = np.conj(B[idx, jdx])
                J[n_pq+i, n_pq+j] = np.conj(A[idx, jdx])
            # w.r.t PV vars
            for j, jdx in enumerate(pv):
                J[i, 2*n_pq + j] = A[idx, jdx]
                J[i, 2*n_pq + n_pv + j] = B[idx, jdx]
                J[n_pq+i, 2*n_pq + j] = np.conj(B[idx, jdx])
                J[n_pq+i, 2*n_pq + n_pv + j] = np.conj(A[idx, jdx])

        # PV Equations
        for i, idx in enumerate(pv):
            R[2*n_pq + i] = -mis[idx].real
            R[2*n_pq + n_pv + i] = -(np.abs(V[idx])**2 - case.bus[idx, VM]**2)
            # Row 1: dP/dV = 0.5 * (dS/dV + dS*/dV)
            for j, jdx in enumerate(pq):
                J[2*n_pq+i, j] = 0.5 * (A[idx, jdx] + np.conj(B[idx, jdx]))
                J[2*n_pq+i, n_pq+j] = 0.5 * (B[idx, jdx] + np.conj(A[idx, jdx]))
            for j, jdx in enumerate(pv):
                J[2*n_pq+i, 2*n_pq+j] = 0.5 * (A[idx, jdx] + np.conj(B[idx, jdx]))
                J[2*n_pq+i, 2*n_pq+n_pv+j] = 0.5 * (B[idx, jdx] + np.conj(A[idx, jdx]))
                
            # Row 2: d|V|^2
            J[2*n_pq + n_pv + i, 2*n_pq + i] = np.conj(V[idx])
            J[2*n_pq + n_pv + i, 2*n_pq + n_pv + i] = V[idx]

        # 4. Solve
        dx = np.linalg.solve(J, R)
        
        # 5. Update
        V[pq] += dx[0:n_pq]
        V[pv] += dx[2*n_pq : 2*n_pq+n_pv]
        
    if success:
        if verbose: print(f"Complex NR Converged in {it+1} iterations.")
        case.bus[:, VM], case.bus[:, VA] = np.abs(V), np.angle(V) * 180 / np.pi
        from ..network.branch_flows import calculate_branch_flows
        pf, qf, pt, qt = calculate_branch_flows(baseMVA, case.bus, case.branch, V)
        case.branch[:, PF], case.branch[:, QF] = pf, qf
        case.branch[:, PT], case.branch[:, QT] = pt, qt
    return case, success
