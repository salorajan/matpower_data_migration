# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
from ..core.constants import *

def make_sbus(baseMVA, bus, gen):
    """
    Builds the vector of complex bus power injections (per unit).
    generation - load
    """
    nb = bus.shape[0]
    ng = gen.shape[0]
    
    # Net generation at each bus
    # Note: Multiple generators can be at the same bus
    Sg = np.zeros(nb, dtype=complex)
    for i in range(ng):
        if gen[i, GEN_STATUS] > 0:
            bus_idx = int(gen[i, GEN_BUS])
            Sg[bus_idx] += (gen[i, PG] + 1j * gen[i, QG]) / baseMVA
            
    # Load at each bus
    # Pload = PD / baseMVA, Qload = QD / baseMVA
    Sd = (bus[:, PD] + 1j * bus[:, QD]) / baseMVA
    
    # Shunts are handled in Ybus, so they are not part of Sbus here
    # in MATPOWER makeSbus.m
    
    return Sg - Sd
