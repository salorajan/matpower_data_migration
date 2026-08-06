# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
from ..core.constants import *
from ..network.admittance import make_ybus

def run_state_estimation(case, measurements=None, verbose=True):
    """
    Solves the Power System State Estimation (PSSE) using Weighted Least Squares (WLS).
    
    Args:
        case: PowerCase object.
        measurements: Dict containing 'type', 'idx', 'val', 'sigma'.
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, success)
    """
    case.to_internal()
    nb = len(case.bus)
    
    # 1. Measurement Setup
    if measurements is None:
        if verbose: print("No measurements provided. Generating synthetic measurements...")
        measurements = generate_synthetic_measurements(case)
        
    z = measurements['val']
    w = 1.0 / (measurements['sigma']**2)
    W = np.diag(w) # Weight matrix
    
    # 2. State Initialization
    ref = np.where(case.bus[:, BUS_TYPE] == REF)[0][0]
    non_ref = np.setdiff1d(np.arange(nb), [ref])
    
    va = case.bus[:, VA] * np.pi / 180
    vm = case.bus[:, VM]
    
    Ybus, _, _ = make_ybus(case.baseMVA, case.bus, case.branch)
    
    max_it = 20
    tol = 1e-5
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'STATE ESTIMATION (WLS)':^80}")
        print("="*80)
        print(f"{'Iteration':<10} {'Max Update':<20} {'Weighted Objective':<20}")
        print("-" * 50)

    success = False
    for it in range(max_it):
        # 3. Calculate h(x) and Jacobian H
        hx, H = calculate_h_and_H(case, va, vm, Ybus, measurements, ref)
        
        # 4. Residuals
        r = z - hx
        obj = r.T @ W @ r
        
        # 5. Gain Matrix G = H^T * W * H
        G = H.T @ W @ H
        rhs = H.T @ W @ r
        
        # 6. Solve for update dx
        # Add a small regularization to G to handle potential local unobservability during iteration
        G += np.eye(G.shape[0]) * 1e-9
        
        try:
            dx = np.linalg.solve(G, rhs)
        except np.linalg.LinAlgError:
            if verbose: print("Singular Gain Matrix. Estimation Failed.")
            break
            
        # 7. Update State
        # dx = [dVa_non_ref, dVm_all]
        va[non_ref] += dx[0:nb-1]
        vm[:] += dx[nb-1:]
        
        max_update = np.max(np.abs(dx))
        if verbose:
            print(f"{it:<10} {max_update:<20.4e} {obj:<20.4f}")
            
        if max_update < tol:
            success = True
            break
            
    if success:
        case.bus[:, VA] = va * 180 / np.pi
        case.bus[:, VM] = vm
        if verbose: print(f"State Estimation Converged in {it+1} iterations.")
    else:
        if verbose: print("State Estimation failed to converge.")
        
    return case, success

def generate_synthetic_measurements(case):
    """Generates redundant measurements by adding noise to the current state."""
    nb = len(case.bus)
    
    z_types = []
    z_vals = []
    z_sigs = []
    
    # Standard deviations for sensors
    sigma_v = 0.001
    sigma_p = 0.01
    
    # 1. Bus Voltages (All buses)
    for i in range(nb):
        z_types.append(('VM', i))
        z_vals.append(case.bus[i, VM] + np.random.normal(0, sigma_v))
        z_sigs.append(sigma_v)
        
    # 2. Net Power Injections (All buses)
    # Calculated from case state
    from ..network.power_balance import make_sbus
    Sbus = make_sbus(case.baseMVA, case.bus, case.gen)
    
    for i in range(nb):
        # P Injection
        z_types.append(('PINJ', i))
        z_vals.append(Sbus[i].real + np.random.normal(0, sigma_p))
        z_sigs.append(sigma_p)
        
        # Q Injection
        z_types.append(('QINJ', i))
        z_vals.append(Sbus[i].imag + np.random.normal(0, sigma_p))
        z_sigs.append(sigma_p)
    
    return {
        'type': [t[0] for t in z_types],
        'idx': [t[1] for t in z_types],
        'val': np.array(z_vals),
        'sigma': np.array(z_sigs)
    }

def calculate_h_and_H(case, va, vm, Ybus, measurements, ref):
    """Calculates measurement function h(x) and its Jacobian H."""
    nb = len(case.bus)
    nm = len(measurements['val'])
    non_ref = np.setdiff1d(np.arange(nb), [ref])
    
    hx = np.zeros(nm)
    H = np.zeros((nm, 2*nb - 1))
    
    V = vm * np.exp(1j * va)
    Ibus = Ybus @ V
    Sbus = V * np.conj(Ibus)
    
    # Pre-calculate derivatives for injections (same as PF Jacobian)
    # dS/dVm = diag(V/Vm) * conj(Y*V) + diag(V) * conj(Y * diag(V/Vm))
    # dS/dVa = j * diag(V) * conj(Y*V) - j * diag(V) * conj(Y * V) ... wait
    
    # We'll use a simpler element-wise approach for clarity in this SE port
    Y = Ybus.toarray()
    
    for k in range(nm):
        m_type = measurements['type'][k]
        i = measurements['idx'][k]
        
        if m_type == 'VM':
            hx[k] = vm[i]
            H[k, nb - 1 + i] = 1.0
            
        elif m_type == 'PINJ':
            hx[k] = Sbus[i].real
            # dPi/dVa_j
            for j_idx, j in enumerate(non_ref):
                if i == j:
                    H[k, j_idx] = -Sbus[i].imag - (vm[i]**2) * Y[i, i].imag
                else:
                    H[k, j_idx] = vm[i] * vm[j] * (Y[i, j].real * np.sin(va[i]-va[j]) - Y[i, j].imag * np.cos(va[i]-va[j]))
            # dPi/dVm_j
            for j in range(nb):
                if i == j:
                    H[k, nb - 1 + j] = Sbus[i].real / vm[i] + Y[i, i].real * vm[i]
                else:
                    H[k, nb - 1 + j] = vm[i] * (Y[i, j].real * np.cos(va[i]-va[j]) + Y[i, j].imag * np.sin(va[i]-va[j]))

        elif m_type == 'QINJ':
            hx[k] = Sbus[i].imag
            # dQi/dVa_j
            for j_idx, j in enumerate(non_ref):
                if i == j:
                    H[k, j_idx] = Sbus[i].real - (vm[i]**2) * Y[i, i].real
                else:
                    H[k, j_idx] = -vm[i] * vm[j] * (Y[i, j].real * np.cos(va[i]-va[j]) + Y[i, j].imag * np.sin(va[i]-va[j]))
            # dQi/dVm_j
            for j in range(nb):
                if i == j:
                    H[k, nb - 1 + j] = Sbus[i].imag / vm[i] - Y[i, i].imag * vm[i]
                else:
                    H[k, nb - 1 + j] = vm[i] * (Y[i, j].real * np.sin(va[i]-va[j]) - Y[i, j].imag * np.cos(va[i]-va[j]))
            
    return hx, H
