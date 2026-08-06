# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import pandas as pd
import numpy as np
from ..core.constants import *

def print_pf_results(case):
    """
    Prints a formatted report of power flow results.
    """
    print("\n" + "="*80)
    print(f"{'POWER FLOW RESULTS':^80}")
    print("="*80)
    
    # 1. Bus Data
    print("\nBUS DATA")
    print("-" * 65)
    print(f"{'Bus':<6} {'Mag(pu)':<10} {'Ang(deg)':<10} {'P Load(MW)':<12} {'Q Load(MVAr)':<12}")
    print("-" * 65)
    
    for i in range(len(case.bus)):
        bus_id = int(case.external_bus_ids[i])
        vm = case.bus[i, VM]
        va = case.bus[i, VA]
        pd_val = case.bus[i, PD]
        qd_val = case.bus[i, QD]
        print(f"{bus_id:<6} {vm:<10.4f} {va:<10.4f} {pd_val:<12.2f} {qd_val:<12.2f}")

    # 2. Branch Data
    print("\nBRANCH DATA (Flows)")
    print("-" * 75)
    print(f"{'From':<6} {'To':<6} {'P_f (MW)':<12} {'Q_f (MVAr)':<12} {'P_t (MW)':<12} {'Q_t (MVAr)':<12}")
    print("-" * 75)
    
    for i in range(len(case.branch)):
        f_bus = int(case.external_bus_ids[int(case.branch[i, F_BUS])])
        t_bus = int(case.external_bus_ids[int(case.branch[i, T_BUS])])
        pf = case.branch[i, PF]
        qf = case.branch[i, QF]
        pt = case.branch[i, PT]
        qt = case.branch[i, QT]
        print(f"{f_bus:<6} {t_bus:<6} {pf:<12.2f} {qf:<12.2f} {pt:<12.2f} {qt:<12.2f}")

    # 3. System Summary
    print("\nSYSTEM SUMMARY")
    print("-" * 30)
    total_load_p = np.sum(case.bus[:, PD])
    total_load_q = np.sum(case.bus[:, QD])
    total_loss_p = np.sum(case.branch[:, PF] + case.branch[:, PT])
    total_loss_q = np.sum(case.branch[:, QF] + case.branch[:, QT])
    
    print(f"Total Load:    {total_load_p:10.2f} MW    {total_load_q:10.2f} MVAr")
    print(f"Total Losses:  {total_loss_p:10.2f} MW    {total_loss_q:10.2f} MVAr")
    print("="*80 + "\n")

def print_audit_report(case):
    """
    Prints a detailed audit report: Physical Balance and Violations.
    """
    from .audit import calculate_system_balance, check_voltage_violations, check_thermal_violations
    
    balance = calculate_system_balance(case)
    v_violations = check_voltage_violations(case)
    t_violations = check_thermal_violations(case)
    
    print("\n" + "="*80)
    print(f"{'SYSTEM AUDIT REPORT':^80}")
    print("="*80)
    
    # 1. Physical Balance
    print("\n1.0 PHYSICAL POWER BALANCE")
    print("-" * 50)
    print(f"{'Component':<15} {'Real (MW)':<15} {'Reactive (MVAr)':<15}")
    print("-" * 50)
    print(f"{'Total Generation':<15} {balance['gen_p']:<15.2f} {balance['gen_q']:<15.2f}")
    print(f"{'Total Load':<15} {balance['load_p']:<15.2f} {balance['load_q']:<15.2f}")
    print(f"{'Total Losses':<15} {balance['loss_p']:<15.2f} {balance['loss_q']:<15.2f}")
    print("-" * 50)
    print(f"{'RESIDUAL':<15} {balance['residual_p']:<15.2f} {balance['residual_q']:<15.2f}")
    
    # 2. Voltage Violations
    print("\n2.0 VOLTAGE VIOLATION SUMMARY")
    print("-" * 50)
    if not v_violations:
        print("No voltage violations detected.")
    else:
        print(f"{'Bus':<10} {'Type':<15} {'Value (pu)':<15} {'Limit (pu)':<10}")
        for v in v_violations:
            print(f"{v['bus']:<10} {v['type']:<15} {v['val']:<15.4f} {v['limit']:<10.2f}")
            
    # 3. Thermal Violations
    print("\n3.0 THERMAL VIOLATION SUMMARY")
    print("-" * 50)
    if not t_violations:
        print("No branch thermal violations detected.")
    else:
        print(f"{'Branch':<15} {'Flow (MVA)':<15} {'Limit (MVA)':<15} {'Loading (%)':<10}")
        for t in t_violations:
            print(f"{t['branch']:<15} {t['val']:<15.2f} {t['limit']:<15.2f} {t['loading']:<10.1f}%")
            
    print("\n" + "="*80 + "\n")

def print_3p_results(case):
    """
    Prints results for a 3-Phase unbalanced simulation.
    """
    print("\n" + "="*80)
    print(f"{'THREE-PHASE UNBALANCED RESULTS':^80}")
    print("="*80)
    print(f"{'Bus':<6} {'Phase A VM':<12} {'Phase B VM':<12} {'Phase C VM':<12}")
    print(f"{'':<6} {'Phase A VA':<12} {'Phase B VA':<12} {'Phase C VA':<12}")
    print("-" * 65)
    
    for i in range(len(case.bus3p)):
        bus_id = int(case.bus3p[i, 0])
        vmag = case.bus3p[i, 3:6]
        vang = case.bus3p[i, 6:9]
        
        print(f"{bus_id:<6} {vmag[0]:<12.4f} {vmag[1]:<12.4f} {vmag[2]:<12.4f}")
        print(f"{'':<6} {vang[0]:<12.2f} {vang[1]:<12.2f} {vang[2]:<12.2f}")
        print("-" * 65)
        
    print("="*80 + "\n")
