# MATPOWER (MATLAB) vs. PowerPython Feature Comparison

This document details the architectural and functional differences between **MATPOWER MATLAB (latest version 8.1)** and the **PowerPython (`power_python`)** codebase. It outlines a roadmap for how PowerPython can achieve parity and act as a functional superset.

---

## 1. Core Architecture Comparison

| Feature / Aspect | MATPOWER (MATLAB v8.1) | PowerPython (`power_python`) |
| :--- | :--- | :--- |
| **Language** | MATLAB / Octave | Python (v3.11+) |
| **Core Structure** | Mixed: Functional (Legacy structs `mpc`) & Object-Oriented (MATPOWER Object Model - MPOM) | Functional-Object hybrid (`PowerCase` wrapping NumPy arrays) |
| **Data Storage** | Dense double-precision matrices, cell arrays | NumPy `ndarray` arrays, Pandas DataFrames for contingency reports |
| **Admittance Matrix** | Sparse MATLAB matrices | SciPy `csr_matrix` sparse matrix |
| **Optimization Backend** | MIPS (built-in solver), IPOPT, fmincon, Gurobi, CPLEX | CVXPY (Clarabel, OSQP, HiGHS, etc.) |

---

## 2. Solver Capability Matrix

| Power System Tool | MATPOWER (MATLAB v8.1) | PowerPython (`power_python`) | Parity Status / Action |
| :--- | :--- | :--- | :--- |
| **Newton-Raphson AC Power Flow (ACPF)** | Yes (`newtonpf`) | Yes (`newtonpf` / `runpf`) | **Full Parity** |
| **Fast Decoupled Power Flow (FDPF)** | Yes (`fdpf`) | No | Add decoupled solver (XB/BX versions) |
| **Gauss-Seidel Power Flow (GSPF)** | Yes (`gausspf`) | No | Add Gauss-Seidel solver for legacy systems |
| **Optimal Power Flow (DC-OPF)** | Yes (`dcopf`) | Yes (`dcopf`) | **Full Parity** (PowerPython uses modern CVXPY) |
| **Optimal Power Flow (AC-OPF)** | Yes (`acopf` via NLP solvers) | No | Add AC-OPF solver using non-convex solvers |
| **Sensitivity Analysis** | Yes (PTDF, LODF) | Yes (`sensitivity`) | **Full Parity** |
| **Contingency Analysis** | Yes (often custom or MOST-based) | Yes (`contingency` with Pandas outputs) | **Exceeds MATPOWER** in native Python integration |
| **Security-Constrained OPF** | Yes (via MOST) | Yes (`sc_opf` with N-1 contingency) | **Full Parity** |

---

## 3. Road Map to Becoming a Superset of MATPOWER

To make PowerPython a true functional superset of MATPOWER, we will add advanced features that are either absent or difficult to execute in MATPOWER MATLAB:

### 3.1. Holomorphic Embedding Load Flow (HELM / HEM)
*   **What it is:** A non-iterative power flow technique that uses analytic continuation of complex functions to solve the algebraic power flow equations.
*   **Why it's a superset feature:** Unlike the Newton-Raphson method (which is highly sensitive to the initial guess and may fail to converge or diverge to a non-physical solution), HELM is guaranteed to find the true, high-voltage stable operating point if one exists. If no solution exists, the mathematical poles of the method will signal this unambiguously.
*   **Implementation Plan:**
    1.  Implement a recurrence relation solver to compute the Maclaurin series coefficients of voltage and power.
    2.  Use Padé Approximants to evaluate the series at the physical boundary ($s=1$).
    3.  Develop a new solver entry point: `power_python.solvers.helmpf`.

### 3.2. Modern Pythonic Export and Integration
*   Integrate directly with modern data frames, Parquet/feather files, and ML frameworks (PyTorch/TensorFlow) for Deep Learning-based OPF models.
