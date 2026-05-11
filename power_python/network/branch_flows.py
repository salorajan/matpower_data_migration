import numpy as np
from ..core.constants import *

def calculate_branch_flows(baseMVA, bus, branch, V):
    """
    Calculates complex power flows at each end of each branch.
    
    Args:
        baseMVA (float): System MVA base.
        bus (np.ndarray): Bus matrix.
        branch (np.ndarray): Branch matrix.
        V (np.ndarray): Complex voltage vector.
        
    Returns:
        tuple: (Pf, Qf, Pt, Qt) power flow vectors in MW/MVAr.
    """
    nl = branch.shape[0]
    
    # Admittance matrix components for branches
    stat = branch[:, BR_STATUS]
    Zs = branch[:, BR_R] + 1j * branch[:, BR_X]
    Ys = stat / Zs
    Bc = stat * branch[:, BR_B]
    
    tap = np.ones(nl, dtype=complex)
    i = np.where(branch[:, TAP] != 0)[0]
    tap[i] = branch[i, TAP]
    tap = tap * np.exp(1j * np.pi / 180 * branch[:, SHIFT])
    
    # Standard Pi-model admittances
    Ytt = Ys + 1j * Bc / 2
    Yff = Ytt / (tap * np.conj(tap))
    Yft = -Ys / np.conj(tap)
    Ytf = -Ys / tap
    
    # Bus indices
    f = branch[:, F_BUS].astype(int)
    t = branch[:, T_BUS].astype(int)
    
    # Complex voltages at from/to ends
    Vf = V[f]
    Vt = V[t]
    
    # Complex current injections
    # If = Yff * Vf + Yft * Vt
    # It = Ytf * Vf + Ytt * Vt
    If = Yff * Vf + Yft * Vt
    It = Ytf * Vf + Ytt * Vt
    
    # Complex power injections (S = V * conj(I))
    Sf = Vf * np.conj(If) * baseMVA
    St = Vt * np.conj(It) * baseMVA
    
    return Sf.real, Sf.imag, St.real, St.imag
