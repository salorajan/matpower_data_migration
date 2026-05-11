import cvxpy as cp
import numpy as np
from ..core.constants import *
from ..network.admittance import make_ybus

def run_dc_opf(case, verbose=True):
    """
    Solves a DC Optimal Power Flow using CVXPY.
    
    Args:
        case: A PowerCase object.
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, success)
    """
    case.to_internal()
    nb = len(case.bus)
    ng = len(case.gen)
    nl = len(case.branch)
    baseMVA = case.baseMVA
    
    # 1. Constants and Indices
    ref_idx = np.where(case.bus[:, BUS_TYPE] == REF)[0][0]
    
    # 2. Build DC Network Matrices
    # Bbus * Va = Pbus
    # Pline = Bbranch * Va
    
    # For DC, we only care about reactance X and tap ratios
    # Neglect resistance and charging B
    stat = case.branch[:, BR_STATUS]
    X = case.branch[:, BR_X]
    tap = case.branch[:, TAP]
    tap[tap == 0] = 1.0
    
    # B_line = 1 / (X * tap)
    b_line = stat / (X * tap)
    
    # Bbus matrix (simplified DC)
    Bbus = np.zeros((nb, nb))
    f = case.branch[:, F_BUS].astype(int)
    t = case.branch[:, T_BUS].astype(int)
    
    for i in range(nl):
        if stat[i] > 0:
            Bbus[f[i], f[i]] += b_line[i]
            Bbus[t[i], t[i]] += b_line[i]
            Bbus[f[i], t[i]] -= b_line[i]
            Bbus[t[i], f[i]] -= b_line[i]
            
    # 3. Decision Variables
    Pg = cp.Variable(ng) # Gen real power (MW)
    Va = cp.Variable(nb) # Bus angles (radians)
    
    # 4. Objective Function: Minimize sum(Ci(Pg))
    costs = []
    
    # Check if gencost is available
    has_cost = len(case.gencost) >= ng
    
    for i in range(ng):
        if has_cost:
            # gencost: MODEL, STARTUP, SHUTDOWN, NCOST, COST...
            model = case.gencost[i, MODEL]
            ncost = int(case.gencost[i, NCOST])
            
            if model == POLYNOMIAL:
                if ncost == 3: # Quadratic: c2*p^2 + c1*p + c0
                    c2 = case.gencost[i, COST]
                    c1 = case.gencost[i, COST+1]
                    c0 = case.gencost[i, COST+2]
                    costs.append(c2 * cp.square(Pg[i]) + c1 * Pg[i] + c0)
                elif ncost == 2: # Linear: c1*p + c0
                    c1 = case.gencost[i, COST]
                    c0 = case.gencost[i, COST+1]
                    costs.append(c1 * Pg[i] + c0)
        else:
            # Default cost: Pg^2 (simple minimization)
            costs.append(cp.square(Pg[i]))
    
    objective = cp.Minimize(cp.sum(costs))
    
    # 5. Constraints
    constraints = []
    
    # Gen Limits (MW)
    constraints += [Pg >= case.gen[:, PMIN], Pg <= case.gen[:, PMAX]]
    
    # Reference Bus Angle
    constraints += [Va[ref_idx] == 0]
    
    # Power Balance (DC Approximation)
    # Sum(Pg at bus i) - Pd at bus i = Bbus * Va * baseMVA
    Pd = case.bus[:, PD]
    
    # Map generators to buses
    bus_gen_map = np.zeros((nb, ng))
    for i in range(ng):
        bus_idx = int(case.gen[i, GEN_BUS])
        bus_gen_map[bus_idx, i] = 1.0
        
    bus_gen_injections = bus_gen_map @ Pg
        
    # Nodal power balance equations
    constraints += [bus_gen_injections - Pd == (Bbus @ Va) * baseMVA]
    
    # Line Flow Limits (MW)
    # | (Va[f] - Va[t]) * b_line * baseMVA | <= RATE_A
    for i in range(nl):
        if stat[i] > 0 and case.branch[i, RATE_A] > 0:
            flow = (Va[f[i]] - Va[t[i]]) * b_line[i] * baseMVA
            constraints += [flow <= case.branch[i, RATE_A], flow >= -case.branch[i, RATE_A]]
            
    # 6. Solve
    prob = cp.Problem(objective, constraints)
    prob.solve(verbose=verbose)
    
    if prob.status in ["optimal", "feasible"]:
        if verbose:
            print(f"DC-OPF Solved. Optimal Cost: {prob.value:.2f}")
        # Update case with results
        case.gen[:, PG] = Pg.value
        case.bus[:, VA] = Va.value * 180 / np.pi
        # Vm remains 1.0 for DC
        case.bus[:, VM] = 1.0
        return case, True
    else:
        if verbose:
            print(f"DC-OPF Failed: {prob.status}")
        return case, False
