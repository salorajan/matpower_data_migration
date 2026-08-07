# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import numpy as np
import json
from .constants import *

class PowerCase:
    """
    Core data structure for a power system case.
    Stores data in NumPy arrays mirroring MATPOWER matrices.
    """
    def __init__(self, baseMVA=100.0):
        self.baseMVA = baseMVA
        # Matrices initialized as empty arrays with correct number of columns
        self.bus = np.empty((0, 17))
        self.gen = np.empty((0, 25))
        self.branch = np.empty((0, 21))
        self.gencost = np.empty((0, 7)) # Minimum columns for gencost
        self.reserves = {} # Reserve zones, requirements, costs
        
        # 3-Phase Data (Unbalanced)
        self.bus3p = np.empty((0, 9))
        self.line3p = np.empty((0, 6))
        self.xfmr3p = np.empty((0, 9))
        self.load3p = np.empty((0, 9))
        self.gen3p = np.empty((0, 12))
        self.lc = np.empty((0, 19))
        
        # Multi-period & Storage Data
        self.storage = {}   # UnitIdx, MaxStorage, InEff, OutEff, etc.
        self.profiles = {}  # Type ('load', 'gen'), idx, values (nt x 1)
        
        # Internal mapping
        self.bus_map = {} # External BUS_I -> Internal 0-based index
        self.is_internal = False
        self.external_bus_ids = None
        self.external_gen_ids = None

    def load_from_json(self, file_path):
        """
        Loads case data from a JSON file formatted by the project converters.
        """
        self.is_internal = False
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if "General" in data and len(data["General"]) > 0:
            self.baseMVA = data["General"][0].get("baseMVA", 100.0)
        
        if "Bus" in data:
            bus_list = data["Bus"]
            self.bus = np.zeros((len(bus_list), 17))
            for i, b in enumerate(bus_list):
                self.bus[i, BUS_I] = b.get("BUS_I")
                self.bus[i, BUS_TYPE] = b.get("TYPE")
                self.bus[i, PD] = b.get("PD", 0.0)
                self.bus[i, QD] = b.get("QD", 0.0)
                self.bus[i, GS] = b.get("GS", 0.0)
                self.bus[i, BS] = b.get("BS", 0.0)
                self.bus[i, BUS_AREA] = b.get("BUS_AREA", 1)
                self.bus[i, VM] = b.get("VM", 1.0)
                self.bus[i, VA] = b.get("VA", 0.0)
                self.bus[i, BASE_KV] = b.get("BASE_KV", 0.0)
                self.bus[i, ZONE] = b.get("ZONE", 1)
                self.bus[i, VMAX] = b.get("VMAX", 1.1)
                self.bus[i, VMIN] = b.get("VMIN", 0.9)
            
            # Build internal mapping
            self.bus_map = {int(val): i for i, val in enumerate(self.bus[:, BUS_I])}

        if "Generator" in data:
            gen_list = data["Generator"]
            self.gen = np.zeros((len(gen_list), 25))
            for i, g in enumerate(gen_list):
                self.gen[i, GEN_BUS] = g.get("GEN_BUS")
                self.gen[i, PG] = g.get("PG", 0.0)
                self.gen[i, QG] = g.get("QG", 0.0)
                self.gen[i, QMAX] = g.get("QMAX", 0.0)
                self.gen[i, QMIN] = g.get("QMIN", 0.0)
                self.gen[i, VG] = g.get("VG", 1.0)
                self.gen[i, MBASE] = g.get("MBASE", self.baseMVA)
                self.gen[i, GEN_STATUS] = g.get("GEN_STATUS", 1)
                self.gen[i, PMAX] = g.get("PMAX", 0.0)
                self.gen[i, PMIN] = g.get("PMIN", 0.0)
        
        if "Branch" in data:
            branch_list = data["Branch"]
            self.branch = np.zeros((len(branch_list), 21))
            for i, br in enumerate(branch_list):
                self.branch[i, F_BUS] = br.get("F_BUS")
                self.branch[i, T_BUS] = br.get("T_BUS")
                self.branch[i, BR_R] = br.get("BR_R", 0.0)
                self.branch[i, BR_X] = br.get("BR_X", 0.0)
                self.branch[i, BR_B] = br.get("BR_B", 0.0)
                self.branch[i, RATE_A] = br.get("RATE_A", 0.0)
                self.branch[i, RATE_B] = br.get("RATE_B", 0.0)
                self.branch[i, RATE_C] = br.get("RATE_C", 0.0)
                self.branch[i, TAP] = br.get("TAP", 0.0)
                self.branch[i, SHIFT] = br.get("SHIFT", 0.0)
                self.branch[i, BR_STATUS] = br.get("BR_STATUS", 1)
                self.branch[i, ANGMIN] = br.get("ANGMIN", -360)
                self.branch[i, ANGMAX] = br.get("ANGMAX", 360)

        if "Generator Cost" in data:
            cost_list = data["Generator Cost"]
            self.gencost = np.zeros((len(cost_list), 25)) # Large enough for many coefficients
            for i, c in enumerate(cost_list):
                self.gencost[i, MODEL] = c.get("MODEL")
                self.gencost[i, STARTUP] = c.get("STARTUP", 0.0)
                self.gencost[i, SHUTDOWN] = c.get("SHUTDOWN", 0.0)
                self.gencost[i, NCOST] = c.get("NCOST")
                # Handle arbitrary number of cost coefficients
                if "COST" in c:
                    costs = c["COST"]
                    for j, val in enumerate(costs):
                        if COST + j < self.gencost.shape[1]:
                            self.gencost[i, COST + j] = val
                            
        if "Reserves" in data:
            self.reserves = data["Reserves"]
            
        # Load 3-Phase Data
        if "Bus3P" in data:
            self.bus3p = np.array(data["Bus3P"])
        if "Line3P" in data:
            self.line3p = np.array(data["Line3P"])
        if "Xfmr3P" in data:
            self.xfmr3p = np.array(data["Xfmr3P"])
        if "Load3P" in data:
            self.load3p = np.array(data["Load3P"])
        if "Gen3P" in data:
            self.gen3p = np.array(data["Gen3P"])
        if "LineConst" in data:
            self.lc = np.array(data["LineConst"])

    def get_internal_bus_idx(self, external_id):
        return self.bus_map.get(int(external_id))

    def to_internal(self):
        """
        Converts external bus numbers to internal 0-based indices.
        Updates the matrices in-place. Idempotent.
        """
        if self.is_internal:
            return
            
        # Create a copy of the mapping for efficiency
        mapping = self.bus_map
        
        # Update Bus matrix
        self.external_bus_ids = self.bus[:, BUS_I].copy()
        self.bus[:, BUS_I] = np.arange(len(self.bus))
        
        # Update Generator matrix
        self.external_gen_ids = np.arange(len(self.gen))
        for i in range(len(self.gen)):
            self.gen[i, GEN_BUS] = mapping[int(self.gen[i, GEN_BUS])]
            
        # Update Branch matrix
        for i in range(len(self.branch)):
            self.branch[i, F_BUS] = mapping[int(self.branch[i, F_BUS])]
            self.branch[i, T_BUS] = mapping[int(self.branch[i, T_BUS])]
            
        self.is_internal = True

    def update_generator_power(self):
        """
        Re-calculates and updates generator PG and QG outputs based on the
        solved bus voltages VM and VA and branch parameters.
        """
        if self.bus is None or len(self.bus) == 0 or self.gen is None or len(self.gen) == 0:
            return
            
        from ..network.admittance import make_ybus
        
        # Save state and convert to internal representation if not already
        was_internal = self.is_internal
        if not was_internal:
            self.to_internal()
            
        try:
            V = self.bus[:, VM] * np.exp(1j * np.pi / 180 * self.bus[:, VA])
            Ybus, _, _ = make_ybus(self.baseMVA, self.bus, self.branch)
            S_inj = V * np.conj(Ybus @ V)
            
            P_inj = S_inj.real * self.baseMVA
            Q_inj = S_inj.imag * self.baseMVA
            
            # Find online generators
            online_gens = np.where(self.gen[:, GEN_STATUS] > 0)[0]
            
            # Group online generators by bus index
            gens_by_bus = {}
            for g in online_gens:
                bus_idx = int(self.gen[g, GEN_BUS])
                if bus_idx not in gens_by_bus:
                    gens_by_bus[bus_idx] = []
                gens_by_bus[bus_idx].append(g)
                
            for bus_idx, gens in gens_by_bus.items():
                bus_type = int(self.bus[bus_idx, BUS_TYPE])
                
                # Update QG for PV and Slack buses
                if bus_type in [PV, REF]:
                    q_gen_total = Q_inj[bus_idx] + self.bus[bus_idx, QD]
                    
                    if len(gens) == 1:
                        self.gen[gens[0], QG] = q_gen_total
                    else:
                        q_min_sum = sum(self.gen[g, QMIN] for g in gens)
                        q_max_sum = sum(self.gen[g, QMAX] for g in gens)
                        q_range_sum = q_max_sum - q_min_sum
                        
                        if q_range_sum > 0:
                            for g in gens:
                                g_range = self.gen[g, QMAX] - self.gen[g, QMIN]
                                self.gen[g, QG] = self.gen[g, QMIN] + (q_gen_total - q_min_sum) * (g_range / q_range_sum)
                        else:
                            for g in gens:
                                self.gen[g, QG] = q_gen_total / len(gens)
                                
                # Update PG for Slack (REF) buses
                if bus_type == REF:
                    p_gen_total = P_inj[bus_idx] + self.bus[bus_idx, PD]
                    
                    if len(gens) == 1:
                        self.gen[gens[0], PG] = p_gen_total
                    else:
                        mbase_sum = sum(self.gen[g, MBASE] for g in gens)
                        if mbase_sum > 0:
                            for g in gens:
                                self.gen[g, PG] = p_gen_total * (self.gen[g, MBASE] / mbase_sum)
                        else:
                            for g in gens:
                                self.gen[g, PG] = p_gen_total / len(gens)
        except Exception as e:
            print(f"Warning: Failed to update generator active/reactive power: {e}")

    def copy(self):
        import copy
        return copy.deepcopy(self)

    def __repr__(self):
        return f"PowerCase(baseMVA={self.baseMVA}, nb={len(self.bus)}, ng={len(self.gen)}, nl={len(self.branch)})"
