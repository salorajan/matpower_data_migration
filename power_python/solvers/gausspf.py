# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np

def gausspf(Ybus, Sbus, V0, pv, pq, ref, tol=1e-8, max_it=1000, verbose=True):
    """
    Solves power flow using the Gauss-Seidel method.
    Note: Much slower than Newton-Raphson.
    """
    V = V0.copy()
    nb = len(V)
    converged = False
    it = 0
    
    # Identify indices
    pv_idx = list(pv)
    pq_idx = list(pq)
    ref_idx = list(ref)
    
    if verbose:
        print(f"{'it':<4} {'max mismatch (p.u.)':<20}")
        print("-" * 25)

    while not converged and it < max_it:
        V_prev = V.copy()
        
        for i in range(nb):
            if i in ref_idx:
                continue
            
            # Sum_{j != i} Yij * Vj
            # We use the most recent voltage values (Seidel)
            sum_yv = 0
            # For efficiency in a real system we'd use sparse access
            # But for simplicity we use dense here
            # Ybus[i, :] @ V
            sum_yv = Ybus[i, :].toarray().flatten() @ V - Ybus[i, i] * V[i]
            
            if i in pq_idx:
                # Vi = (1/Yii) * ( (Pi - jQi)/Vi* - sum_yv )
                V[i] = (1.0 / Ybus[i, i]) * (np.conj(Sbus[i]) / np.conj(V[i]) - sum_yv)
            
            elif i in pv_idx:
                # 1. Update Reactive Power Injection Qi
                # Qi = -imag( Vi* * sum_yv_full )
                sum_yv_full = Ybus[i, :].toarray().flatten() @ V
                qi = -np.imag(np.conj(V[i]) * sum_yv_full)
                
                # 2. Update Vi while keeping |Vi| constant
                Sbus_i = np.real(Sbus[i]) + 1j * qi
                V[i] = (1.0 / Ybus[i, i]) * (np.conj(Sbus_i) / np.conj(V[i]) - sum_yv)
                V[i] = np.abs(V0[i]) * (V[i] / np.abs(V[i]))
        
        # Mismatch check
        mis = V * np.conj(Ybus @ V) - Sbus
        # Only check P for PV, P and Q for PQ
        F = np.concatenate([mis[pv].real, mis[pq].real, mis[pq].imag])
        normF = np.linalg.norm(F, np.inf)
        
        if verbose and (it % 10 == 0 or it < 5):
            print(f"{it:<4} {normF:<20.3e}")
            
        if normF < tol:
            converged = True
            break
        
        it += 1
        
    if verbose:
        if converged:
            print(f"Gauss-Seidel converged in {it} iterations.")
        else:
            print(f"Gauss-Seidel failed to converge after {it} iterations.")
            
    return V, converged, it
