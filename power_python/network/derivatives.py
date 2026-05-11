import numpy as np
from scipy.sparse import diags

def dSbus_dv(Ybus, V):
    """
    Computes partial derivatives of power injection w.r.t. voltage (polar coordinates).
    
    Args:
        Ybus: Bus admittance matrix (sparse)
        V: Complex voltage vector
        
    Returns:
        tuple: (dS_dVa, dS_dVm) as sparse matrices
    """
    nb = len(V)
    Ibus = Ybus @ V
    
    # Voltage magnitude
    Vmag = np.abs(V)
    # V / |V|
    Vnorm = np.zeros_like(V, dtype=complex)
    nonzero_v = Vmag > 0
    Vnorm[nonzero_v] = V[nonzero_v] / Vmag[nonzero_v]
    
    # Diagonal matrices for sparse operations
    diagV = diags(V)
    diagIbus = diags(Ibus)
    diagVnorm = diags(Vnorm)
    
    # dS/dVa = j * diag(V) * conj(diag(Ibus) - Ybus * diag(V))
    # This is equivalent to MATPOWER's vectorized implementation
    dS_dVa = 1j * diagV @ (diagIbus.conj() - Ybus.conj() @ diagV.conj())
    
    # dS/dVm = diag(V) * conj(Ybus * diag(V/|V|)) + diag(conj(Ibus)) * diag(V/|V|)
    dS_dVm = diagV @ (Ybus.conj() @ diagVnorm.conj()) + diagIbus.conj() @ diagVnorm
    
    return dS_dVa, dS_dVm
