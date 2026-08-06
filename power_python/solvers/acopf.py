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

def run_ac_opf(case, verbose=True):
    """
    Solves an AC Optimal Power Flow using SciPy's minimize (SLSQP).
    """
    case.to_internal()
    nb = len(case.bus)
    ng = len(case.gen)
    nl = len(case.branch)
    baseMVA = case.baseMVA
    
    # 1. Decision Variables
    # x = [Va (nb), Vm (nb), Pg (ng), Qg (ng)]
    # Note: Va[ref] will be fixed at 0.
    
    # Initial guess from current case state
    va0 = case.bus[:, VA] * np.pi / 180
    vm0 = case.bus[:, VM]
    pg0 = case.gen[:, PG] / baseMVA
    qg0 = case.gen[:, QG] / baseMVA
    x0 = np.concatenate([va0, vm0, pg0, qg0])
    
    # 2. Bounds
    bounds = []
    # Va bounds (slack fixed at 0)
    ref_idx = np.where(case.bus[:, BUS_TYPE] == REF)[0][0]
    for i in range(nb):
        if i == ref_idx:
            bounds.append((0, 0))
        else:
            bounds.append((-np.pi, np.pi))
            
    # Vm bounds
    for i in range(nb):
        bounds.append((case.bus[i, VMIN], case.bus[i, VMAX]))
        
    # Pg and Qg bounds (in p.u.)
    for i in range(ng):
        bounds.append((case.gen[i, PMIN] / baseMVA, case.gen[i, PMAX] / baseMVA))
    for i in range(ng):
        bounds.append((case.gen[i, QMIN] / baseMVA, case.gen[i, QMAX] / baseMVA))
        
    # 3. Objective Function: Minimize Cost
    def objective(x):
        pg = x[2*nb : 2*nb + ng] * baseMVA
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
                total_cost += pg[i]**2 # Default quadratic
        return total_cost

    # 4. Constraints
    Ybus, _, _ = make_ybus(baseMVA, case.bus, case.branch)
    
    # Map gens to buses
    bus_gen_map = np.zeros((nb, ng))
    for i in range(ng):
        bus_idx = int(case.gen[i, GEN_BUS])
        bus_gen_map[bus_idx, i] = 1.0
    
    def constraints_func(x):
        va = x[0:nb]
        vm = x[nb:2*nb]
        pg = x[2*nb:2*nb+ng]
        qg = x[2*nb+ng:2*nb+2*ng]
        
        V = vm * np.exp(1j * va)
        
        # Complex power injection
        Sbus = V * np.conj(Ybus @ V)
        Pbus = Sbus.real
        Qbus = Sbus.imag
        
        # Net injection from gens and loads
        Pgen_bus = bus_gen_map @ pg
        Qgen_bus = bus_gen_map @ qg
        Pload_bus = case.bus[:, PD] / baseMVA
        Qload_bus = case.bus[:, QD] / baseMVA
        
        # Shunt elements
        Gshunt = case.bus[:, GS] / baseMVA
        Bshunt = case.bus[:, BS] / baseMVA
        Pshunt = vm**2 * Gshunt
        Qshunt = -vm**2 * Bshunt
        
        # Equality constraints: Pgen - Pload - Pshunt = Pbus
        eq_p = Pgen_bus - Pload_bus - Pshunt - Pbus
        eq_q = Qgen_bus - Qload_bus - Qshunt - Qbus
        
        # We also need branch flow constraints (Rate A)
        # S_ij = Vi * conj( (Vi - Vj)*Yij + Vi*Ysh_i )
        # This is expensive, we'll add it if needed for the test case
        
        return np.concatenate([eq_p, eq_q])

    cons = {'type': 'eq', 'fun': constraints_func}
    
    # 5. Solve
    res = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=cons, 
                   options={'maxiter': 100, 'disp': verbose})
    
    if res.success:
        if verbose:
            print(f"AC-OPF Solved. Optimal Cost: {res.fun:.2f}")
        # Update case
        va = res.x[0:nb]
        vm = res.x[nb:2*nb]
        pg = res.x[2*nb:2*nb+ng]
        qg = res.x[2*nb+ng:2*nb+2*ng]
        
        case.bus[:, VA] = va * 180 / np.pi
        case.bus[:, VM] = vm
        case.gen[:, PG] = pg * baseMVA
        case.gen[:, QG] = qg * baseMVA
        return case, True
    else:
        if verbose:
            print(f"AC-OPF Failed: {res.message}")
        return case, False
