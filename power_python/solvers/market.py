# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
import pandas as pd
from ..core.constants import *
from .dcopf import run_dc_opf

def run_market_auction(case, offers, bids=None, verbose=True):
    """
    Simulates a Smart Market Auction.
    
    Args:
        case: PowerCase object.
        offers: Dict with 'qty' and 'prc' (NG x N_blocks).
        bids: Dict with 'qty' and 'prc' (NB x N_blocks) - optional, 
              if None, loads are treated as fixed (price-inelastic).
        verbose: Print progress.
        
    Returns:
        tuple: (updated_case, results_dict)
    """
    case.to_internal()
    ng = len(case.gen)
    nb = len(case.bus)
    
    # 1. Update Generator Costs with Offers
    # We convert price/quantity blocks into piecewise linear (PWL) costs
    new_gencost = np.zeros((ng, 25)) # Large enough for PWL
    
    for i in range(ng):
        qty_blocks = np.array(offers['qty'][i])
        prc_blocks = np.array(offers['prc'][i])
        
        # Sort blocks by price
        idx = np.argsort(prc_blocks)
        qty_s = qty_blocks[idx]
        prc_s = prc_blocks[idx]
        
        # Build PWL points: (0, 0), (q1, q1*p1), (q1+q2, q1*p1 + q2*p2), ...
        n_pts = len(qty_s) + 1
        points = np.zeros((n_pts, 2))
        curr_q = 0
        curr_c = 0
        for j in range(len(qty_s)):
            curr_q += qty_s[j]
            curr_c += qty_s[j] * prc_s[j]
            points[j+1, 0] = curr_q
            points[j+1, 1] = curr_c
            
        # Store in gencost
        new_gencost[i, MODEL] = PW_LINEAR
        new_gencost[i, NCOST] = n_pts
        # Points are stored as x1, y1, x2, y2...
        flat_pts = points.flatten()
        new_gencost[i, COST : COST + len(flat_pts)] = flat_pts
        
        # Update Gen Pmax to match total offer quantity
        case.gen[i, PMAX] = np.sum(qty_s)
        case.gen[i, PMIN] = 0 # Assume gens can be off
        
    case.gencost = new_gencost
    
    # 2. Handle Demand Bids (Dispatchable Loads)
    # For now, we'll keep loads fixed as per the base case, 
    # which is equivalent to infinite-price bids.
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'SMART MARKET AUCTION':^80}")
        print("="*80)
        print(f"Clearing market for {ng} generators...")

    # 3. Solve OPF (Market Clearing)
    # Use DC-OPF to get nodal prices (LMPs)
    case, success = run_dc_opf(case, verbose=False)
    
    if success:
        # 4. Settle Market
        # Quantities cleared are the Pg values from the OPF
        cleared_q = case.gen[:, PG]
        # Prices are the LMPs at the generator buses
        nodal_prices = case.bus[case.gen[:, GEN_BUS].astype(int), LAM_P]
        
        revenue = cleared_q * nodal_prices
        
        market_results = pd.DataFrame({
            "Gen_ID": np.arange(ng),
            "Bus_ID": case.external_bus_ids[case.gen[:, GEN_BUS].astype(int)].astype(int),
            "Cleared_MW": cleared_q,
            "Price_$/MWh": nodal_prices,
            "Revenue_$": revenue
        })
        
        if verbose:
            print(f"Market Cleared successfully.")
            total_rev = np.sum(revenue)
            print(f"Total Market Turnover: ${total_rev:,.2f}")
            
        return case, market_results
    else:
        if verbose: print("Market Clearing Failed (OPF Infeasible).")
        return case, None

def print_market_results(df):
    """Prints a formatted market clearing report."""
    print("\n" + "="*80)
    print(f"{'MARKET CLEARING REPORT':^80}")
    print("="*80)
    print(f"{'Gen':<6} {'Bus':<8} {'Cleared MW':<15} {'Price ($/MWh)':<15} {'Revenue ($)':<15}")
    print("-" * 75)
    
    for _, row in df.iterrows():
        print(f"{int(row['Gen_ID']):<6} {int(row['Bus_ID']):<8} {row['Cleared_MW']:<15.2f} {row['Price_$/MWh']:<15.2f} {row['Revenue_$']:<15.2f}")
    
    print("="*80 + "\n")
