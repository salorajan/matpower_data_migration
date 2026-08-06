# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from ..core.constants import *

def calculate_total_cost(case):
    """
    Calculates total generation cost based on case.gencost and case.gen[:, PG].
    
    Args:
        case: PowerCase object.
        
    Returns:
        float: Total cost.
    """
    total_cost = 0.0
    ng = len(case.gen)
    
    # If no gencost, return a simple sum of Pg^2 as a fallback
    if len(case.gencost) < ng:
        return np.sum(np.square(case.gen[:, PG]))
        
    for i in range(ng):
        # Only count generators that are in service
        if case.gen[i, GEN_STATUS] <= 0:
            continue
            
        model = int(case.gencost[i, MODEL])
        ncost = int(case.gencost[i, NCOST])
        pg = case.gen[i, PG]
        
        if model == POLYNOMIAL:
            # Polynomial cost: c(n-1)*p^(n-1) + ... + c1*p + c0
            cost_coeffs = case.gencost[i, COST:COST+ncost]
            for j, coeff in enumerate(cost_coeffs):
                exponent = ncost - 1 - j
                total_cost += coeff * (pg ** exponent)
        elif model == PW_LINEAR:
            # Piecewise linear: (p0, c0), (p1, c1), ...
            # Not fully implemented yet, use linear approximation between points
            points = case.gencost[i, COST:COST+2*ncost].reshape(-1, 2)
            # Find which segment Pg falls into
            if pg <= points[0, 0]:
                total_cost += points[0, 1]
            elif pg >= points[-1, 0]:
                total_cost += points[-1, 1]
            else:
                for j in range(len(points)-1):
                    if points[j, 0] <= pg <= points[j+1, 0]:
                        # Linear interpolation
                        slope = (points[j+1, 1] - points[j, 1]) / (points[j+1, 0] - points[j, 0])
                        total_cost += points[j, 1] + slope * (pg - points[j, 0])
                        break
                        
    return total_cost
