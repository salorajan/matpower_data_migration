# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from ..core.constants import *
from ..network.admittance import make_ybus
from ..network.power_balance import make_sbus
from .newtonpf import newtonpf
from .gausspf import gausspf
from .fdpf import fdpf

from ..network.branch_flows import calculate_branch_flows

def run_power_flow(case, algorithm='nr', enforce_q_limits=False, tol=1e-8, max_it=1000, verbose=True):
    """
    Main entry point for running a power flow simulation.
    
    Args:
        case: A PowerCase object.
        algorithm: 'nr', 'gs', 'fd'
        enforce_q_limits: If True, convert PV to PQ if Q limits are hit.
        tol: Convergence tolerance.
        max_it: Maximum iterations.
        verbose: Print progress.
    """
    case.to_internal()
    
    # Outer loop for Q limits (maximum 10 trials)
    for trial in range(10):
        # Identify current bus types
        ref = np.where(case.bus[:, BUS_TYPE] == REF)[0]
        pv = np.where(case.bus[:, BUS_TYPE] == PV)[0]
        pq = np.where(case.bus[:, BUS_TYPE] == PQ)[0]
        
        Ybus, _, _ = make_ybus(case.baseMVA, case.bus, case.branch)
        Sbus = make_sbus(case.baseMVA, case.bus, case.gen)
        V0 = case.bus[:, VM] * np.exp(1j * np.pi / 180 * case.bus[:, VA])
        
        # Generator setpoints
        for i in range(len(case.gen)):
            if case.gen[i, GEN_STATUS] > 0:
                bus_idx = int(case.gen[i, GEN_BUS])
                if case.bus[bus_idx, BUS_TYPE] in [PV, REF]:
                    V0[bus_idx] = case.gen[i, VG] * np.exp(1j * np.angle(V0[bus_idx]))
        
        # Solve inner power flow
        if algorithm == 'nr':
            V, converged, it = newtonpf(Ybus, Sbus, V0, pv, pq, ref, tol=tol, max_it=max_it, verbose=(verbose and trial==0))
        elif algorithm == 'gs':
            V, converged, it = gausspf(Ybus, Sbus, V0, pv, pq, ref, tol=tol, max_it=max_it, verbose=(verbose and trial==0))
        elif algorithm == 'fd':
            V, converged, it = fdpf(Ybus, Sbus, V0, pv, pq, ref, tol=tol, max_it=max_it, verbose=(verbose and trial==0))
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
            
        if not converged:
            return case, False


        # Update case with current solution
        case.bus[:, VM] = np.abs(V)
        case.bus[:, VA] = np.angle(V) * 180 / np.pi
        
        if not enforce_q_limits:
            break
            
        # Check Q limits at PV buses
        # S_inj = V * conj(Y * V)
        S_inj = V * np.conj(Ybus @ V)
        Q_inj_pu = S_inj.imag
        
        violations = False
        for i in range(len(case.gen)):
            if case.gen[i, GEN_STATUS] > 0:
                bus_idx = int(case.gen[i, GEN_BUS])
                if case.bus[bus_idx, BUS_TYPE] == PV:
                    # Q_gen = Q_inj + Q_load
                    q_gen = (Q_inj_pu[bus_idx] * case.baseMVA) + case.bus[bus_idx, QD]
                    
                    q_max = case.gen[i, QMAX]
                    q_min = case.gen[i, QMIN]
                    
                    if q_gen > q_max:
                        if verbose: print(f"Bus {int(case.external_bus_ids[bus_idx])} (Gen {i}) hit Qmax ({q_max:.2f}). Converting to PQ.")
                        case.bus[bus_idx, BUS_TYPE] = PQ
                        case.gen[i, QG] = q_max
                        violations = True
                        break # Convert one at a time for stability
                    elif q_gen < q_min:
                        if verbose: print(f"Bus {int(case.external_bus_ids[bus_idx])} (Gen {i}) hit Qmin ({q_min:.2f}). Converting to PQ.")
                        case.bus[bus_idx, BUS_TYPE] = PQ
                        case.gen[i, QG] = q_min
                        violations = True
                        break
        
        if not violations:
            break
            
    # Final flow update
    pf, qf, pt, qt = calculate_branch_flows(case.baseMVA, case.bus, case.branch, V)
    case.branch[:, PF], case.branch[:, QF] = pf, qf
    case.branch[:, PT], case.branch[:, QT] = pt, qt
    
    case.update_generator_power()
    
    return case, True
