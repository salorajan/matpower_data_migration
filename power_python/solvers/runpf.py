import numpy as np
from ..core.constants import *
from ..network.admittance import make_ybus
from ..network.power_balance import make_sbus
from .newtonpf import newtonpf

from ..network.branch_flows import calculate_branch_flows

def run_power_flow(case, verbose=True):
    """
    Main entry point for running a power flow simulation.
    
    Args:
        case: A PowerCase object.
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, converged)
    """
    # Ensure internal indexing
    case.to_internal()
    
    # Identify bus types
    # Bus types: 1=PQ, 2=PV, 3=REF
    ref = np.where(case.bus[:, BUS_TYPE] == REF)[0]
    pv = np.where(case.bus[:, BUS_TYPE] == PV)[0]
    pq = np.where(case.bus[:, BUS_TYPE] == PQ)[0]
    
    # Build Ybus
    Ybus, Yf, Yt = make_ybus(case.baseMVA, case.bus, case.branch)
    
    # Build Sbus
    Sbus = make_sbus(case.baseMVA, case.bus, case.gen)
    
    # Initial voltage guess
    V0 = case.bus[:, VM] * np.exp(1j * np.pi / 180 * case.bus[:, VA])
    
    # Override PV and REF voltage magnitudes with generator setpoints
    for i in range(len(case.gen)):
        if case.gen[i, GEN_STATUS] > 0:
            bus_idx = int(case.gen[i, GEN_BUS])
            if case.bus[bus_idx, BUS_TYPE] in [PV, REF]:
                V0[bus_idx] = case.gen[i, VG] * np.exp(1j * np.angle(V0[bus_idx]))
    
    # Solve using Newton-Raphson
    V, converged, it = newtonpf(Ybus, Sbus, V0, pv, pq, ref, verbose=verbose)
    
    # Update bus voltages in the case object
    case.bus[:, VM] = np.abs(V)
    case.bus[:, VA] = np.angle(V) * 180 / np.pi
    
    # Update branch flows
    pf, qf, pt, qt = calculate_branch_flows(case.baseMVA, case.bus, case.branch, V)
    case.branch[:, PF] = pf
    case.branch[:, QF] = qf
    case.branch[:, PT] = pt
    case.branch[:, QT] = qt
    
    return case, converged
