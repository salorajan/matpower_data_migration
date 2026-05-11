import cvxpy as cp
import numpy as np
from ..core.constants import *
from ..network.sensitivity import make_ptdf, make_lodf

def run_sc_opf(case, verbose=True):
    """
    Solves a Security-Constrained DC OPF (SC-OPF) using CVXPY.
    Ensures that no single line outage results in a violation.
    
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
    
    # 1. Sensitivity Factors
    PTDF = make_ptdf(baseMVA, case.bus, case.branch)
    LODF = make_lodf(case.branch, PTDF)
    
    # 2. Decision Variables
    Pg = cp.Variable(ng) # Gen real power (MW)
    
    # 3. Objective Function (Minimize Quadratic/Linear Costs)
    costs = []
    has_cost = len(case.gencost) >= ng
    for i in range(ng):
        if has_cost:
            model = case.gencost[i, MODEL]
            ncost = int(case.gencost[i, NCOST])
            if model == POLYNOMIAL:
                if ncost == 3:
                    c2, c1, c0 = case.gencost[i, COST:COST+3]
                    costs.append(c2 * cp.square(Pg[i]) + c1 * Pg[i] + c0)
                elif ncost == 2:
                    c1, c0 = case.gencost[i, COST:COST+2]
                    costs.append(c1 * Pg[i] + c0)
        else:
            costs.append(cp.square(Pg[i]))
    objective = cp.Minimize(cp.sum(costs))
    
    # 4. Constraints
    constraints = []
    
    # Gen Limits
    constraints += [Pg >= case.gen[:, PMIN], Pg <= case.gen[:, PMAX]]
    
    # Nodal Power Balance (Net Injection = Pgen - Pload)
    Pd = case.bus[:, PD]
    bus_gen_map = np.zeros((nb, ng))
    for i in range(ng):
        bus_idx = int(case.gen[i, GEN_BUS])
        bus_gen_map[bus_idx, i] = 1.0
        
    Pgen_bus = bus_gen_map @ Pg
    Pinj_pu = (Pgen_bus - Pd) / baseMVA
    
    # Global balance: Sum(Pg) = Sum(Pd) (DC ignores losses)
    constraints += [cp.sum(Pg) == np.sum(Pd)]
    
    # 5. Line Flow Constraints (Base Case)
    # Flow = PTDF * Pinj
    flows_pu = PTDF @ Pinj_pu
    for i in range(nl):
        limit = case.branch[i, RATE_A]
        if limit > 0:
            limit_pu = limit / baseMVA
            constraints += [flows_pu[i] <= limit_pu, flows_pu[i] >= -limit_pu]
            
    # 6. Contingency Constraints (N-1 Security)
    # Flow_new(i, outage j) = Flow_base(i) + LODF(i, j) * Flow_base(j)
    # We add this for every non-bridge outage j
    for j in range(nl):
        if np.isnan(LODF[j, j]) or case.branch[j, BR_STATUS] <= 0:
            continue
            
        # Post-outage flows for contingency j
        # Note: We use the expression for post_flows directly as an optimization constraint
        for i in range(nl):
            if i == j: continue
            limit = case.branch[i, RATE_A]
            if limit > 0:
                lodf_val = LODF[i, j]
                # Skip if LODF is NaN or Inf (should be handled by bridge check, but for safety)
                if not np.isfinite(lodf_val):
                    continue
                    
                limit_pu = limit / baseMVA
                post_flow_ij = flows_pu[i] + lodf_val * flows_pu[j]
                constraints += [post_flow_ij <= limit_pu, post_flow_ij >= -limit_pu]
                
    # 7. Solve
    prob = cp.Problem(objective, constraints)
    prob.solve(verbose=verbose)
    
    if prob.status in ["optimal", "feasible"]:
        if verbose:
            print(f"SC-OPF Solved. Optimal Cost: {prob.value:.2f}")
        case.gen[:, PG] = Pg.value
        return case, True
    else:
        if verbose:
            print(f"SC-OPF Failed: {prob.status}")
        return case, False
