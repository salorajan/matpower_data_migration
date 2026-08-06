# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
import pandas as pd
from ..core.constants import *
from ..network.sensitivity import make_ptdf

def decompose_dc_lmp(case):
    """
    Performs LMP Decomposition for a solved DC-OPF case.
    LMP = Energy + Congestion (Losses are 0 in DC-OPF).
    
    Args:
        case: A solved PowerCase object (must have LAM_P and MU_SF/MU_ST populated).
        
    Returns:
        pd.DataFrame: Decomposition results.
    """
    case.to_internal()
    nb = len(case.bus)
    nl = len(case.branch)
    
    # 1. Identify Components
    # Energy component is the LMP at the reference bus
    ref_idx = np.where(case.bus[:, BUS_TYPE] == REF)[0]
    if len(ref_idx) == 0:
        ref_idx = 0
    else:
        ref_idx = ref_idx[0]
        
    lam = case.bus[:, LAM_P]
    energy_comp = lam[ref_idx]
    
    # 2. Calculate PTDF
    PTDF = make_ptdf(case.baseMVA, case.bus, case.branch)
    
    # 3. Calculate Congestion Component
    # Shadow price of flow limit: mu = mu_pos - mu_neg
    mu = case.branch[:, MU_SF] - case.branch[:, MU_ST]
    
    # Congestion LMP = PTDF^T * mu
    # In some conventions, this needs a sign flip based on the solver dual definition
    congestion_comp = PTDF.T @ mu
    
    # Check if we need to flip the sign (skeptical approach)
    # The sum should match the calculated LMP at buses where congestion is high
    residual_pos = lam - (energy_comp + congestion_comp)
    residual_neg = lam - (energy_comp - congestion_comp)
    
    if np.sum(np.abs(residual_neg)) < np.sum(np.abs(residual_pos)):
        congestion_comp = -congestion_comp
        residual = residual_neg
    else:
        residual = residual_pos
    
    # 4. Assemble Results
    results = pd.DataFrame({
        "Bus_ID": case.external_bus_ids.astype(int),
        "LMP": lam,
        "Energy": energy_comp,
        "Congestion": congestion_comp,
        "Loss": 0.0,
        "Residual": residual
    })
    
    return results

def print_lmp_report(df):
    """Prints a formatted LMP decomposition report."""
    print("\n" + "="*80)
    print(f"{'LMP DECOMPOSITION REPORT (DC)':^80}")
    print("="*80)
    print(f"{'Bus':<8} {'Total LMP':<12} {'Energy':<12} {'Congestion':<12} {'Residual':<12}")
    print("-" * 65)
    
    for _, row in df.iterrows():
        print(f"{int(row['Bus_ID']):<8} {row['LMP']:<12.4f} {row['Energy']:<12.4f} {row['Congestion']:<12.4f} {row['Residual']:<12.4e}")
    
    print("="*80 + "\n")
