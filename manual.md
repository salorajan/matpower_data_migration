# PowerPython Manual

PowerPython is a high-performance power system modeling and simulation package written in Python. It is designed to be a modern alternative to MATPOWER, leveraging the efficiency of NumPy and the optimization capabilities of CVXPY.

## Table of Contents
1. [Installation](#installation)
2. [Core Features](#core-features)
3. [Directory Structure](#directory-structure)
4. [Usage Examples](#usage-examples)
5. [Running Tests](#running-tests)
6. [Constants & Data Format](#constants--data-format)

---

## Installation

Ensure you have a Python environment (v3.11+ recommended) and install the dependencies:

```bash
pip install numpy pandas cvxpy scipy
```

If you are using the provided virtual environment:
```powershell
.\power_env\Scripts\activate
```

---

## Core Features

### 1. AC Power Flow (ACPF)
Solves the non-linear power flow equations using the Newton-Raphson method.
- **Solver:** `power_python.solvers.runpf`
- **Engine:** `newtonpf`

### 2. DC Optimal Power Flow (DC-OPF)
Solves the linear DC approximation of the Optimal Power Flow problem to minimize generation costs.
- **Solver:** `power_python.solvers.dcopf`
- **Optimizer:** CVXPY (supports various backends like OSQP, Clarabel)

### 3. Sensitivity Factors
Calculates Power Transfer Distribution Factors (PTDF) and Line Outage Distribution Factors (LODF).
- **Module:** `power_python.network.sensitivity`

### 4. N-1 Contingency Analysis
Evaluates the system state for every single line outage scenario using DC approximations and LODFs to detect thermal violations.
- **Solver:** `power_python.solvers.contingency`

### 5. Security-Constrained OPF (SC-OPF)
Solves a DC-OPF that ensures system stability even under any single N-1 contingency.
- **Solver:** `power_python.solvers.sc_opf`

---

## Directory Structure

- `core/`: Data structures (`PowerCase`) and physical constants.
- `network/`: Admittance matrix (Ybus), Sensitivity factors, and flow calculations.
- `solvers/`: Power flow and optimization algorithms.
- `utils/`: Data converters and reporting tools.
- `tests/`: Unit tests and verification scripts.

---

## Usage Examples

### Running a basic AC Power Flow
```python
from power_python.core.case import PowerCase
from power_python.solvers.runpf import run_power_flow

# Load a case
case = PowerCase()
case.load_from_json("outputs/json/case9.json")

# Run solver
updated_case, converged = run_power_flow(case)

if converged:
    print("Power flow converged!")
```

### Running DC-OPF
```python
from power_python.solvers.dcopf import run_dc_opf

updated_case, success = run_dc_opf(case)
if success:
    print(f"Optimal Cost: {updated_case.total_cost}")
```

### Contingency Analysis
```python
from power_python.solvers.contingency import run_contingency_analysis

violations_df = run_contingency_analysis(case)
print(violations_df)
```

---

## Running Tests

The package includes a comprehensive suite of tests to verify accuracy against standard MATPOWER benchmarks.

**Run Case 6 Wood & Wollenberg Verification:**
```powershell
python .\power_python\tests\test_case6ww.py
```

**Run Y-Bus Verification:**
```powershell
python .\project\ybus_verification.py
```

**Run All Unit Tests:**
```powershell
# In the project directory
python -m unittest discover power_python/tests
```

---

## Constants & Data Format

PowerPython uses standard MATPOWER indexing. To access data, always use the provided constants:

```python
from power_python.core.constants import *

# Access bus voltage of the first bus
voltage = case.bus[0, VM]

# Access real power generation
pg = case.gen[:, PG]
```

*Note: All angles are handled in Radians internally and converted to Degrees for external case data.*
