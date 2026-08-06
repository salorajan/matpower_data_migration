# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from scipy.sparse import bmat
from scipy.sparse.linalg import spsolve
from ..network.derivatives import dSbus_dv

def newtonpf(Ybus, Sbus, V0, pv, pq, ref, tol=1e-8, max_it=10, verbose=True):
    """
    Solves power flow using Newton's method (polar coordinates).
    
    Args:
        Ybus: Admittance matrix
        Sbus: Scheduled power injections
        V0: Initial voltage guess
        pv: PV bus indices
        pq: PQ bus indices
        ref: Slack bus indices
        tol: Convergence tolerance
        max_it: Maximum iterations
        
    Returns:
        tuple: (V, converged, iterations)
    """
    V = V0.copy()
    Va = np.angle(V)
    Vm = np.abs(V)
    
    converged = False
    it = 0
    
    # Combined PV and PQ indices for angle updates
    pvpq = np.concatenate([pv, pq])
    
    if verbose:
        print(f"{'it':<4} {'max mismatch (p.u.)':<20}")
        print("-" * 25)

    while not converged and it < max_it:
        # Complex power mismatch
        # mis = V * conj(I) - Sbus
        mis = V * np.conj(Ybus @ V) - Sbus
        
        # F(x) = [ real(mis[pvpq]); imag(mis[pq]) ]
        F = np.concatenate([
            mis[pvpq].real,
            mis[pq].imag
        ])
        
        # Check convergence
        normF = np.linalg.norm(F, np.inf)
        if verbose:
            print(f"{it:<4} {normF:<20.3e}")
            
        if normF < tol:
            converged = True
            break
            
        # Jacobian calculation
        dS_dVa, dS_dVm = dSbus_dv(Ybus, V)
        
        # Extract sub-matrices for the Jacobian
        # J = [ dP/dVa  dP/dVm ]
        #     [ dQ/dVa  dQ/dVm ]
        
        J11 = dS_dVa[pvpq, :][:, pvpq].real
        J12 = dS_dVm[pvpq, :][:, pq].real
        J21 = dS_dVa[pq, :][:, pvpq].imag
        J22 = dS_dVm[pq, :][:, pq].imag
        
        # Build the full Jacobian matrix
        J = bmat([
            [J11, J12],
            [J21, J22]
        ], format='csr')
        
        # Solve J * dx = -F
        try:
            dx = spsolve(J, -F)
        except Exception as e:
            if verbose:
                print(f"Linear solver failed: {e}")
            break
            
        # Update state variables
        n_pvpq = len(pvpq)
        Va[pvpq] += dx[:n_pvpq]
        Vm[pq] += dx[n_pvpq:]
        
        # Update complex voltage vector
        V = Vm * np.exp(1j * Va)
        it += 1
        
    if verbose and converged:
        print(f"Converged in {it} iterations.")
    elif verbose:
        print(f"Did not converge in {max_it} iterations.")
        
    return V, converged, it
