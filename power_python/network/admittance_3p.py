# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from scipy.sparse import csr_matrix
from ..core.constants import *

def make_ybus_3p(case):
    """
    Builds the 3-phase bus admittance matrix Ybus_3p.
    Ybus_3p is a (3*nb) x (3*nb) complex matrix.
    """
    nb = len(case.bus3p)
    nl = len(case.line3p)
    
    # Initialize 3x3 block-sparse structure
    # For now, let's use a dense matrix for small distribution systems, 
    # then convert to CSR if needed.
    Ybus = np.zeros((3*nb, 3*nb), dtype=complex)
    
    # 1. Line Admittances
    # Each line has a construction ID (lcid) pointing to the lc matrix
    # which defines the 3x3 Z and C matrices.
    for i in range(nl):
        brid = int(case.line3p[i, 0])
        f_bus = int(case.line3p[i, 1]) - 1 # 0-indexed
        t_bus = int(case.line3p[i, 2]) - 1
        stat = int(case.line3p[i, 3])
        lcid = int(case.line3p[i, 4])
        length = case.line3p[i, 5]
        
        if stat <= 0: continue
        
        # Get line construction data (R and X matrices)
        # mpc.lc = [lcid, R11, R21, R31, R22, R32, R33, X11, X21, X31, X22, X32, X33, ...]
        lc_row = case.lc[np.where(case.lc[:, 0] == lcid)[0][0]]
        
        R = np.array([
            [lc_row[1], lc_row[2], lc_row[3]],
            [lc_row[2], lc_row[4], lc_row[5]],
            [lc_row[3], lc_row[5], lc_row[6]]
        ])
        X = np.array([
            [lc_row[7], lc_row[8], lc_row[9]],
            [lc_row[8], lc_row[10], lc_row[11]],
            [lc_row[9], lc_row[11], lc_row[12]]
        ])
        
        Zabc = (R + 1j*X) * length
        Yabc = np.linalg.inv(Zabc)
        
        # Add to Ybus blocks
        f_idx = f_bus * 3
        t_idx = t_bus * 3
        
        # Off-diagonal
        Ybus[f_idx:f_idx+3, t_idx:t_idx+3] -= Yabc
        Ybus[t_idx:t_idx+3, f_idx:f_idx+3] -= Yabc
        
        # Diagonal
        Ybus[f_idx:f_idx+3, f_idx:f_idx+3] += Yabc
        Ybus[t_idx:t_idx+3, t_idx:t_idx+3] += Yabc
        
        # Add shunt charging (if available in LC data)
        # ... simplified for now ...
        
    # 2. Transformer Admittances
    # xfmr3p = [xfid, fbus, tbus, status, R, X, basekVA, basekV, ratio]
    for i in range(len(case.xfmr3p)):
        stat = int(case.xfmr3p[i, 3])
        if stat <= 0: continue
        
        f_bus = int(case.xfmr3p[i, 1]) - 1
        t_bus = int(case.xfmr3p[i, 2]) - 1
        R = case.xfmr3p[i, 4]
        X = case.xfmr3p[i, 5]
        Z = R + 1j*X
        Yt = 1.0 / Z
        
        f_idx = f_bus * 3
        t_idx = t_bus * 3
        
        # Simple Y-Y transformer (no phase shift)
        # This is a 3x3 identity * Yt
        Yt_3p = np.eye(3) * Yt
        
        Ybus[f_idx:f_idx+3, t_idx:t_idx+3] -= Yt_3p
        Ybus[t_idx:t_idx+3, f_idx:f_idx+3] -= Yt_3p
        Ybus[f_idx:f_idx+3, f_idx:f_idx+3] += Yt_3p
        Ybus[t_idx:t_idx+3, t_idx:t_idx+3] += Yt_3p
        
    return Ybus
