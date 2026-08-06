# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from ..core.constants import *

def calculate_system_balance(case):
    """
    Calculates the system-wide power balance: Gen = Load + Loss + Residual.
    
    Args:
        case: A PowerCase object.
        
    Returns:
        dict: A dictionary containing balance components.
    """
    # 1. Total Generation
    # Filter for generators in service
    on_gen = case.gen[case.gen[:, GEN_STATUS] > 0]
    total_gen_p = np.sum(on_gen[:, PG])
    total_gen_q = np.sum(on_gen[:, QG])
    
    # 2. Total Load
    total_load_p = np.sum(case.bus[:, PD])
    total_load_q = np.sum(case.bus[:, QD])
    
    # 3. Total Losses (if flows are calculated)
    # Sum(P_from + P_to) for all branches
    total_loss_p = np.sum(case.branch[:, PF] + case.branch[:, PT])
    total_loss_q = np.sum(case.branch[:, QF] + case.branch[:, QT])
    
    # 4. Residual Errors
    residual_p = total_gen_p - (total_load_p + total_loss_p)
    residual_q = total_gen_q - (total_load_q + total_loss_q)
    
    return {
        "gen_p": total_gen_p, "gen_q": total_gen_q,
        "load_p": total_load_p, "load_q": total_load_q,
        "loss_p": total_loss_p, "loss_q": total_loss_q,
        "residual_p": residual_p, "residual_q": residual_q
    }

def check_voltage_violations(case):
    """
    Checks for voltage magnitude violations at all buses.
    
    Args:
        case: A PowerCase object.
        
    Returns:
        list: A list of dicts describing violations.
    """
    violations = []
    for i in range(len(case.bus)):
        vm = case.bus[i, VM]
        vmax = case.bus[i, VMAX]
        vmin = case.bus[i, VMIN]
        bus_id = int(case.external_bus_ids[i])
        
        if vm > vmax:
            violations.append({"bus": bus_id, "type": "High Voltage", "val": vm, "limit": vmax})
        elif vm < vmin:
            violations.append({"bus": bus_id, "type": "Low Voltage", "val": vm, "limit": vmin})
            
    return violations

def check_thermal_violations(case):
    """
    Checks for branch thermal limit violations (RATE_A).
    """
    violations = []
    for i in range(len(case.branch)):
        limit = case.branch[i, RATE_A]
        if limit <= 0:
            continue
            
        # Flow magnitude is sqrt(P^2 + Q^2)
        # Use from-side flow for check
        pf = case.branch[i, PF]
        qf = case.branch[i, QF]
        flow = np.sqrt(pf**2 + qf**2)
        
        if flow > limit:
            f_bus = int(case.external_bus_ids[int(case.branch[i, F_BUS])])
            t_bus = int(case.external_bus_ids[int(case.branch[i, T_BUS])])
            violations.append({
                "branch": f"{f_bus}-{t_bus}",
                "val": flow,
                "limit": limit,
                "loading": (flow / limit) * 100
            })
            
    return violations
