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
        
        # Internal mapping
        self.bus_map = {} # External BUS_I -> Internal 0-based index

    def load_from_json(self, file_path):
        """
        Loads case data from a JSON file formatted by the project converters.
        """
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
                # ... other columns as needed for OPF
        
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

    def get_internal_bus_idx(self, external_id):
        return self.bus_map.get(int(external_id))

    def to_internal(self):
        """
        Converts external bus numbers to internal 0-based indices.
        Updates the matrices in-place.
        """
        # Create a copy of the mapping for efficiency
        mapping = self.bus_map
        
        # Update Bus matrix
        # BUS_I column stays as external for reference, or we can replace it.
        # MATPOWER usually replaces it. Let's follow that.
        # But we need to save the original IDs if we want to go back.
        self.external_bus_ids = self.bus[:, BUS_I].copy()
        self.bus[:, BUS_I] = np.arange(len(self.bus))
        
        # Update Generator matrix
        for i in range(len(self.gen)):
            self.gen[i, GEN_BUS] = mapping[int(self.gen[i, GEN_BUS])]
            
        # Update Branch matrix
        for i in range(len(self.branch)):
            self.branch[i, F_BUS] = mapping[int(self.branch[i, F_BUS])]
            self.branch[i, T_BUS] = mapping[int(self.branch[i, T_BUS])]

    def __repr__(self):
        return f"PowerCase(baseMVA={self.baseMVA}, nb={len(self.bus)}, ng={len(self.gen)}, nl={len(self.branch)})"
