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

Detailed instructions are available in the [User Manual](file:///C:/users/robert/power/matpower_data_migration/manual.md).

### 4.1 CLI Mode Examples
Registering console scripts makes the solvers directly executable from the terminal:
- **Run ACPF on Case 14 at 1e-4 accuracy, export to Excel:**
  ```bash
  acpf case14 1e-4 excel
  ```
- **Run HEPF on Case 9, export to Word Report (DOCX):**
  ```bash
  hepf case9 docx
  ```
- **Export solver help menu to Word Document:**
  ```bash
  hepf --help docx
  ```

### 4.2 Scripting Mode Example
Import the package directly in your custom Python scripts:
```python
import power_python as pp

case = pp.PowerCase()
case.load_from_json("outputs/json/case9.json")

# Run Holomorphic Embedding
case, success = pp.run_hepf(case)
if success:
    print(f"Bus 1 Voltage Magnitude: {case.bus[0, pp.VM]} p.u.")
```

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

