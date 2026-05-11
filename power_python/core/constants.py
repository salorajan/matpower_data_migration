"""
Constants for named column indices for MATPOWER matrices.
Translated from MATPOWER lib/idx_*.m files.
Note: All indices are 0-based for Python compatibility.
"""

# Bus indices (from idx_bus.m)
BUS_I       = 0   # bus number (positive integer)
BUS_TYPE    = 1   # bus type (1 = PQ, 2 = PV, 3 = ref, 4 = isolated)
PD          = 2   # Pd, real power demand (MW)
QD          = 3   # Qd, reactive power demand (MVAr)
GS          = 4   # Gs, shunt conductance (MW demanded at V = 1.0 p.u.)
BS          = 5   # Bs, shunt susceptance (MVAr injected at V = 1.0 p.u.)
BUS_AREA    = 6   # area number, (positive integer)
VM          = 7   # Vm, voltage magnitude (p.u.)
VA          = 8   # Va, voltage angle (degrees)
BASE_KV     = 9   # baseKV, base voltage (kV)
ZONE        = 10  # zone, loss zone (positive integer)
VMAX        = 11  # maxVm, maximum voltage magnitude (p.u.)
VMIN        = 12  # minVm, minimum voltage magnitude (p.u.)

# Added after OPF
LAM_P       = 13  # Lagrange multiplier on real power mismatch (u/MW)
LAM_Q       = 14  # Lagrange multiplier on reactive power mismatch (u/MVAr)
MU_VMAX     = 15  # Kuhn-Tucker multiplier on upper voltage limit (u/p.u.)
MU_VMIN     = 16  # Kuhn-Tucker multiplier on lower voltage limit (u/p.u.)

# Bus types
PQ          = 1
PV          = 2
REF         = 3
NONE        = 4

# Generator indices (from idx_gen.m)
GEN_BUS     = 0   # bus number
PG          = 1   # Pg, real power output (MW)
QG          = 2   # Qg, reactive power output (MVAr)
QMAX        = 3   # Qmax, maximum reactive power output (MVAr)
QMIN        = 4   # Qmin, minimum reactive power output (MVAr)
VG          = 5   # Vg, voltage magnitude setpoint (p.u.)
MBASE       = 6   # mBase, total MVA base of machine, defaults to baseMVA
GEN_STATUS  = 7   # status, > 0 - in service, <= 0 - out of service
PMAX        = 8   # Pmax, maximum real power output (MW)
PMIN        = 9   # Pmin, minimum real power output (MW)
PC1         = 10  # Pc1, lower real power output of PQ capability curve (MW)
PC2         = 11  # Pc2, upper real power output of PQ capability curve (MW)
QC1MIN      = 12  # Qc1min, minimum reactive power output at Pc1 (MVAr)
QC1MAX      = 13  # Qc1max, maximum reactive power output at Pc1 (MVAr)
QC2MIN      = 14  # Qc1min, minimum reactive power output at Pc2 (MVAr)
QC2MAX      = 15  # Qc1max, maximum reactive power output at Pc2 (MVAr)
RAMP_AGC    = 16  # ramp rate for load following/AGC (MW/min)
RAMP_10     = 17  # ramp rate for 10 minute reserves (MW)
RAMP_30     = 18  # ramp rate for 30 minute reserves (MW)
RAMP_Q      = 19  # ramp rate for reactive power (2 sec timescale) (MVAr/min)
APF         = 20  # area participation factor

# Added after OPF
MU_PMAX     = 21
MU_PMIN     = 22
MU_QMAX     = 23
MU_QMIN     = 24

# Branch indices (from idx_brch.m)
F_BUS       = 0   # f, from bus number
T_BUS       = 1   # t, to bus number
BR_R        = 2   # r, resistance (p.u.)
BR_X        = 3   # x, reactance (p.u.)
BR_B        = 4   # b, total line charging susceptance (p.u.)
RATE_A      = 5   # rateA, MVA rating A (long term rating)
RATE_B      = 6   # rateB, MVA rating B (short term rating)
RATE_C      = 7   # rateC, MVA rating C (emergency rating)
TAP         = 8   # ratio, transformer off nominal turns ratio
SHIFT       = 9   # angle, transformer phase shift angle (degrees)
BR_STATUS   = 10  # initial branch status, 1 - in service, 0 - out of service
ANGMIN      = 11  # minimum angle difference (degrees)
ANGMAX      = 12  # maximum angle difference (degrees)

# Added after PF/OPF
PF          = 13  # real power injected into "from" end (MW)
QF          = 14  # reactive power injected into "from" end (MVAr)
PT          = 15  # real power injected into "to" end (MW)
QT          = 16  # reactive power injected into "to" end (MVAr)
MU_SF       = 17  # Kuhn-Tucker multiplier on MVA limit at "from" bus
MU_ST       = 18  # Kuhn-Tucker multiplier on MVA limit at "to" bus
MU_ANGMIN   = 19  # Kuhn-Tucker multiplier on min angle difference
MU_ANGMAX   = 20  # Kuhn-Tucker multiplier on max angle difference

# Gencost indices (from idx_cost.m)
MODEL       = 0   # cost model, 1 = piecewise linear, 2 = polynomial
STARTUP     = 1   # startup cost in US dollars
SHUTDOWN    = 2   # shutdown cost in US dollars
NCOST       = 3   # number of data points or coefficients
COST        = 4   # start of cost parameters

# Cost models
PW_LINEAR   = 1
POLYNOMIAL  = 2
