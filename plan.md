# Plan: MATPOWER Data Migration and Package Expansion

This plan outlines the stage-by-stage tasks to synchronize, license, align, and package the `power_python` project as a Python package that acts as a superset of MATPOWER (MATLAB).

---

## Stage 1: Repository Observation & Difference Analysis
- [x] **Task 1.1**: Compare local files with the remote GitHub repository `salorajan/matpower_data_migration`.
- [x] **Task 1.2**: List all differences (local modifications, untracked files, or missing commits).
- [x] **Task 1.3**: Validate the status of the local test suite.

## Stage 2: Licensing Review & Header Incorporation
- [x] **Task 2.1**: Analyze Cornell University's MATPOWER licensing (BSD 3-Clause) and ensure PSERC/Cornell copyright notice alignment.
- [x] **Task 2.2**: Prepare a standardized license header for all Python files.
- [x] **Task 2.3**: Inject license headers into all source code files under `power_python/` to maintain legal compliance.

## Stage 3: Feature Comparison & Superset Planning
- [x] **Task 3.1**: Compare MATPOWER MATLAB (v8.1) solvers with `power_python`'s current solvers.
- [x] **Task 3.2**: Identify missing features (e.g., ACPF with Decoupled/Gauss-Seidel, AC-OPF, advanced contingency).
- [x] **Task 3.3**: Read user selections from `fun0.txt` and clean up excluded solvers (TSR-HE, TSR-NR, HE-TMP, RHEM).
- [x] **Task 3.4**: Copy 3-phase JSON/Excel data cases and create `test_advanced_solvers.py` to verify standard HEPF, Complex NR, and 3-phase Complex NR.
- [x] **Task 3.5**: Exclude the Diagonal-Admittance Newton-Parametric method based on user instruction.

## Stage 4: Package Naming & PyPI Preparation
- [x] **Task 4.1**: Investigate PyPI package name availability (`powerpython`, `python-power`, `matpower-python`, etc.).
- [x] **Task 4.2**: Design and implement the package structure (`pyproject.toml`, `setup.py` if needed, `MANIFEST.in`).
- [x] **Task 4.3**: Integrate package configuration and verify local installation (`pip install -e .`).
- [x] **Task 4.4**: Verify package functionality by running the test suite under the newly packaged environment.
