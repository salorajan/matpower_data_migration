# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from ..core.constants import *

def run_dc_pf(case, verbose=True):
    """
    Solves a DC Power Flow using standard DC approximation (neglects R).
    
    Args:
        case: A PowerCase object.
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, success)
    """
    case.to_internal()
    nb = len(case.bus)
    nl = len(case.branch)
    baseMVA = case.baseMVA
    
    # 1. Identify reference bus
    ref_idx = np.where(case.bus[:, BUS_TYPE] == REF)[0]
    if len(ref_idx) == 0:
        ref = 0
    else:
        ref = ref_idx[0]
    
    # 2. Build DC B matrix
    B = np.zeros((nb, nb))
    f = case.branch[:, F_BUS].astype(int)
    t = case.branch[:, T_BUS].astype(int)
    stat = case.branch[:, BR_STATUS]
    X = case.branch[:, BR_X]
    tap = case.branch[:, TAP]
    tap[tap == 0] = 1.0
    
    b_line = stat / (X * tap)
    
    for i in range(nl):
        if stat[i] > 0:
            B[f[i], f[i]] += b_line[i]
            B[t[i], t[i]] += b_line[i]
            B[f[i], t[i]] -= b_line[i]
            B[t[i], f[i]] -= b_line[i]
            
    # 3. Build Power Injection vector P
    # Pbus = Pgen - Pload
    Pbus = np.zeros(nb)
    for i in range(len(case.gen)):
        if case.gen[i, GEN_STATUS] > 0:
            bus_idx = int(case.gen[i, GEN_BUS])
            Pbus[bus_idx] += case.gen[i, PG]
            
    Pbus -= case.bus[:, PD]
    Ppu = Pbus / baseMVA
    
    # 4. Solve B * Va = Ppu
    non_ref = np.delete(np.arange(nb), ref)
    B_red = B[np.ix_(non_ref, non_ref)]
    P_red = Ppu[non_ref]
    
    try:
        va_red = np.linalg.solve(B_red, P_red)
        va = np.zeros(nb)
        va[non_ref] = va_red
        
        # Update case
        case.bus[:, VA] = va * 180 / np.pi
        case.bus[:, VM] = 1.0
        
        # Calculate DC branch flows
        Va_rad = va
        f_idx = case.branch[:, F_BUS].astype(int)
        t_idx = case.branch[:, T_BUS].astype(int)
        X_val = case.branch[:, BR_X]
        tap_val = case.branch[:, TAP].copy()
        tap_val[tap_val == 0] = 1.0
        shift_val = case.branch[:, SHIFT] * np.pi / 180
        
        pf_val = baseMVA * (Va_rad[f_idx] - Va_rad[t_idx] - shift_val) / (X_val * tap_val)
        pf_val = pf_val * (case.branch[:, BR_STATUS] > 0)
        
        case.branch[:, PF] = pf_val
        case.branch[:, PT] = -pf_val
        case.branch[:, QF] = 0.0
        case.branch[:, QT] = 0.0
        
        # Update slack generator PG
        online_gens = np.where(case.gen[:, GEN_STATUS] > 0)[0]
        slack_gens = [g for g in online_gens if int(case.gen[g, GEN_BUS]) in ref_idx]
        non_slack_gens = [g for g in online_gens if int(case.gen[g, GEN_BUS]) not in ref_idx]
        
        if len(slack_gens) > 0:
            total_load = np.sum(case.bus[:, PD])
            total_non_slack_gen = np.sum(case.gen[non_slack_gens, PG])
            pg_slack_total = total_load - total_non_slack_gen
            
            if len(slack_gens) == 1:
                case.gen[slack_gens[0], PG] = pg_slack_total
            else:
                mbase_sum = sum(case.gen[g, MBASE] for g in slack_gens)
                if mbase_sum > 0:
                    for g in slack_gens:
                        case.gen[g, PG] = pg_slack_total * (case.gen[g, MBASE] / mbase_sum)
                else:
                    for g in slack_gens:
                        case.gen[g, PG] = pg_slack_total / len(slack_gens)
                        
        case.gen[online_gens, QG] = 0.0
        
        if verbose:
            print("DC Power Flow solved successfully.")
        return case, True
    except np.linalg.LinAlgError:
        if verbose:
            print("DC Power Flow failed: Matrix is singular.")
        return case, False
