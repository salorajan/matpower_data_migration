# PowerPython Dynamics
# Copyright (c) 2026 PowerPython contributors
# Licensed under the 3-clause BSD License (see LICENSE file for details).

"""
Dynamic models for generators, exciters, and governors.
Implements clean-room mathematical block diagrams matching standard PSS/E models.
"""

import numpy as np

# Registry mapping model names to class types
MODEL_REGISTRY = {}

def register_model(cls):
    MODEL_REGISTRY[cls.__name__.upper()] = cls
    return cls

class DynamicModel:
    """Base class for all dynamic simulation components."""
    def __init__(self, bus_id, gen_id, params):
        self.bus_id = int(bus_id)
        self.gen_id = str(gen_id)
        self.params = [float(p) for p in params]
        self.states = {}
        self.derivatives_dict = {}

    def get_states(self):
        return self.states

    def set_states(self, state_values):
        for name, val in state_values.items():
            if name in self.states:
                self.states[name] = val

    def get_derivatives(self):
        return self.derivatives_dict


class GeneratorModel(DynamicModel):
    """Base class for generator models."""
    def __init__(self, bus_id, gen_id, params):
        super().__init__(bus_id, gen_id, params)
        self.mbase = 100.0  # Default machine MVA base
        self.pm = 0.0       # Mechanical power input (p.u. on machine base)
        self.efd = 1.0      # Excitation voltage input (p.u.)
        
    def initialize(self, Vt, S_inj, baseMVA, mbase):
        """
        Initialize generator state variables from power flow results.
        Vt: terminal voltage complex number (p.u.)
        S_inj: complex power injection (MW + jMVAR) from power flow
        baseMVA: system MVA base
        mbase: machine MVA base
        """
        raise NotImplementedError

    def derivatives(self, Vt):
        """Calculate derivatives of state variables."""
        raise NotImplementedError

    def algebraic_current(self, Vt):
        """Return the complex current injection (p.u. on system base)."""
        raise NotImplementedError


class ExciterModel(DynamicModel):
    """Base class for excitation system models."""
    def __init__(self, bus_id, gen_id, params):
        super().__init__(bus_id, gen_id, params)
        self.vref = 1.0
        
    def initialize(self, Vt, efd_init):
        """Initialize exciter state variables."""
        raise NotImplementedError

    def derivatives(self, Vt, efd):
        """Calculate derivatives of state variables."""
        raise NotImplementedError

    def get_efd(self):
        """Return the current field voltage output."""
        raise NotImplementedError


class GovernorModel(DynamicModel):
    """Base class for turbine-governor models."""
    def __init__(self, bus_id, gen_id, params):
        super().__init__(bus_id, gen_id, params)
        self.pref = 1.0
        self.w = 1.0 # Current speed in p.u.
        
    def initialize(self, pm_init):
        """Initialize governor state variables."""
        raise NotImplementedError

    def derivatives(self, w):
        """Calculate derivatives of state variables."""
        raise NotImplementedError

    def get_pm(self):
        """Return the current mechanical power output."""
        raise NotImplementedError


# ==============================================================================
# Generator Models
# ==============================================================================

@register_model
class GENCLS(GeneratorModel):
    """
    PSS/E Classical Generator Model.
    Parameters in order: H, D, Ra, Xd_prime
    """
    def __init__(self, bus_id, gen_id, params):
        super().__init__(bus_id, gen_id, params)
        # Parameters
        self.H = self.params[0]
        self.D = self.params[1]
        self.Ra = self.params[2]
        self.Xd_prime = self.params[3]
        
        # State variables
        self.states = {
            'delta': 0.0,
            'omega': 0.0
        }
        self.eq_prime = 1.0 # Internal constant voltage magnitude

    def initialize(self, Vt, S_inj, baseMVA, mbase):
        self.mbase = mbase
        # Convert S_inj to p.u. on machine base
        S_mac = (S_inj / baseMVA) * (baseMVA / mbase)
        # Terminal current in machine base
        It = np.conj(S_mac / Vt)
        
        # E' = Vt + (Ra + j*Xd_prime) * It
        Z_source = self.Ra + 1j * self.Xd_prime
        E = Vt + Z_source * It
        
        self.states['delta'] = np.angle(E)
        self.states['omega'] = 0.0 # Speed deviation is 0 at steady-state
        
        self.eq_prime = np.abs(E)
        self.pm = np.real(E * np.conj(It)) # Mechanical power matches electrical power
        self.efd = self.eq_prime # Excitation field voltage
        return True

    def derivatives(self, Vt):
        delta = self.states['delta']
        omega = self.states['omega']
        
        # Internal voltage E = eq_prime * exp(j * delta)
        E = self.eq_prime * np.exp(1j * delta)
        
        # Calculate current injection into terminal Vt in machine p.u.
        Z_source = self.Ra + 1j * self.Xd_prime
        It = (E - Vt) / Z_source
        
        # Electrical power output (p.u. on machine base)
        pe = np.real(Vt * np.conj(It))
        
        # Swing equations
        # d(delta)/dt = 2 * pi * f0 * omega_deviation
        # where omega is speed deviation in p.u. f0 = 60 Hz.
        f0 = 60.0
        omega_base = 2 * np.pi * f0
        
        ddelta = omega_base * omega
        domega = (self.pm - pe - self.D * omega) / (2.0 * self.H)
        
        self.derivatives_dict = {
            'delta': ddelta,
            'omega': domega
        }
        return self.derivatives_dict

    def algebraic_current(self, Vt):
        delta = self.states['delta']
        E = self.eq_prime * np.exp(1j * delta)
        Z_source = self.Ra + 1j * self.Xd_prime
        It_mac = (E - Vt) / Z_source
        # Convert current to system MVA base
        It_sys = It_mac * (self.mbase / 100.0)
        return It_sys


@register_model
class GENSAL(GeneratorModel):
    """
    PSS/E Salient Pole Generator Model.
    Parameters in order: H, D, Td0_prime, Td0_dprime, Tq0_dprime, Xd, Xq, Xd_prime, Xd_dprime, Xl, S10, S12
    Note: For simplicity, we implement the standard transient/subtransient model equations.
    """
    def __init__(self, bus_id, gen_id, params):
        super().__init__(bus_id, gen_id, params)
        self.H = self.params[0]
        self.D = self.params[1]
        self.Td0_prime = self.params[2]
        self.Td0_dprime = self.params[3]
        self.Tq0_dprime = self.params[4]
        self.Xd = self.params[5]
        self.Xq = self.params[6]
        self.Xd_prime = self.params[7]
        self.Xd_dprime = self.params[8]
        self.Xq_dprime = self.params[8] # Often Xq_dprime = Xd_dprime in GENSAL
        self.Xl = self.params[9]
        self.Ra = 0.0 # Assumed stator resistance is small/zero in standard GENSAL
        
        self.states = {
            'delta': 0.0,
            'omega': 0.0,
            'eq_prime': 0.0,
            'eq_dprime': 0.0,
            'ed_dprime': 0.0
        }

    def initialize(self, Vt, S_inj, baseMVA, mbase):
        self.mbase = mbase
        # Convert S_inj to p.u. on machine base
        S_mac = (S_inj / baseMVA) * (baseMVA / mbase)
        It = np.conj(S_mac / Vt)
        
        # Calculate rotor angle delta from generator internal equations
        # Eq_voltage = Vt + (Ra + j*Xq) * It
        Eq = Vt + (self.Ra + 1j * self.Xq) * It
        delta = np.angle(Eq)
        self.states['delta'] = delta
        self.states['omega'] = 0.0
        
        # Transform Vt and It to dq reference frame
        # Vt = Vt_d + j*Vt_q relative to e^(j*delta)
        # V_dq = Vt * e^(-j*(delta - pi/2))
        V_dq = Vt * np.exp(-1j * (delta - np.pi/2))
        vd = V_dq.real
        vq = V_dq.imag
        
        I_dq = It * np.exp(-1j * (delta - np.pi/2))
        id_ = I_dq.real
        iq = I_dq.imag
        
        # Initialize internal state EMFs
        # eq_prime = vq + Ra*iq + id_*(Xd - Xd_prime)
        eq_prime = vq + self.Ra * iq + id_ * (self.Xd - self.Xd_prime)
        self.states['eq_prime'] = eq_prime
        
        # eq_dprime = vq + Ra*iq + id_*(Xd_prime - Xd_dprime)
        eq_dprime = vq + self.Ra * iq + id_ * (self.Xd_prime - self.Xd_dprime)
        self.states['eq_dprime'] = eq_dprime
        
        # ed_dprime = vd + Ra*id_ - iq*(Xq - Xd_dprime)
        ed_dprime = vd + self.Ra * id_ - iq * (self.Xq - self.Xd_dprime)
        self.states['ed_dprime'] = ed_dprime
        
        # Initial mechanical power & excitation voltage
        self.efd = eq_prime + id_ * (self.Xd - self.Xd_prime)
        self.pm = vq * iq + vd * id_ + self.Ra * (id_**2 + iq**2)
        return True

    def derivatives(self, Vt):
        delta = self.states['delta']
        omega = self.states['omega']
        eq_prime = self.states['eq_prime']
        eq_dprime = self.states['eq_dprime']
        ed_dprime = self.states['ed_dprime']
        
        # Project Vt to dq frame
        V_dq = Vt * np.exp(-1j * (delta - np.pi/2))
        vd = V_dq.real
        vq = V_dq.imag
        
        # Solve stator algebraic currents in dq frame
        # eq_dprime - vq = Ra * iq + Xd_dprime * id_
        # ed_dprime - vd = Ra * id_ - Xd_dprime * iq
        # Represented as linear system:
        # [  Ra           Xd_dprime ] [ iq ]   [ eq_dprime - vq ]
        # [ -Xd_dprime    Ra        ] [ id_ ] = [ ed_dprime - vd ]
        A = np.array([
            [self.Ra, self.Xd_dprime],
            [-self.Xd_dprime, self.Ra]
        ])
        b = np.array([eq_dprime - vq, ed_dprime - vd])
        currents = np.linalg.solve(A, b)
        iq = currents[0]
        id_ = currents[1]
        
        # Electrical power output
        pe = vq * iq + vd * id_ + self.Ra * (id_**2 + iq**2)
        
        f0 = 60.0
        omega_base = 2 * np.pi * f0
        
        # State derivatives
        ddelta = omega_base * omega
        domega = (self.pm - pe - self.D * omega) / (2.0 * self.H)
        
        deq_prime = (self.efd - eq_prime - id_ * (self.Xd - self.Xd_prime)) / self.Td0_prime
        deq_dprime = (eq_prime - eq_dprime - id_ * (self.Xd_prime - self.Xd_dprime)) / self.Td0_dprime
        ded_dprime = (-ed_dprime + iq * (self.Xq - self.Xd_dprime)) / self.Tq0_dprime
        
        self.derivatives_dict = {
            'delta': ddelta,
            'omega': domega,
            'eq_prime': deq_prime,
            'eq_dprime': deq_dprime,
            'ed_dprime': ded_dprime
        }
        return self.derivatives_dict

    def algebraic_current(self, Vt):
        delta = self.states['delta']
        eq_dprime = self.states['eq_dprime']
        ed_dprime = self.states['ed_dprime']
        
        # Project Vt to dq frame
        V_dq = Vt * np.exp(-1j * (delta - np.pi/2))
        vd = V_dq.real
        vq = V_dq.imag
        
        A = np.array([
            [self.Ra, self.Xd_dprime],
            [-self.Xd_dprime, self.Ra]
        ])
        b = np.array([eq_dprime - vq, ed_dprime - vd])
        currents = np.linalg.solve(A, b)
        iq = currents[0]
        id_ = currents[1]
        
        # Transform back to network frame
        It_dq = id_ + 1j * iq
        It_net = It_dq * np.exp(1j * (delta - np.pi/2))
        
        # Convert to system base
        return It_net * (self.mbase / 100.0)


# ==============================================================================
# Excitation System Models
# ==============================================================================

@register_model
class SEXS(ExciterModel):
    """
    PSS/E Simplified Excitation System.
    Parameters in order: TA_over_TB, TB, K, TE, Emin, Emax
    """
    def __init__(self, bus_id, gen_id, params):
        super().__init__(bus_id, gen_id, params)
        self.TA_TB = self.params[0]
        self.TB = self.params[1]
        self.K = self.params[2]
        self.TE = self.params[3]
        self.Emin = self.params[4]
        self.Emax = self.params[5]
        
        self.states = {
            'x1': 0.0, # Lead-lag state variable
            'efd': 0.0 # Exciter integrator state variable
        }

    def initialize(self, Vt, efd_init):
        # efd = efd_init
        # In steady state: Input to exciter integrator = output = efd_init
        # Gain K scales the difference.
        # Input to Lead-Lag block = efd_init / K.
        # Since Lead-Lag has unity steady-state gain, input to Lead-Lag block is V_err = Vref - Vt = efd_init / K
        # Therefore, Vref = Vt + efd_init / K.
        Vt_mag = np.abs(Vt)
        self.vref = Vt_mag + efd_init / self.K
        
        # State variables
        self.states['efd'] = efd_init
        # Lead-lag block transfer function is (1 + s*TA)/(1 + s*TB).
        # At steady-state, x1 = (1 - TA/TB) * V_err
        # if TB == 0, lead-lag is bypassed.
        if self.TB > 1e-4:
            v_err = self.vref - Vt_mag
            self.states['x1'] = (1.0 - self.TA_TB) * v_err
        else:
            self.states['x1'] = 0.0
            
        return True

    def derivatives(self, Vt, efd):
        Vt_mag = np.abs(Vt)
        v_err = self.vref - Vt_mag
        
        if self.TB > 1e-4:
            # Lead-lag input/output:
            # dx1/dt = (v_err - x1) / TB
            # out = x1 + (TA/TB)*v_err = x1 + TA_TB * v_err
            dx1 = (v_err - self.states['x1']) / self.TB
            ll_out = self.states['x1'] + self.TA_TB * v_err
        else:
            dx1 = 0.0
            ll_out = v_err
            
        # Exciter block:
        # dx2/dt = (K * ll_out - efd) / TE
        # with output efd limited to [Emin, Emax]
        efd_current = self.states['efd']
        input_signal = self.K * ll_out
        defd = (input_signal - efd_current) / self.TE
        
        # Limit handling (non-windup limit)
        if efd_current >= self.Emax and defd > 0:
            defd = 0.0
            self.states['efd'] = self.Emax
        elif efd_current <= self.Emin and defd < 0:
            defd = 0.0
            self.states['efd'] = self.Emin
            
        self.derivatives_dict = {
            'x1': dx1,
            'efd': defd
        }
        return self.derivatives_dict

    def get_efd(self):
        return np.clip(self.states['efd'], self.Emin, self.Emax)


# ==============================================================================
# Turbine-Governor Models
# ==============================================================================

@register_model
class TGOV1(GovernorModel):
    """
    PSS/E Simple Steam Turbine-Governor Model.
    Parameters in order: R, T1, Vmax, Vmin, T2, T3
    """
    def __init__(self, bus_id, gen_id, params):
        super().__init__(bus_id, gen_id, params)
        self.R = self.params[0]
        self.T1 = self.params[1]
        self.Vmax = self.params[2]
        self.Vmin = self.params[3]
        self.T2 = self.params[4]
        self.T3 = self.params[5]
        
        self.states = {
            'x1': 0.0, # Governor valve position state
            'pm': 0.0  # Turbine output power state
        }

    def initialize(self, pm_init):
        # In steady state, speed w is synchronous (deviation = 0).
        # Output mechanical power matches pm_init.
        # TGOV1 block transfer function: (1 + s*T2) / ( (1 + s*T1)*(1 + s*T3) )
        # Steady-state gain is 1.0.
        # Governor input = pref - w_deviation / R.
        # w_deviation = 0, so governor input = pref = pm_init.
        self.pref = pm_init
        self.states['x1'] = pm_init
        self.states['pm'] = pm_init
        return True

    def derivatives(self, w):
        # w is speed in p.u., speed deviation dw = w - 1.0
        dw = w - 1.0
        
        # Governor block input:
        input_gov = self.pref - dw / self.R
        
        # dx1/dt = (input_gov - x1) / T1
        # output is limited to [Vmin, Vmax]
        x1_current = self.states['x1']
        dx1 = (input_gov - x1_current) / self.T1
        
        # Limit handling (non-windup limits on valve position x1)
        if x1_current >= self.Vmax and dx1 > 0:
            dx1 = 0.0
            self.states['x1'] = self.Vmax
        elif x1_current <= self.Vmin and dx1 < 0:
            dx1 = 0.0
            self.states['x1'] = self.Vmin
            
        valve_pos = np.clip(x1_current, self.Vmin, self.Vmax)
        
        # Turbine lead-lag + lag block:
        # TGOV1 output equation:
        # d(pm)/dt = ( valve_pos + (T2/T1)*(input_gov - valve_pos) - pm ) / T3 ?
        # Standard formulation:
        # dx2/dt = (valve_pos - pm) / T3
        # If T2 > 0:
        # pm_out = T2/T3 * valve_pos + (1 - T2/T3) * x2
        # Let's use the standard formulation:
        # dx2/dt = (valve_pos - self.states['pm']) / self.T3 (if T2 == 0)
        # In general, Lead-Lag block:
        # dx2/dt = (valve_pos * (1 - T2/T3) - pm) / T3
        # Standard implementation of TGOV1:
        # dx2/dt = (valve_pos - self.states['pm']) / self.T3
        # and mechanical power is out = pm_state + T2/T3 * (valve_val - pm_state)
        # Wait, let's write it in standard state-space:
        # d(pm)/dt = (valve_pos - pm) / T3 if T2 == 0.
        # Let's do:
        pm_state = self.states['pm']
        dpm = (valve_pos - pm_state) / self.T3
        
        self.derivatives_dict = {
            'x1': dx1,
            'pm': dpm
        }
        return self.derivatives_dict

    def get_pm(self):
        pm_state = self.states['pm']
        valve_pos = np.clip(self.states['x1'], self.Vmin, self.Vmax)
        if self.T3 > 1e-4 and self.T2 > 1e-4:
            # Output power includes the transient lead term
            return pm_state + (self.T2 / self.T3) * (valve_pos - pm_state)
        return pm_state
