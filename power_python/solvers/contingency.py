# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
import pandas as pd
from ..core.constants import *
from ..network.sensitivity import make_ptdf, make_lodf
from ..network.power_balance import make_sbus

def run_contingency_analysis(case, verbose=True):
    """
    Performs N-1 Contingency Analysis using DC approximation and LODFs.
    
    Args:
        case: A PowerCase object.
        verbose: Print summary.
        
    Returns:
        pd.DataFrame: A report of all contingencies and their violations.
    """
    case.to_internal()
    nb = len(case.bus)
    nl = len(case.branch)
    
    # 1. Base Case DC Power Flow
    # For DC: P = Bf * Va
    # Va = Bbus_red^-1 * (Pgen - Pload)_red
    # But it's easier to use PTDF: Flow = PTDF * (Pgen - Pload)
    
    PTDF = make_ptdf(case.baseMVA, case.bus, case.branch)
    Sbus = make_sbus(case.baseMVA, case.bus, case.gen)
    Pbus = Sbus.real # DC power injections (p.u.)
    
    # Base case flows (p.u.)
    base_flows = PTDF @ Pbus
    
    # Calculate LODFs
    LODF = make_lodf(case.branch, PTDF)
    
    results = []
    
    if verbose:
        print(f"\n{'Outaged Line':<15} {'Monitored Line':<15} {'Post-Flow (MW)':<15} {'Limit (MW)':<10} {'Loading %':<10}")
        print("-" * 70)

    # 2. Iterate through each contingency (outage of line j)
    for j in range(nl):
        if case.branch[j, BR_STATUS] <= 0:
            continue
            
        # If line j is a bridge, LODF is NaN, skip as it causes islanding
        if np.isnan(LODF[j, j]):
            if verbose:
                # print(f"Line {j+1} is a bridge. Skipping.")
                pass
            continue
            
        # Predicted flows after outage of line j
        # P_new(i) = P_base(i) + LODF(i, j) * P_base(j)
        post_flows = base_flows + LODF[:, j] * base_flows[j]
        
        # 3. Check for violations
        # We only care about lines other than the outaged one
        for i in range(nl):
            if i == j or case.branch[i, BR_STATUS] <= 0:
                continue
                
            limit = case.branch[i, RATE_A]
            if limit <= 0: continue
            
            flow_mw = np.abs(post_flows[i] * case.baseMVA)
            loading = (flow_mw / limit) * 100
            
            if loading > 100:
                out_f = int(case.external_bus_ids[int(case.branch[j, F_BUS])])
                out_t = int(case.external_bus_ids[int(case.branch[j, T_BUS])])
                mon_f = int(case.external_bus_ids[int(case.branch[i, F_BUS])])
                mon_t = int(case.external_bus_ids[int(case.branch[i, T_BUS])])
                
                res = {
                    "outage": f"{out_f}-{out_t}",
                    "monitored": f"{mon_f}-{mon_t}",
                    "flow_mw": flow_mw,
                    "limit": limit,
                    "loading": loading
                }
                results.append(res)
                
                if verbose:
                    print(f"{res['outage']:<15} {res['monitored']:<15} {flow_mw:<15.2f} {limit:<10.1f} {loading:<10.1f}%")

    if verbose and not results:
        print("No N-1 violations detected.")
        
    return pd.DataFrame(results)
