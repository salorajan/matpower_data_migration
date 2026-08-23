# PowerPython Dynamics Solver
# Copyright (c) 2026 PowerPython contributors
# Licensed under the 3-clause BSD License (see LICENSE file for details).

"""
Simulation engine for transient stability (dynamic simulation) in PowerPython.
Solves the Differential-Algebraic Equations (DAEs) of the network and dynamic models.
"""

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from power_python.core.constants import *
from power_python.network.admittance import make_ybus
from .models import MODEL_REGISTRY, GeneratorModel, ExciterModel, GovernorModel, GENCLS, GENSAL, SEXS, TGOV1

class DynamicCase:
    """Manages dynamic models mapped to network components."""
    def __init__(self):
        self.generators = {}  # gen_idx -> GeneratorModel
        self.exciters = {}    # gen_idx -> ExciterModel
        self.governors = {}   # gen_idx -> GovernorModel
        self.state_map = []   # List of (model, state_name) for flat state vector mapping

    def initialize_states(self, power_case):
        """
        Initialize the states of all dynamic models from steady-state power flow.
        """
        # Ensure power flow is solved and voltages are present
        vm = power_case.bus[:, VM]
        va = power_case.bus[:, VA]
        V_net = vm * np.exp(1j * np.pi / 180.0 * va)
        
        baseMVA = power_case.baseMVA
        
        # Initialize generator models
        for gen_idx, gen_model in self.generators.items():
            bus_idx = int(power_case.gen[gen_idx, GEN_BUS])
            Vt = V_net[bus_idx]
            
            Pg = power_case.gen[gen_idx, PG]
            Qg = power_case.gen[gen_idx, QG]
            S_inj = Pg + 1j * Qg
            mbase = power_case.gen[gen_idx, MBASE]
            
            success = gen_model.initialize(Vt, S_inj, baseMVA, mbase)
            if not success:
                return False
                
            # Initialize associated exciter
            if gen_idx in self.exciters:
                exc_model = self.exciters[gen_idx]
                exc_model.initialize(Vt, gen_model.efd)
                
            # Initialize associated governor
            if gen_idx in self.governors:
                gov_model = self.governors[gen_idx]
                gov_model.initialize(gen_model.pm)
                
        # Build state map for packing/unpacking
        self._build_state_map()
        return True

    def _build_state_map(self):
        """Build flat state vector map."""
        self.state_map = []
        # Generators
        for idx, model in sorted(self.generators.items()):
            for name in sorted(model.states.keys()):
                self.state_map.append((model, name))
        # Exciters
        for idx, model in sorted(self.exciters.items()):
            for name in sorted(model.states.keys()):
                self.state_map.append((model, name))
        # Governors
        for idx, model in sorted(self.governors.items()):
            for name in sorted(model.states.keys()):
                self.state_map.append((model, name))

    def get_state_vector(self):
        """Returns the flat 1D numpy array of all system states."""
        return np.array([model.states[name] for model, name in self.state_map])

    def set_state_vector(self, x):
        """Unpacks the flat 1D state vector back to individual models."""
        for i, (model, name) in enumerate(self.state_map):
            model.states[name] = x[i]

    def get_internal_emf_and_admittance(self, gen_idx):
        """
        Returns the internal EMF complex value (p.u. on network base) and 
        the source admittance (p.u. on system base) for a generator.
        """
        gen_model = self.generators[gen_idx]
        mbase = gen_model.mbase
        
        # Determine internal voltage and source impedance on machine base
        if isinstance(gen_model, GENCLS):
            delta = gen_model.states['delta']
            E_int_mac = gen_model.eq_prime * np.exp(1j * delta)
            Z_g_mac = gen_model.Ra + 1j * gen_model.Xd_prime
        elif isinstance(gen_model, GENSAL):
            delta = gen_model.states['delta']
            eq_dprime = gen_model.states['eq_dprime']
            ed_dprime = gen_model.states['ed_dprime']
            E_int_mac = (ed_dprime + 1j * eq_dprime) * np.exp(1j * (delta - np.pi/2))
            Z_g_mac = gen_model.Ra + 1j * gen_model.Xd_dprime
        else:
            # Fallback
            E_int_mac = 1.0 + 0j
            Z_g_mac = 0.0 + 0.1j
            
        # Convert impedance to system base
        Z_g_sys = Z_g_mac * (100.0 / mbase)
        y_g_sys = 1.0 / Z_g_sys
        return E_int_mac, y_g_sys

    def update_inputs_from_controllers(self):
        """Updates generator inputs (efd and pm) from exciter and governor states."""
        for gen_idx, gen_model in self.generators.items():
            if gen_idx in self.exciters:
                gen_model.efd = self.exciters[gen_idx].get_efd()
            if gen_idx in self.governors:
                gen_model.pm = self.governors[gen_idx].get_pm()

    def get_derivatives(self, V_net):
        """
        Returns the flat 1D numpy array of all state derivatives.
        V_net: terminal voltages at all buses (network base)
        """
        # First, ensure generator models have updated inputs from exciters and governors
        self.update_inputs_from_controllers()
        
        # Compute derivatives for all models
        for gen_idx, gen_model in self.generators.items():
            bus_idx = gen_model.bus_id
            Vt = V_net[bus_idx]
            
            # Generator derivatives
            gen_model.derivatives(Vt)
            
            # Exciter derivatives
            if gen_idx in self.exciters:
                self.exciters[gen_idx].derivatives(Vt, gen_model.efd)
                
            # Governor derivatives (needs generator speed deviation omega + 1.0)
            if gen_idx in self.governors:
                w_current = 1.0 + gen_model.states['omega']
                self.governors[gen_idx].derivatives(w_current)
                
        # Pack derivatives into a flat array matching state_map
        derivs = []
        for model, name in self.state_map:
            derivs.append(model.get_derivatives()[name])
        return np.array(derivs)


def run_simulation(power_case, dyr_records, fault_bus, fault_time, clear_time, 
                   t_end=5.0, dt=0.005, trip_branch=None, verbose=True):
    """
    Runs the transient stability simulation.
    
    fault_bus: external bus number where fault is applied.
    trip_branch: optional tuple (f_bus, t_bus) of the branch to trip upon fault clearing.
    """
    # 1. Ensure internal representation
    power_case.to_internal()
    
    # 2. Parse and map dynamic models
    dyn_case = DynamicCase()
    
    # Group dyr records by bus and gen_id
    grouped_records = {}
    for r in dyr_records:
        bus_id = r['bus_id']
        gen_id = r['gen_id']
        key = (bus_id, gen_id)
        if key not in grouped_records:
            grouped_records[key] = []
        grouped_records[key].append(r)
        
    # Map to PowerCase generators
    # Map by bus number (and order if multiple gens are at the same bus)
    for (ext_bus_id, gen_id), records in grouped_records.items():
        bus_idx = power_case.get_internal_bus_idx(ext_bus_id)
        if bus_idx is None:
            if verbose:
                print(f"Warning: Bus {ext_bus_id} from dyr file not found in power case.")
            continue
            
        # Find generators at this bus
        gen_indices = np.where(power_case.gen[:, GEN_BUS] == bus_idx)[0]
        if len(gen_indices) == 0:
            if verbose:
                print(f"Warning: No generators found at bus {ext_bus_id}.")
            continue
            
        # Match by ordering for simplicity or machine ID
        # Here we match the first parsed record set to the first generator, etc.
        # Find which generator index matches this gen_id
        # For simplicity, map to the first generator at the bus
        gen_idx = gen_indices[0]
        
        # Instantiate models
        for r in records:
            model_name = r['model_name']
            params = r['params']
            
            if model_name in MODEL_REGISTRY:
                model_cls = MODEL_REGISTRY[model_name]
                instance = model_cls(bus_idx, gen_id, params)
                
                if issubclass(model_cls, GeneratorModel):
                    dyn_case.generators[gen_idx] = instance
                elif issubclass(model_cls, ExciterModel):
                    dyn_case.exciters[gen_idx] = instance
                elif issubclass(model_cls, GovernorModel):
                    dyn_case.governors[gen_idx] = instance
            else:
                if verbose:
                    print(f"Warning: Model {model_name} is not implemented or registered.")

    if not dyn_case.generators:
        raise ValueError("No generators mapped from .dyr records to network case.")
        
    # 3. Solve power flow to get initial voltage profile
    from power_python.solvers.runpf import run_power_flow
    power_case, success = run_power_flow(power_case, verbose=False)
    if not success:
        raise ValueError("Initial power flow failed to converge. Cannot start dynamic simulation.")
        
    # Initialize state variables
    success = dyn_case.initialize_states(power_case)
    if not success:
        raise ValueError("Failed to initialize dynamic state variables.")

    # 4. Build augmented admittance matrices
    nb = len(power_case.bus)
    base_Ybus, _, _ = make_ybus(power_case.baseMVA, power_case.bus, power_case.branch)
    
    # Calculate load shunts at t=0
    load_shunts = np.zeros(nb, dtype=complex)
    vm_base = power_case.bus[:, VM]
    va_base = power_case.bus[:, VA]
    V_base = vm_base * np.exp(1j * np.pi / 180.0 * va_base)
    
    for i in range(nb):
        Pd_pu = power_case.bus[i, PD] / power_case.baseMVA
        Qd_pu = power_case.bus[i, QD] / power_case.baseMVA
        v_mag = np.abs(V_base[i])
        if v_mag > 1e-4 and (Pd_pu != 0.0 or Qd_pu != 0.0):
            # y = (P - jQ) / V^2
            load_shunts[i] = (Pd_pu - 1j * Qd_pu) / (v_mag**2)

    # Augmented Ybus matrix helper
    def build_augmented_ybus(base_y):
        y_aug = base_y.copy().tolil()
        # Add load shunts
        for idx in range(nb):
            if load_shunts[idx] != 0.0:
                y_aug[idx, idx] += load_shunts[idx]
        # Add generator internal admittances
        for g_idx in dyn_case.generators:
            bus_idx = int(power_case.gen[g_idx, GEN_BUS])
            _, y_g = dyn_case.get_internal_emf_and_admittance(g_idx)
            y_aug[bus_idx, bus_idx] += y_g
        return y_aug.tocsr()

    # Prefault Ybus
    Ybus_prefault = build_augmented_ybus(base_Ybus)
    
    # Fault Ybus
    # Map external fault bus number to internal index
    fault_bus_idx = power_case.get_internal_bus_idx(fault_bus)
    if fault_bus_idx is None:
        raise ValueError(f"Fault bus {fault_bus} not found in the network.")
        
    Ybus_fault = Ybus_prefault.copy().tolil()
    Ybus_fault[fault_bus_idx, fault_bus_idx] += 1e9  # Add short circuit path
    Ybus_fault = Ybus_fault.tocsr()
    
    # Postfault Ybus
    if trip_branch is not None:
        # Re-build Ybus with designated line removed
        f_ext, t_ext = trip_branch
        f_int = power_case.get_internal_bus_idx(f_ext)
        t_int = power_case.get_internal_bus_idx(t_ext)
        
        # Find branch index
        branch_idx = -1
        for idx in range(len(power_case.branch)):
            if ((int(power_case.branch[idx, F_BUS]) == f_int and int(power_case.branch[idx, T_BUS]) == t_int) or 
                (int(power_case.branch[idx, F_BUS]) == t_int and int(power_case.branch[idx, T_BUS]) == f_int)):
                branch_idx = idx
                break
                
        if branch_idx >= 0:
            # Save status and trip the branch
            orig_status = power_case.branch[branch_idx, BR_STATUS]
            power_case.branch[branch_idx, BR_STATUS] = 0
            
            # Re-generate network base Ybus
            base_Ybus_post, _, _ = make_ybus(power_case.baseMVA, power_case.bus, power_case.branch)
            Ybus_postfault = build_augmented_ybus(base_Ybus_post)
            
            # Restore branch status
            power_case.branch[branch_idx, BR_STATUS] = orig_status
        else:
            if verbose:
                print(f"Warning: Branch between {f_ext} and {t_ext} not found. Using pre-fault network.")
            Ybus_postfault = Ybus_prefault.copy()
    else:
        Ybus_postfault = Ybus_prefault.copy()

    # Network solver helper
    def solve_network(t, E_int_dict):
        # Determine which Ybus to use
        if t >= fault_time and t < clear_time:
            Y = Ybus_fault
        elif t >= clear_time:
            Y = Ybus_postfault
        else:
            Y = Ybus_prefault
            
        # Calculate Norton equivalent current injections
        I_inj = np.zeros(nb, dtype=complex)
        for g_idx, E_int in E_int_dict.items():
            bus_idx = int(power_case.gen[g_idx, GEN_BUS])
            _, y_g = dyn_case.get_internal_emf_and_admittance(g_idx)
            I_inj[bus_idx] += y_g * E_int
            
        # Solve Y * V = I_inj
        return spsolve(Y, I_inj)

    # 5. Simulation Time Loop (Modified Euler Integration)
    steps = int(t_end / dt)
    time = np.zeros(steps)
    
    # Track states, angles, and terminal voltages over time
    history = {
        'time': time,
        'bus_voltages': np.zeros((steps, nb), dtype=complex),
        'rotor_angles': {g_idx: np.zeros(steps) for g_idx in dyn_case.generators},
        'speeds': {g_idx: np.zeros(steps) for g_idx in dyn_case.generators},
        'pm': {g_idx: np.zeros(steps) for g_idx in dyn_case.generators},
        'efd': {g_idx: np.zeros(steps) for g_idx in dyn_case.generators}
    }
    
    # Initialize voltage profile
    E_int_dict = {}
    for g_idx in dyn_case.generators:
        E_int_dict[g_idx], _ = dyn_case.get_internal_emf_and_admittance(g_idx)
    V_net = solve_network(0.0, E_int_dict)
    
    if verbose:
        print(f"Starting dynamic simulation: t_end={t_end}s, dt={dt}s")
        print(f"Fault applied at t={fault_time}s on bus {fault_bus}, cleared at t={clear_time}s")
        if trip_branch:
            print(f"Trip branch: {trip_branch[0]} - {trip_branch[1]}")
            
    for step in range(steps):
        t = step * dt
        time[step] = t
        
        # Solve network voltages given current internal states
        E_int_dict = {}
        for g_idx in dyn_case.generators:
            E_int_dict[g_idx], _ = dyn_case.get_internal_emf_and_admittance(g_idx)
        V_net = solve_network(t, E_int_dict)
        
        # Log history
        history['bus_voltages'][step, :] = V_net
        for g_idx, gen_model in dyn_case.generators.items():
            history['rotor_angles'][g_idx][step] = gen_model.states['delta']
            history['speeds'][g_idx][step] = gen_model.states['omega']
            history['pm'][g_idx][step] = gen_model.pm
            history['efd'][g_idx][step] = gen_model.efd
            
        # --- Integration Step: Modified Euler ---
        # Get current states
        x_t = dyn_case.get_state_vector()
        
        # 1. Predictor step
        dxdt_t = dyn_case.get_derivatives(V_net)
        x_pred = x_t + dt * dxdt_t
        
        # Apply predicted states to models to solve network equations
        dyn_case.set_state_vector(x_pred)
        E_int_dict_pred = {}
        for g_idx in dyn_case.generators:
            E_int_dict_pred[g_idx], _ = dyn_case.get_internal_emf_and_admittance(g_idx)
        V_net_pred = solve_network(t + dt, E_int_dict_pred)
        
        # 2. Corrector step
        dxdt_pred = dyn_case.get_derivatives(V_net_pred)
        
        # Update states
        x_new = x_t + 0.5 * dt * (dxdt_t + dxdt_pred)
        dyn_case.set_state_vector(x_new)

    if verbose:
        print("Dynamic simulation completed successfully.\n")
        
    return history
