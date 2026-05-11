import numpy as np
from scipy.sparse import csr_matrix
from ..core.constants import *

def make_ybus(baseMVA, bus, branch):
    """
    Builds the bus admittance matrix and branch admittance matrices.
    
    Args:
        baseMVA (float): System MVA base.
        bus (np.ndarray): Bus matrix (internal 0-indexed).
        branch (np.ndarray): Branch matrix (internal 0-indexed).
        
    Returns:
        tuple: (Ybus, Yf, Yt) as scipy sparse matrices.
    """
    nb = bus.shape[0]
    nl = branch.shape[0]

    # Series admittance
    stat = branch[:, BR_STATUS]
    # Series impedance Zs = R + jX
    # Series admittance Ys = 1 / Zs
    Zs = branch[:, BR_R] + 1j * branch[:, BR_X]
    Ys = stat / Zs
    
    # Line charging susceptance
    Bc = stat * branch[:, BR_B]
    
    # Tap ratio (complex)
    tap = np.ones(nl, dtype=complex)
    i = np.where(branch[:, TAP] != 0)[0]
    tap[i] = branch[i, TAP]
    # Phase shift
    tap = tap * np.exp(1j * np.pi / 180 * branch[:, SHIFT])
    
    # Branch admittances for the pi-model
    # Ytt = Ys + j*Bc/2
    # Yff = Ytt / |tap|^2
    # Yft = -Ys / conj(tap)
    # Ytf = -Ys / tap
    
    Ytt = Ys + 1j * Bc / 2
    Yff = Ytt / (tap * np.conj(tap))
    Yft = -Ys / np.conj(tap)
    Ytf = -Ys / tap
    
    # Shunt admittance
    # Ysh = (Gs + jBs) / baseMVA
    Ysh = (bus[:, GS] + 1j * bus[:, BS]) / baseMVA
    
    # Bus indices (assumed internal 0-based)
    f = branch[:, F_BUS].astype(int)
    t = branch[:, T_BUS].astype(int)
    
    # Build Yf and Yt
    # Yf = [Yff Yft] * [Vf; Vt]
    # Yt = [Ytf Ytt] * [Vf; Vt]
    
    row = np.concatenate([np.arange(nl), np.arange(nl)])
    col = np.concatenate([f, t])
    
    data_f = np.concatenate([Yff, Yft])
    Yf = csr_matrix((data_f, (row, col)), shape=(nl, nb))
    
    data_t = np.concatenate([Ytf, Ytt])
    Yt = csr_matrix((data_t, (row, col)), shape=(nl, nb))
    
    # Build Ybus
    # Ybus = sum of branch admittances + shunts
    row_bus = np.concatenate([f, f, t, t])
    col_bus = np.concatenate([f, t, f, t])
    data_bus = np.concatenate([Yff, Yft, Ytf, Ytt])
    
    Ybus = csr_matrix((data_bus, (row_bus, col_bus)), shape=(nb, nb))
    
    # Add shunt admittances (diagonal)
    Ybus += csr_matrix((Ysh, (np.arange(nb), np.arange(nb))), shape=(nb, nb))
    
    return Ybus, Yf, Yt
