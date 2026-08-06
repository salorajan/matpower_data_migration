# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np

# 1. DATA DEFINITION (Skepticism: Using clear, small data for manual verification)
# Bus 1 to 2: R=0.02, X=0.06, B=0.06 (p.u.)
# Bus 2 to 3: R=0.01, X=0.03, B=0.02 (p.u.)
# Bus 1 to 3: R=0.0125, X=0.025, B=0.04 (p.u.)

def calculate_ybus():
    num_buses = 3
    # Initialize complex zero matrix
    Ybus = np.zeros((num_buses, num_buses), dtype=complex)
    
    # Branch data: [from_bus, to_bus, R, X, B_total]
    branches = [
        [0, 1, 0.02, 0.06, 0.06],
        [1, 2, 0.01, 0.03, 0.02],
        [0, 2, 0.0125, 0.025, 0.04]
    ]

    for branch in branches:
        fb, tb, r, x, b_total = branch
        z = r + 1j*x
        y = 1/z
        y_shunt = 1j * (b_total / 2)
        
        # Off-diagonal elements
        Ybus[fb, tb] -= y
        Ybus[tb, fb] -= y
        
        # Diagonal elements (Series + Shunt)
        Ybus[fb, fb] += y + y_shunt
        Ybus[tb, tb] += y + y_shunt

    return Ybus

# 2. NUMERICAL OUTPUT (Optimized for NVDA Screen Reader)
y_matrix = calculate_ybus()

print("--- Y-BUS CALCULATION RESULTS ---")
print(f"Matrix Dimensions: {y_matrix.shape}")
print("---------------------------------")

for i in range(len(y_matrix)):
    for j in range(len(y_matrix)):
        val = y_matrix[i, j]
        # Printing with 4 decimal precision for clarity
        print(f"Element [{i+1},{j+1}]: {val.real:+.4f} + {val.imag:+.4f}j")

print("---------------------------------")
print("Verification complete.")
