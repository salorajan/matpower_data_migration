# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from scipy.sparse.linalg import spsolve

def fdpf(Ybus, Sbus, V0, pv, pq, ref, tol=1e-8, max_it=100, verbose=True):
    """
    Solves power flow using the Fast Decoupled Power Flow method (XB version).
    """
    V = V0.copy()
    nb = len(V)
    
    # Indices
    pvpq = np.concatenate([pv, pq])
    
    # Matrices B' and B''
    # B' is nb-1 x nb-1 (slack removed)
    # B'' is npq x npq (slack and PV removed)
    B = -Ybus.imag
    
    # Standard FDPF XB version:
    # B' neglects R and shunt, B'' neglects tap shift
    # For simplicity, we'll use the imag(Ybus) sub-matrices
    Bp = B[np.ix_(pvpq, pvpq)]
    Bpp = B[np.ix_(pq, pq)]
    
    converged = False
    it = 0
    
    if verbose:
        print(f"{'it':<4} {'max mismatch (p.u.)':<20}")
        print("-" * 25)

    while not converged and it < max_it:
        # 1. P-Theta Step
        mis = V * np.conj(Ybus @ V) - Sbus
        P_mis = mis[pvpq].real
        
        # Check convergence on P and Q
        F = np.concatenate([mis[pvpq].real, mis[pq].imag])
        normF = np.linalg.norm(F, np.inf)
        
        if verbose:
            print(f"{it:<4} {normF:<20.3e}")
            
        if normF < tol:
            converged = True
            break
            
        # Delta_P / Vm = B' * Delta_Theta
        # Note: We use the mismatch directly as -F
        dp_v = -P_mis / np.abs(V[pvpq])
        dtheta = spsolve(Bp, dp_v)
        
        # Update Angles
        va = np.angle(V)
        va[pvpq] += dtheta
        V = np.abs(V) * np.exp(1j * va)
        
        # 2. Q-Vm Step
        mis = V * np.conj(Ybus @ V) - Sbus
        Q_mis = mis[pq].imag
        
        # Delta_Q / Vm = B'' * Delta_Vm
        dq_v = -Q_mis / np.abs(V[pq])
        dvm = spsolve(Bpp, dq_v)
        
        # Update Voltages
        vm = np.abs(V)
        vm[pq] += dvm
        V = vm * np.exp(1j * np.angle(V))
        
        it += 1
        
    if verbose:
        if converged:
            print(f"FDPF converged in {it} iterations.")
        else:
            print(f"FDPF failed to converge after {it} iterations.")
            
    return V, converged, it
