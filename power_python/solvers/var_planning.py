# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from scipy.optimize import minimize
from ..core.constants import *
from ..network.admittance import make_ybus

def run_var_planning(case, candidate_buses=None, cap_cost=100.0, max_b=0.5, verbose=True):
    """
    Performs Optimal Capacitor Placement (VAr Planning) using AC-OPF.
    Determines where and how much reactive compensation (Bshunt) is needed
    to maintain voltage profiles at minimum cost.
    
    Args:
        case: PowerCase object.
        candidate_buses: List of external bus IDs where capacitors can be placed.
                         If None, all PQ buses are candidates.
        cap_cost: Cost of installing 1.0 p.u. of shunt susceptance ($/pu).
        max_b: Maximum susceptance per bus (p.u.).
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, success)
    """
    case.to_internal()
    nb = len(case.bus)
    ng = len(case.gen)
    baseMVA = case.baseMVA
    
    # 1. Identify Candidate Buses
    if candidate_buses is None:
        # Default: All PQ buses are candidates
        candidates = np.where(case.bus[:, BUS_TYPE] == PQ)[0]
    else:
        candidates = [case.bus_map[int(bid)] for bid in candidate_buses]
    
    nc = len(candidates)
    
    # 2. Decision Variables
    # x = [Va (nb), Vm (nb), Pg (ng), Qg (ng), Bsh (nc)]
    
    va0 = case.bus[:, VA] * np.pi / 180
    vm0 = case.bus[:, VM]
    pg0 = case.gen[:, PG] / baseMVA
    qg0 = case.gen[:, QG] / baseMVA
    bsh0 = np.zeros(nc) # Start with no capacitors
    
    x0 = np.concatenate([va0, vm0, pg0, qg0, bsh0])
    
    # 3. Bounds
    bounds = []
    # Va
    ref_idx = np.where(case.bus[:, BUS_TYPE] == REF)[0][0]
    for i in range(nb):
        bounds.append((0, 0) if i == ref_idx else (-np.pi, np.pi))
    # Vm
    for i in range(nb):
        bounds.append((case.bus[i, VMIN], case.bus[i, VMAX]))
    # Pg
    for i in range(ng):
        bounds.append((case.gen[i, PMIN] / baseMVA, case.gen[i, PMAX] / baseMVA))
    # Qg
    for i in range(ng):
        bounds.append((case.gen[i, QMIN] / baseMVA, case.gen[i, QMAX] / baseMVA))
    # Bsh
    for i in range(nc):
        bounds.append((0, max_b)) # Positive B is capacitive (injects Q)
        
    # 4. Objective: Gen Cost + Capacitor Cost
    def objective(x):
        pg = x[2*nb : 2*nb + ng] * baseMVA
        bsh = x[2*nb + 2*ng :]
        
        # Gen Cost
        total_cost = 0
        has_cost = len(case.gencost) >= ng
        for i in range(ng):
            if has_cost:
                model = int(case.gencost[i, MODEL])
                ncost = int(case.gencost[i, NCOST])
                cost_params = case.gencost[i, COST:COST+ncost]
                if model == POLYNOMIAL:
                    p = pg[i]
                    val = 0
                    for j, coeff in enumerate(cost_params):
                        val += coeff * (p ** (ncost - 1 - j))
                    total_cost += val
            else:
                total_cost += pg[i]**2
                
        # Capacitor Cost
        total_cost += np.sum(bsh * cap_cost)
        
        return total_cost

    # 5. Constraints
    Ybus, _, _ = make_ybus(baseMVA, case.bus, case.branch)
    bus_gen_map = np.zeros((nb, ng))
    for i in range(ng):
        bus_gen_map[int(case.gen[i, GEN_BUS]), i] = 1.0
        
    def constraints_func(x):
        va = x[0:nb]
        vm = x[nb:2*nb]
        pg = x[2*nb:2*nb+ng]
        qg = x[2*nb+ng:2*nb+2*ng]
        bsh_vars = x[2*nb+2*ng:]
        
        V = vm * np.exp(1j * va)
        Sbus = V * np.conj(Ybus @ V)
        
        # Net injection
        Pgen_bus = bus_gen_map @ pg
        Qgen_bus = bus_gen_map @ qg
        Pload_bus = case.bus[:, PD] / baseMVA
        Qload_bus = case.bus[:, QD] / baseMVA
        
        # Static Shunts
        Gshunt = case.bus[:, GS] / baseMVA
        Bshunt = case.bus[:, BS] / baseMVA
        
        # Dynamic Optimized Shunts
        Bsh_opt = np.zeros(nb)
        for i, bus_idx in enumerate(candidates):
            Bsh_opt[bus_idx] = bsh_vars[i]
            
        # Q_inj_shunt = V^2 * (B_static + B_opt)
        # Note: B > 0 injects Q (capacitive)
        Qshunt_total = vm**2 * (Bshunt + Bsh_opt)
        
        # Equality: Pgen - Pload - Pshunt = Pbus
        eq_p = Pgen_bus - Pload_bus - (vm**2 * Gshunt) - Sbus.real
        eq_q = Qgen_bus - Qload_bus + Qshunt_total - Sbus.imag
        
        return np.concatenate([eq_p, eq_q])

    cons = {'type': 'eq', 'fun': constraints_func}

    if verbose:
        print("\n" + "="*80)
        print(f"{'VAR PLANNING / OPTIMAL CAPACITOR PLACEMENT':^80}")
        print("="*80)
        print(f"Candidates: {nc} buses | Cap Cost: ${cap_cost:.2f}/pu")

    # 6. Solve
    res = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=cons, 
                   options={'maxiter': 200, 'disp': verbose})
    
    if res.success:
        if verbose:
            print(f"VAr Planning Solved. Optimal Cost: ${res.fun:,.2f}")
        
        # Update case
        va = res.x[0:nb]
        vm = res.x[nb:2*nb]
        pg = res.x[2*nb:2*nb+ng]
        qg = res.x[2*nb+ng:2*nb+2*ng]
        bsh_final = res.x[2*nb+2*ng:]
        
        case.bus[:, VA] = va * 180 / np.pi
        case.bus[:, VM] = vm
        case.gen[:, PG] = pg * baseMVA
        case.gen[:, QG] = qg * baseMVA
        
        # Apply optimized shunts to case.bus[:, BS]
        for i, bus_idx in enumerate(candidates):
            if bsh_final[i] > 0.001:
                case.bus[bus_idx, BS] += bsh_final[i] * baseMVA
                if verbose:
                    print(f"     -> Placed Capacitor at Bus {int(case.external_bus_ids[bus_idx])}: {bsh_final[i]*baseMVA:.2f} MVAr")
        
        return case, True
    else:
        if verbose:
            print(f"VAr Planning Failed: {res.message}")
        return case, False
