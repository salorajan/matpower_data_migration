# PowerPython: Converted MATPOWER Data & Advanced Simulation Package

This repository provides a modernized, accessible version of the standard MATPOWER power system test cases and a fully integrated Pythonic simulation package (`powerpython`) that acts as a functional superset of MATPOWER (MATLAB).

---

## 1.0 Data Formats Available

The original `.m` files from the MATPOWER project have been converted into three high-accessibility formats under the `outputs/` folder:
- **Excel (.xlsx)**: Human-readable with standard IEEE headers. Each case contains separate sheets for `Bus`, `Generator`, `Branch`, and `GenCost`.
- **JSON (.json)**: Programmatic-friendly nested structures.
- **Parquet (.parquet)**: High-performance columnar storage optimized for Large-Scale analysis and Machine Learning dataloaders.

---

## 2.0 Features & Capability Catalog

PowerPython contains **23 analytical solvers** grouped by standard MATPOWER parity and advanced additions:

### 2.1 MATPOWER Parity Solvers
- **AC Power Flows**: Newton-Raphson (`acpf`), Gauss-Seidel (`gausspf`), and Fast Decoupled (`fdpf`).
- **DC Power Flow & OPF**: Linearized DCPF (`dcpf`), cost optimization (`dcopf`), co-optimized reserves.
- **AC Optimal Power Flow**: Non-convex optimization (`acopf`).
- **Security & Dispatch**: Contingency analysis (`contingency`), Security-Constrained OPF (`scopf`), Unit Decommitment OPF (`uopf`).
- **System Monitoring & Auctions**: State Estimation (`se`), Smart Market Auction (`market`), LMP Congestion Decomposition (`lmp`).
- **Sensitivity & Stability**: PTDF/LODF sensitivity factors, Continuation Power Flow (`cpf`).

### 2.2 Advanced Additions (Non-Existing in MATPOWER MATLAB)
- **Complex Wirtinger Newton-Raphson**: Bypasses polar variables solving directly in the complex variable domain (`cnr`).
- **Unbalanced 3-Phase solvers**: Full unbalanced 3-phase complex AC Power Flow (`pf3p`) and three-phase AC Optimal Power Flow (`opf3p`).
- **Holomorphic Embedding (HEPF)**: Non-iterative analytic continuation solver (`hepf`).
- **Distribution Solvers**: Backward-Forward Sweep power flow (`radial`).
- **Multi-Period & Storage**: DC-OPF with battery storage scheduling and ramping constraints (`mpopf`).
- **Stochastic Dispatch**: Optimization under renewable generation scenarios (`stopf`).
- **SDP OPF Relaxation**: Semidefinite Programming convex relaxation verifying global optimality (`sdpopf`).
- **Grid Planning**: VAr Planning/Capacitor placement (`varplan`).

---

## 3.0 Installation & Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/salorajan/matpower_data_migration.git
   cd matpower_data_migration
   ```
2. Install the package and dependencies in editable mode:
   ```bash
   pip install -e .
   ```

---

## 4.0 Dual-Mode Usage

Detailed instructions are available in the [User Manual](manual.md).

### 4.1 CLI Mode Examples
Registering console scripts makes the solvers directly executable from the terminal:
- **Run ACPF on Case 14 at 1e-4 accuracy, export to Excel:**
  ```bash
  acpf case14 1e-4 excel
  ```
  *(Generates `acpf_case14.xlsx` containing solved bus voltages, line flows, and generator active/reactive outputs in MATLAB MATPOWER format).*
- **Run HEPF on Case 9, export to Word Report (DOCX):**
  ```bash
  hepf case9 docx
  ```
- **Export solver help menu to Word Document:**
  ```bash
  hepf --help docx
  ```

### 4.2 Scripting Mode Example & Programmatic Export
Import the package directly in your custom Python scripts and export results programmatically:
```python
import power_python as pp

# 1. Load the case
case = pp.PowerCase()
case.load_from_json("outputs/json/case9.json")

# 2. Run the AC Power Flow
case, success = pp.run_power_flow(case)

if success:
    print(f"Bus 1 Voltage Magnitude: {case.bus[0, pp.VM]} p.u.")
    
    # 3. Export solved results to Excel in MATLAB MATPOWER format
    pp.export_results_excel(case, "acpf_results.xlsx", "acpf")
    
    # Or export to CSV
    pp.export_results_csv(case, "acpf_results", "acpf")
```

### 4.3 Solved Outputs & Format details
When you run any solver, the solved parameters are written directly into the `PowerCase` matrices, matching standard **MATLAB MATPOWER formats**:

#### 4.3.1 Excel (.xlsx) Output Structure
Exporting to Excel (`excel`/`xlsx`) generates a styled workbook with the following sheets and columns matching the standard MATPOWER matrices:
*   **`General`**: Holds the `baseMVA` scalar value.
*   **`Bus`**: Holds all 17 standard bus columns. Solved voltages are updated in `VM` and `VA`. If OPF is solved, Lagrange multipliers (`LAM_P`, `LAM_Q`, `MU_VMAX`, `MU_VMIN`) are included.
*   **`Generator`**: Holds all 25 standard generator columns. Active (`PG`) and reactive (`QG`) power generation outputs are updated at the PV and slack buses to balance load and losses. If OPF is solved, Kuhn-Tucker limits multipliers (`MU_PMAX`, `MU_PMIN`, `MU_QMAX`, `MU_QMIN`) are included.
*   **`Branch`**: Holds all 21 standard branch columns. Active and reactive branch power flows (`PF`, `QF`, `PT`, `QT`) are updated at both the "from" and "to" ends. If OPF is solved, constraint multipliers (`MU_SF`, `MU_ST`, `MU_ANGMIN`, `MU_ANGMAX`) are included.
*   **`Generator Cost`**: (If present) Holds the piecewise linear or polynomial generator cost parameters (`MODEL`, `STARTUP`, `SHUTDOWN`, `NCOST`, `COST_0`, `COST_1`, ...).
*   **`Bus3P` / `Line3P` / `Xfmr3P` / `Load3P` / `Gen3P` / `LineConst`**: (For 3-phase cases) Holds the solved phase voltages and line specifications.

The output sheets are styled with a clean `Segoe UI` font, header highlights (navy blue fill, white bold text), auto-adjusted columns to prevent truncation, and customized numeric styles (e.g. 4 decimals for voltages, 2 decimals for angles, and thousands separators for power).

---

## 5.0 Running Verification Tests

Run the full, detailed verification suite:
```bash
python power_python/tests/test_comprehensive.py
```

---

## 6.0 Authors & Acknowledgement

### Authors
1. **Robert MS Danaraj** (salorajan@gmail.com)
2. **Dr. M. RAMESH BABU**, Professor / EEE, St. Joseph's College of Engineering, Chennai, Tamilnadu, India (rameshbabum@stjosephs.ac.in)

### Acknowledgement
We express our sincere gratitude and appreciation to **St. Joseph's College of Engineering**, Chennai, Tamilnadu, India, for their help, support, and resources during the research, implementation, and verification of this power system analysis package.

