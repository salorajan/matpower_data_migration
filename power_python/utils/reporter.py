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
