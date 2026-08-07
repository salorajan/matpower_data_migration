# PowerPython User Manual

PowerPython is a high-performance power system modeling and simulation package written in Python, serving as a functional superset of MATPOWER (MATLAB).

---

## 1.0 Architecture Overview

PowerPython is designed for dual-mode flexibility:
1. **Command-Line Interface (CLI) Mode**: Direct terminal commands for running 23 different power system analyses, specifying accuracies, and exporting reports to Excel, CSV, or Word (DOCX).
2. **Normal Python Scripting Mode**: Importing `power_python` as a standard module to load files, access constants, and build custom simulation pipelines.

---

## 2.0 Command-Line Interface (CLI) Mode

When you install PowerPython in editable mode (`pip install -e .`), 23 specialized commands are registered to your shell environment.

### 2.1 General CLI Usage
The syntax for executing any analysis is:
```bash
<analysis_command> <case_id> [accuracy] [export_format]
```
- **`<analysis_command>`**: The specific tool (e.g., `acpf`, `hepf`, `dcopf`, `se`, `radial`, `pf3p`).
- **`<case_id>`**: The name or number of the IEEE test case (e.g., `case9`, `case14`, `case3p_a`, `case300`).
- **`[accuracy]`**: Optional convergence tolerance float (e.g. `1e-5`, `1e-8`). Defaults to `1e-8`.
- **`[export_format]`**: Optional export type. Supported:
  - `excel` / `xlsx`: Exports results to a multi-sheet spreadsheet (e.g., `acpf_case14.xlsx`).
  - `csv`: Exports three raw text tables (e.g., `acpf_case14_bus.csv`, `acpf_case14_gen.csv`, `acpf_case14_branch.csv`).
  - `docx` / `word`: Generates a premium Word report document containing simulation metadata, key performance metrics, and formatted data tables (e.g., `acpf_case14.docx`).

### 2.2 CLI Examples
* **AC Power Flow on Case 14 at 1e-4 accuracy exported to Excel:**
  ```bash
  acpf case14 1e-4 excel
  ```
  *Output File:* `acpf_case14.xlsx`

* **Holomorphic Embedding on Case 9 exported to a Word Report:**
  ```bash
  hepf case9 docx
  ```
  *Output File:* `hepf_case9.docx`

* **Unbalanced 3-Phase Power Flow on Case 3P_A exported to CSV:**
  ```bash
  pf3p case3p_a 1e-6 csv
  ```
  *Output File:* `pf3p_case3p_a_bus3p.csv`

### 2.3 CLI Help & Word Help Export
You can view a console help manual for any command by appending `--help` or `-h`:
```bash
hepf --help
```
You can also **export the help manuals to a Word Document** by typing `docx` after help:
```bash
hepf --help docx
```
*Output File:* `hepf_help.docx`

---

## 3.0 Normal Python Scripting Mode

For advanced researchers, PowerPython can be imported directly into your custom scripts to run multi-case loops, sensitivites, or user-defined optimizations.

### 3.1 Scripting Example: Custom AC Power Flow Loop
```python
import power_python as pp
import numpy as np

# 1. Load the Case9 data structure
case = pp.PowerCase()
case.load_from_json("outputs/json/case9.json")

# 2. Run Holomorphic Embedding Power Flow (HEPF)
case, success = pp.run_hepf(case)

if success:
    # 3. Access bus voltages using the MATPOWER indexing constants
    vm = case.bus[:, pp.VM]
    va = case.bus[:, pp.VA]
    
    print("Voltages:")
    for i, bus_id in enumerate(case.external_bus_ids):
        print(f"Bus {int(bus_id)}: Magnitude = {vm[i]:.4f} pu, Angle = {va[i]:.2f} deg")
        
    # 4. Programmatic export to styled Excel sheet
    pp.export_results_excel(case, "solved_case9.xlsx", "hepf")
```

### 3.2 Programmatic Export API
You can export results programmatically from your scripts using:
*   `pp.export_results_excel(case, filename, analysis, extra_results=None)`: Exports to Excel (.xlsx) with Segmented sheets styled in MATLAB MATPOWER format.
*   `pp.export_results_csv(case, prefix, extra_results=None)`: Exports separate CSV files for `bus`, `gen`, and `branch`.
*   `pp.export_results_docx(case, filename, analysis, success, accuracy, extra_results=None, extra_info=None)`: Exports a Word report (.docx).

### 3.3 Solved Outputs Excel (.xlsx) Format Details
The exported Excel sheet has the following sheets and columns matching standard **MATLAB MATPOWER matrices**:
*   **`General`**: Single-cell `baseMVA` scalar value.
*   **`Bus`**: All 17 standard bus columns (`BUS_I`, `TYPE`, `PD`, `QD`, `GS`, `BS`, `BUS_AREA`, `VM`, `VA`, `BASE_KV`, `ZONE`, `VMAX`, `VMIN` + OPF multipliers if solved).
*   **`Generator`**: All 25 standard generator columns (`GEN_BUS`, `PG`, `QG`, `QMAX`, `QMIN`, `VG`, `MBASE`, `GEN_STATUS`, `PMAX`, `PMIN` + OPF multipliers if solved). PG and QG outputs are solved and updated.
*   **`Branch`**: All 21 standard branch columns (`F_BUS`, `T_BUS`, `BR_R`, `BR_X`, `BR_B`, `RATE_A`, `RATE_B`, `RATE_C`, `TAP`, `SHIFT`, `BR_STATUS`, `ANGMIN`, `ANGMAX`, `PF`, `QF`, `PT`, `QT` + OPF multipliers if solved).
*   **`Generator Cost`**: (If present) Holds piecewise linear/polynomial generator costs.
*   **`Bus3P` / `Line3P` / `Xfmr3P` / `Load3P` / `Gen3P` / `LineConst`**: (For 3-phase cases) Phase voltages and specs.

All worksheets are formatted with professional `Segoe UI` fonts, navy blue table headers, frozen first row, auto-fit column widths, visible gridlines, and numeric formatting.

### 3.4 Scripting Example: Sensitivity Factors and Contingency Loop
```python
import power_python as pp

case = pp.PowerCase()
case.load_from_json("outputs/json/case14.json")
case.to_internal()

# 1. Generate PTDF and LODF matrices
ptdf = pp.make_ptdf(case.baseMVA, case.bus, case.branch)
lodf = pp.make_lodf(case.branch, ptdf)

# 2. Run automated N-1 Contingency checks
violations_df = pp.run_contingency_analysis(case, verbose=True)
print(violations_df)
```

---

## 4.0 Catalog of Available Shell Commands

| Command | Category | Description |
| :--- | :--- | :--- |
| `acpf` | Power Flow | AC Power Flow using polar Newton-Raphson. |
| `gausspf` | Power Flow | AC Power Flow using legacy Gauss-Seidel iterations. |
| `fdpf` | Power Flow | AC Power Flow using Fast Decoupled (XB formulation). |
| `dcpf` | Power Flow | DC Linearized Power Flow. |
| `hepf` | Power Flow | Non-iterative Holomorphic Embedding Power Flow. |
| `cnr` | Power Flow | Wirtinger calculus Complex Newton-Raphson. |
| `pf3p` | Power Flow | 3-Phase Unbalanced Power Flow (Z-bus iterative method). |
| `radial` | Power Flow | Radial distribution grid BFS solver. |
| `dcopf` | Optimization | DC Optimal Power Flow (with reserve co-optimization). |
| `acopf` | Optimization | AC Optimal Power Flow using SciPy NLP minimization. |
| `sdpopf` | Optimization | Convex Semidefinite Programming OPF relaxation. |
| `uopf` | Optimization | Heuristic Unit Decommitment & OPF. |
| `scopf` | Optimization | Security-Constrained DC-OPF. |
| `opf3p` | Optimization | 3-Phase Unbalanced AC Optimal Power Flow. |
| `mpopf` | Optimization | Multi-period Storage and Ramping DC-OPF. |
| `stopf` | Optimization | Stochastic DC-OPF under renewable scenario profiles. |
| `market` | Market Operations | Smart Market electricity auction matching. |
| `lmp` | Market Operations | Locational Marginal Price congestion decomposition. |
| `varplan` | Grid Planning | VAr Planning / Optimal Capacitor Placement. |
| `contingency` | Security | Systematic N-1 Contingency Outage screening. |
| `se` | Monitoring | Weighted Least Squares (WLS) Grid State Estimation. |
| `cpf` | Stability | Continuation Power Flow tracing PV nose-point curves. |
| `audit` | Diagnostic | Nodal Active/Reactive power conservation audit. |

---

## 5.0 Authors & Acknowledgement

### Authors
1. **Robert MS Danaraj** (salorajan@gmail.com)
2. **Dr. M. RAMESH BABU**, Professor / EEE, St. Joseph's College of Engineering, Chennai, Tamilnadu, India (rameshbabum@stjosephs.ac.in)

### Acknowledgement
We express our sincere gratitude and appreciation to **St. Joseph's College of Engineering**, Chennai, Tamilnadu, India, for their help, support, and resources during the research, implementation, and verification of this power system analysis package.

