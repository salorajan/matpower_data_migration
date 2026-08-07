# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from scipy.sparse.linalg import splu
from ..core.constants import *
from ..network.admittance import make_ybus
from ..network.power_balance import make_sbus

from scipy.interpolate import pade

import warnings

def run_hepf(case, max_order=14, verbose=True):
    """
    Solves power flow using Holomorphic Embedding method (HEPF) with Pade Approximants.
    """
    case.to_internal()
    nb = len(case.bus)
    baseMVA = case.baseMVA

    # Apply generator setpoints to PV and Slack buses
    # This ensures consistency with run_power_flow
    for i in range(len(case.gen)):
        if case.gen[i, GEN_STATUS] > 0:
            bus_idx = int(case.gen[i, GEN_BUS])
            if case.bus[bus_idx, BUS_TYPE] in [PV, REF]:
                case.bus[bus_idx, VM] = case.gen[i, VG]

    # Identify bus types (re-identify after potential status changes or for clarity)
    ref = np.where(case.bus[:, BUS_TYPE] == REF)[0]
    pv = np.where(case.bus[:, BUS_TYPE] == PV)[0]
    pq = np.where(case.bus[:, BUS_TYPE] == PQ)[0]

    if len(ref) == 0: ref = np.array([0])
    n_pv = len(pv)

    # Admittance matrix and Sbus
    Ybus, _, _ = make_ybus(baseMVA, case.bus, case.branch)
    Sbus = make_sbus(baseMVA, case.bus, case.gen)

    # Germ solution (s=0): No-load solution
    V_coeffs = np.zeros((nb, max_order + 1), dtype=complex)
    W_coeffs = np.zeros((nb, max_order + 1), dtype=complex)
    Q_coeffs = np.zeros((nb, max_order + 1))

    Ytr_mat = Ybus.copy().tolil()
    for r in ref:
        Ytr_mat[r, :] = 0
        Ytr_mat[r, r] = 1.0
    Ytr_mat = Ytr_mat.tocsr()

    V_rhs = np.zeros(nb, dtype=complex)
    V_rhs[ref] = case.bus[ref, VM] * np.exp(1j * np.pi / 180 * case.bus[ref, VA])

    from scipy.sparse.linalg import spsolve
    V_coeffs[:, 0] = spsolve(Ytr_mat, V_rhs)
    W_coeffs[:, 0] = 1.0 / V_coeffs[:, 0]

    # Build System Matrix M
    G, B = Ybus.real, Ybus.imag
    size = 2 * nb + n_pv
    from scipy.sparse import lil_matrix
    M = lil_matrix((size, size))
    M[0:nb, 0:nb] = G
    M[0:nb, nb:2*nb] = -B
    M[nb:2*nb, 0:nb] = B
    M[nb:2*nb, nb:2*nb] = G

    for i, pv_bus in enumerate(pv):
        M[pv_bus, 2*nb + i] = W_coeffs[pv_bus, 0].imag
        M[pv_bus + nb, 2*nb + i] = W_coeffs[pv_bus, 0].real
        M[2*nb + i, pv_bus] = 2 * V_coeffs[pv_bus, 0].real
        M[2*nb + i, pv_bus + nb] = 2 * V_coeffs[pv_bus, 0].imag

    for r in ref:
        M[r, :], M[r, r] = 0, 1.0
        M[r + nb, :], M[r + nb, r + nb] = 0, 1.0

    M_lu = splu(M.tocsc())

    def get_w_k(k, V_c, W_c):
        res = np.zeros(nb, dtype=complex)
        for i in range(1, k + 1):
            res += V_c[:, i] * W_c[:, k - i]
        return -res / V_c[:, 0]

    for k in range(1, max_order + 1):
        RHS = np.zeros(size)
        # PQ RHS
        for i in pq:
            rhs_val = np.conj(Sbus[i]) * np.conj(W_coeffs[i, k-1])
            RHS[i], RHS[i + nb] = rhs_val.real, rhs_val.imag
        # PV RHS
        for i, pv_bus in enumerate(pv):
            sum_jqw = 0
            for j in range(1, k):
                sum_jqw += 1j * Q_coeffs[pv_bus, j] * np.conj(W_coeffs[pv_bus, k-j])
            rhs_val = Sbus[pv_bus].real * np.conj(W_coeffs[pv_bus, k-1]) - sum_jqw
            RHS[pv_bus], RHS[pv_bus + nb] = rhs_val.real, rhs_val.imag

            # Voltage Constraint: RHS_k = delta(k,1)*(Vset^2 - |V0|^2) - sum_{j=1}^{k-1} Vj * conj(V_{k-j})
            sum_vv = 0
            for j in range(1, k):
                sum_vv += V_coeffs[pv_bus, j] * np.conj(V_coeffs[pv_bus, k-j])
            rhs_mag = -sum_vv.real
            if k == 1:
                rhs_mag += (case.bus[pv_bus, VM]**2 - np.abs(V_coeffs[pv_bus, 0])**2)
            RHS[2*nb + i] = rhs_mag

        sol = M_lu.solve(RHS)
        V_coeffs[:, k] = sol[0:nb] + 1j * sol[nb:2*nb]
        for i, pv_bus in enumerate(pv):
            Q_coeffs[pv_bus, k] = sol[2*nb + i]
        W_coeffs[:, k] = get_w_k(k, V_coeffs, W_coeffs)

    # Evaluate using Pade Approximant for better convergence
    V = np.zeros(nb, dtype=complex)
    for i in range(nb):
        # For reference buses, the series is usually just the germ solution
        if i in ref:
            V[i] = V_coeffs[i, 0]
            continue
            
        # Use [N/N] or [N/N-1] Pade
        n_pade = max_order // 2
        with warnings.catch_warnings():
            warnings.simplefilter("ignore") # Suppress all numerical noise during Pade
            try:
                p, q = pade(V_coeffs[i, :], n_pade)
                V[i] = p(1.0) / q(1.0)
            except:
                # Fallback to Taylor sum if Pade fails
                V[i] = np.sum(V_coeffs[i, :])

    # Residual Check
    mis = V * np.conj(Ybus @ V) - Sbus
    # For PV buses, we only care about real power residual
    res_pq = np.abs(mis[pq])
    res_pv_p = np.abs(mis[pv].real)
    max_res = np.max(np.concatenate([res_pq, res_pv_p])) if len(pq) + len(pv) > 0 else 0
    converged = max_res < 1e-5

    if verbose:
        print(f"HEPF {'Converged' if converged else 'Failed'}. Max Res: {max_res:.3e}")

    case.bus[:, VM], case.bus[:, VA] = np.abs(V), np.angle(V) * 180 / np.pi
    
    # Update branch flows
    from ..network.branch_flows import calculate_branch_flows
    pf, qf, pt, qt = calculate_branch_flows(case.baseMVA, case.bus, case.branch, V)
    case.branch[:, PF] = pf
    case.branch[:, QF] = qf
    case.branch[:, PT] = pt
    case.branch[:, QT] = qt
    
    case.update_generator_power()
    
    return case, converged

def pade_approximant(coeffs, s=1.0):
    """
    Computes the [N/N] or [N/N-1] Pade approximant of a power series.
    Not yet implemented.
    """
    pass
