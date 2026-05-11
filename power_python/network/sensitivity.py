import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import spsolve
from ..core.constants import *

def make_ptdf(baseMVA, bus, branch, slack=None):
    """
    Builds the DC PTDF (Power Transfer Distribution Factors) matrix.
    
    Args:
        baseMVA (float): System MVA base.
        bus (np.ndarray): Bus matrix (internal indices).
        branch (np.ndarray): Branch matrix (internal indices).
        slack (int or np.ndarray): Reference bus index or weight vector.
        
    Returns:
        np.ndarray: PTDF matrix (nbr x nb).
    """
    nb = bus.shape[0]
    nl = branch.shape[0]
    
    # 1. Reference bus
    if slack is None:
        slack = np.where(bus[:, BUS_TYPE] == REF)[0]
        if len(slack) == 0:
            slack = 0 # Fallback to first bus
        else:
            slack = slack[0]
            
    # 2. Build Bbus for DC approximation
    stat = branch[:, BR_STATUS]
    X = branch[:, BR_X]
    tap = branch[:, TAP].copy()
    tap[tap == 0] = 1.0
    b_line = stat / (X * tap)
    
    f = branch[:, F_BUS].astype(int)
    t = branch[:, T_BUS].astype(int)
    
    # Admittance matrix Bbus
    # Using sparse construction for efficiency
    i = np.concatenate([f, t, f, t])
    j = np.concatenate([f, t, t, f])
    data = np.concatenate([b_line, b_line, -b_line, -b_line])
    Bbus = csr_matrix((data, (i, j)), shape=(nb, nb))
    
    # 3. Build B_f (branch-bus connection matrix)
    # B_f * Va = flow
    # B_f has nl rows and nb columns
    # Non-zero in columns f and t for each branch
    row = np.concatenate([np.arange(nl), np.arange(nl)])
    col = np.concatenate([f, t])
    data_f = np.concatenate([b_line, -b_line])
    Bf = csr_matrix((data_f, (row, col)), shape=(nl, nb))
    
    # 4. PTDF Calculation
    # PTDF = Bf * inv(Bbus_reduced)
    # We solve Bbus_reduced * X = I_reduced
    
    # Reduced Bbus (remove slack row/column)
    non_slack = np.setdiff1d(np.arange(nb), [slack])
    B_red = Bbus[non_slack, :][:, non_slack]
    
    # Solve for full matrix (inverse substitute)
    # This can be slow for very large systems, but fine for now
    # We solve B_red * PTDF_red^T = Bf_red^T
    Bf_red = Bf[:, non_slack]
    
    # Bf_red.T is (nb-1) x nl
    # We want X such that B_red * X = Bf_red.T
    # spsolve with multiple columns returns a sparse or dense matrix depending on input
    X = spsolve(B_red.tocsc(), Bf_red.T.tocsc()) 
    
    # PTDF matrix is nl x nb
    PTDF = np.zeros((nl, nb))
    # Convert X to dense if it's sparse before assignment
    if hasattr(X, "toarray"):
        PTDF[:, non_slack] = X.T.toarray()
    else:
        PTDF[:, non_slack] = X.T
    
    return PTDF

def make_lodf(branch, PTDF):
    """
    Builds the DC LODF (Line Outage Distribution Factors) matrix.
    
    Args:
        branch (np.ndarray): Branch matrix.
        PTDF (np.ndarray): PTDF matrix (nl x nb).
        
    Returns:
        np.ndarray: LODF matrix (nl x nl).
    """
    nl, nb = PTDF.shape
    f = branch[:, F_BUS].astype(int)
    t = branch[:, T_BUS].astype(int)
    
    # PTDF * Cft gives the outage distribution factors
    # Cft(i, k) is 1 if bus i is f_bus of branch k, -1 if it is t_bus
    # rows: nb, cols: nl
    row = np.concatenate([f, t])
    col = np.concatenate([np.arange(nl), np.arange(nl)])
    data = np.concatenate([np.ones(nl), -np.ones(nl)])
    Cft = csr_matrix((data, (row, col)), shape=(nb, nl))
    
    H = PTDF @ Cft.toarray() # nl x nl
    h = np.diag(H)
    
    # LODF(i, j) = H(i, j) / (1 - H(j, j))
    # where j is the outaged line
    # Denominator (1 - h)
    denom = 1.0 - h
    # Handle division by zero (bridges)
    denom[np.abs(denom) < 1e-10] = np.nan
    
    LODF = H / denom[np.newaxis, :]
    
    # Diagonal should be -1 (by convention in some places, or 0)
    # MATPOWER sets diag to -1 then clears it? 
    # LODF = LODF - diag(diag(LODF)) - eye(nl, nl)
    # Let's match MATPOWER
    np.fill_diagonal(LODF, 0)
    LODF = LODF - np.eye(nl)
    
    return LODF
