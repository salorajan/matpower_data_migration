# PowerPython
# Copyright (c) 2026 PowerPython contributors
#
# Derivative Work Attribution:
# - This file contains code adapted from the research work on:
#   Da Costa, V. M., Martins, N., & Pereira, J. L. R. (1997). Complex NR Method (Wirtinger).
#
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from scipy.sparse import csr_matrix, bmat, diags
from scipy.sparse.linalg import spsolve
from ..core.constants import *

def run_complex_nr_3p(case, max_it=10, tol=1e-8, verbose=True):
    """
    Solves 3-Phase Unbalanced Power Flow using the Complex-Variable Newton-Raphson 
    (CVNR) method, based on Wirtinger Calculus (Da Costa et al., 1997).
    """
    nb = len(case.bus3p)
    baseMVA = case.baseMVA
    
    # 1. Build 3-Phase Ybus
    # For simplicity in this implementation, we assume the case has a make_ybus_3p 
    # Or we build it here from LineConst and Line3P
    Ybus = build_ybus_3p(case)
    Sbus = build_sbus_3p(case)
    
    # Initial Voltages (Balanced 1.0 pu)
    # V is (nb * 3,) vector: [V1a, V1b, V1c, V2a, V2b, V2c, ...]
    V = np.zeros(nb * 3, dtype=complex)
    for i in range(nb):
        V[3*i]   = case.bus3p[i, 3] * np.exp(1j * np.pi/180 * case.bus3p[i, 6])
        V[3*i+1] = case.bus3p[i, 4] * np.exp(1j * np.pi/180 * case.bus3p[i, 7])
        V[3*i+2] = case.bus3p[i, 5] * np.exp(1j * np.pi/180 * case.bus3p[i, 8])

    if verbose:
        print("\n" + "="*80)
        print(f"{'3-PHASE COMPLEX-VARIABLE NEWTON-RAPHSON (DA COSTA 1997)':^80}")
        print("="*80)
        print(f"{'Iter':<10} {'Max Mismatch (pu)':<20}")
        print("-" * 40)

    success = False
    for it in range(max_it):
        I = Ybus @ V
        S_calc = V * np.conj(I)
        mis = S_calc - Sbus
        
        # In distribution systems, usually all buses except the head are PQ
        # For simplicity, we assume nodes with fixed V are 'slack-like' (Type 3)
        # This implementation treats all 3 phases
        
        # Identify 'Unknown' nodes (PQ and PV)
        # For 3-phase, we need to handle phase-level types. 
        # Here we use a mask for nodes that are NOT slack.
        mask = []
        for i in range(nb):
            if case.bus3p[i, 1] != 3: # Not Slack
                mask.extend([3*i, 3*i+1, 3*i+2])
        mask = np.array(mask)
        
        if len(mask) == 0:
            success = True
            break

        max_mis = np.max(np.abs(mis[mask]))
        if verbose: print(f"{it:<10} {max_mis:.4e}")
        
        if max_mis < tol:
            success = True
            break
            
        # 3. Wirtinger Derivatives (3-Phase)
        # dS/dV = diag(I*)
        # dS/dV* = diag(V) * conj(Ybus)
        A = diags(np.conj(I)).tocsr()
        B = (diags(V).tocsr() @ np.conj(Ybus)).tocsr()
        
        # Sub-matrices for unknown nodes
        A_sub = A[mask, :][:, mask].toarray()
        B_sub = B[mask, :][:, mask].toarray()
        
        # System: [A B; B* A*] * [dV; dV*] = -[mis; mis*]
        J = np.block([
            [A_sub, B_sub],
            [np.conj(B_sub), np.conj(A_sub)]
        ])
        
        R = -np.concatenate([mis[mask], np.conj(mis[mask])])
        
        # 4. Solve
        dx = np.linalg.solve(J, R)
        
        # 5. Update
        V[mask] += dx[:len(mask)]
        
    if success:
        if verbose: print(f"3-Phase Complex NR Converged in {it+1} iterations.")
        # Update results in case object
        for i in range(nb):
            case.bus3p[i, 3:6] = np.abs(V[3*i:3*i+3])
            case.bus3p[i, 6:9] = np.angle(V[3*i:3*i+3]) * 180 / np.pi
    
    return case, success

def build_ybus_3p(case):
    """
    Constructs the 3-phase Ybus matrix in phase coordinates.
    """
    nb = len(case.bus3p)
    # Correctly initialize as a complex dense matrix for building
    Ybus = np.zeros((nb * 3, nb * 3), dtype=complex)
    
    # Line Construction (3x3 matrices)
    line_consts = {}
    for lc in case.lc:
        lcid = int(lc[0])
        # R, X, C matrices
        R = np.array([[lc[1], lc[2], lc[3]], [lc[2], lc[4], lc[5]], [lc[3], lc[5], lc[6]]])
        X = np.array([[lc[7], lc[8], lc[9]], [lc[8], lc[10], lc[11]], [lc[9], lc[11], lc[12]]])
        Z = R + 1j * X
        
        # Use pseudo-inverse to handle lines with zero-impedance for some phases
        # (e.g. single-phase or two-phase lines represented in 3x3 matrices)
        Y = np.linalg.pinv(Z)
        line_consts[lcid] = Y

    # Add Line Admittances
    for line in case.line3p:
        f = int(line[1]) - 1
        t = int(line[2]) - 1
        lcid = int(line[4])
        length = line[5]
        Y = line_consts[lcid] / length
        
        # Diagonal blocks
        Ybus[3*f:3*f+3, 3*f:3*f+3] += Y
        Ybus[3*t:3*t+3, 3*t:3*t+3] += Y
        # Off-diagonal blocks
        Ybus[3*f:3*f+3, 3*t:3*t+3] -= Y
        Ybus[3*t:3*t+3, 3*f:3*f+3] -= Y

    # Add Transformers
    for xfmr in case.xfmr3p:
        f = int(xfmr[1]) - 1
        t = int(xfmr[2]) - 1
        R = xfmr[4]
        X = xfmr[5]
        # Simplified series model for 3-phase xfmr
        Y = np.eye(3) / (R + 1j * X)
        Ybus[3*f:3*f+3, 3*f:3*f+3] += Y
        Ybus[3*t:3*t+3, 3*t:3*t+3] += Y
        Ybus[3*f:3*f+3, 3*t:3*t+3] -= Y
        Ybus[3*t:3*t+3, 3*f:3*f+3] -= Y
        
    return csr_matrix(Ybus)

def build_sbus_3p(case):
    """
    Builds the 3-phase complex power injection vector.
    """
    nb = len(case.bus3p)
    Sbus = np.zeros(nb * 3, dtype=complex)
    
    # Load
    for load in case.load3p:
        bus_idx = int(load[1]) - 1
        # P = S*cos(phi), Q = S*sin(phi). Data has P and PF.
        for ph in range(3):
            p = load[3 + ph] / 1000 # Convert kW to MW (assume baseMVA=100)
            pf = load[6 + ph]
            q = p * np.tan(np.arccos(pf))
            Sbus[3*bus_idx + ph] -= (p + 1j * q) / 100 # p.u.
            
    # Generator
    for gen in case.gen3p:
        bus_idx = int(gen[1]) - 1
        for ph in range(3):
            p = gen[6 + ph] / 1000
            q = gen[9 + ph] / 1000
            Sbus[3*bus_idx + ph] += (p + 1j * q) / 100
            
    return Sbus
