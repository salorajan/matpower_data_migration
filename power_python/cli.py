# PowerPython
# Copyright (c) 2026 PowerPython contributors
# This file is derived from MATPOWER, Copyright (c) 1996-2025,
# Power Systems Engineering Research Center (PSERC) by Ray Zimmerman, PSERC Cornell.
# Licensed under the 3-clause BSD License (see LICENSE file for details).
# See https://github.com/salorajan/matpower_data_migration for more info.

import sys
import os
import numpy as np
import pandas as pd
import docx
from docx.shared import Pt

# Expose package path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from power_python.core.case import PowerCase
from power_python.core.constants import *
from power_python.solvers.runpf import run_power_flow
from power_python.solvers.complex_nr import run_complex_nr
from power_python.solvers.complex_nr_3p import run_complex_nr_3p
from power_python.solvers.rundcpf import run_dc_pf
from power_python.solvers.dcopf import run_dc_opf
from power_python.solvers.acopf import run_ac_opf
from power_python.solvers.sdp_opf import run_sdp_opf
from power_python.solvers.uopf import run_uopf
from power_python.solvers.cpf import run_cpf
from power_python.solvers.hepf import run_hepf
from power_python.solvers.se import run_state_estimation
from power_python.solvers.radial_pf import run_radial_pf
from power_python.solvers.pf_3p import run_3p_pf
from power_python.solvers.opf_3p import run_3p_opf
from power_python.solvers.mp_opf import run_mp_opf
from power_python.solvers.stochastic_opf import run_stochastic_opf
from power_python.solvers.market import run_market_auction
from power_python.solvers.var_planning import run_var_planning
from power_python.solvers.contingency import run_contingency_analysis
from power_python.solvers.sc_opf import run_sc_opf

from power_python.network.sensitivity import make_ptdf, make_lodf
from power_python.utils.audit import calculate_system_balance
from power_python.utils.lmp_decomp import decompose_dc_lmp
from power_python.utils.costs import calculate_total_cost

# Root data directory mapping
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.join(BASE_DIR, "outputs", "json")

HELP_DICT = {
    "acpf": """AC Power Flow (Newton-Raphson)
Usage: acpf <case_id> [accuracy] [excel|csv|docx]
Example: acpf case14 1e-5 excel
Physics/Algorithm: 
Solves AC power flow using the standard Newton-Raphson iteration in polar coordinates. 
Constructs a coupled Jacobian matrix of active/reactive mismatches with respect to voltage angle and magnitude, updating state variables quadratically in 3-5 iterations.""",
    
    "gausspf": """AC Power Flow (Gauss-Seidel)
Usage: gausspf <case_id> [accuracy] [excel|csv|docx]
Example: gausspf case9 1e-4 docx
Physics/Algorithm:
Solves AC power flow using legacy Gauss-Seidel nodal propagation.
It solves voltage variables sequentially (Seidel mode) based on the latest iteration estimates. Slow convergence, but requires no Jacobian construction.""",
    
    "fdpf": """AC Power Flow (Fast Decoupled)
Usage: fdpf <case_id> [accuracy] [excel|csv|docx]
Example: fdpf case30 1e-5 csv
Physics/Algorithm:
Solves AC power flow using the Fast Decoupled method (XB formulation).
Decouples voltage magnitudes and angles by neglecting conductance matrices, using constant B' and B'' susceptance matrices. Highly efficient per-iteration scaling.""",
    
    "dcpf": """DC Power Flow (Linearized)
Usage: dcpf <case_id> [accuracy] [excel|csv|docx]
Example: dcpf case118 excel
Physics/Algorithm:
Solves linearized DC power flow by assuming voltage magnitudes are flat at 1.0 p.u., neglecting resistance (R=0) and shunt admittances, resulting in a single linear system solve.""",
    
    "hepf": """Holomorphic Embedding Power Flow (HEPF)
Usage: hepf <case_id> [accuracy] [excel|csv|docx]
Example: hepf case9 1e-6 docx
Physics/Algorithm:
A non-iterative power flow solver based on analytic continuation. 
Formulates a holomorphic parameterization of the network and evaluates physical branch voltage functions via Padé Approximants, guaranteeing discovery of the high-voltage solution without starting guesses.""",
    
    "cnr": """Complex Newton-Raphson (CVNR)
Usage: cnr <case_id> [accuracy] [excel|csv|docx]
Example: cnr case14 1e-8 excel
Physics/Algorithm:
Solves power flow directly in the complex variable plane using Wirtinger calculus derivatives. 
Bypasses polar decomposition, solving a complex mismatch system of size 2N x 2N.""",
    
    "pf3p": """Three-Phase Unbalanced Power Flow
Usage: pf3p <case_id> [accuracy] [excel|csv|docx]
Example: pf3p case3p_a 1e-5 excel
Physics/Algorithm:
Solves unbalanced 3-phase power flow using the Z-bus iterative method.
Accommodates coupling matrices across phases a-b-c, suitable for distribution system modeling.""",
    
    "radial": """Radial Backward-Forward Sweep Power Flow (BFS)
Usage: radial <case_id> [accuracy] [excel|csv|docx]
Example: radial case33bw 1e-6 csv
Physics/Algorithm:
Backward-Forward Sweep (BFS) solver optimized for radial distribution feeders.
Calculates branch currents backward from leaves to root, then updates bus voltages forward from root to leaves.""",
    
    "dcopf": """DC Optimal Power Flow (DC-OPF)
Usage: dcopf <case_id> [accuracy] [excel|csv|docx]
Example: dcopf case9 excel
Physics/Algorithm:
Optimizes generator active power outputs to minimize costs under transmission line limit constraints. 
Uses linearized DC power flow equations co-optimizing spinning reserves if defined.""",
    
    "acopf": """AC Optimal Power Flow (AC-OPF)
Usage: acopf <case_id> [accuracy] [excel|csv|docx]
Example: acopf case14 docx
Physics/Algorithm:
Solves the non-linear, non-convex AC Optimal Power Flow utilizing SciPy SLSQP.
Minimizes generation cost while co-optimizing active/reactive dispatch, keeping voltage profiles within bounds.""",
    
    "sdpopf": """Convex SDP Optimal Power Flow
Usage: sdpopf <case_id> [accuracy] [excel|csv|docx]
Example: sdpopf case9 excel
Physics/Algorithm:
Formulates the non-convex AC-OPF as a convex Semidefinite Programming (SDP) relaxation (Lavaei & Low method).
Relaxes the rank-1 constraint on the voltage matrix. Evaluates global optimality bounds directly via eigenvalue gap.""",
    
    "uopf": """Unit Decommitment and OPF (UOPF)
Usage: uopf <case_id> [accuracy] [excel|csv|docx]
Example: uopf case9 1e-5 excel
Physics/Algorithm:
Determines optimal unit decommitment status and co-optimized generator dispatch using heuristic search.
Progressively shuts down uneconomical generators to minimize total system cost while satisfying grid constraints.""",
    
    "scopf": """Security-Constrained OPF (SC-OPF)
Usage: scopf <case_id> [accuracy] [excel|csv|docx]
Example: scopf case30 excel
Physics/Algorithm:
Solves security-constrained active power dispatch.
Guarantees grid operation remains secure and line flows do not exceed emergency limits under any single N-1 transmission outage.""",
    
    "opf3p": """Three-Phase Unbalanced AC-OPF
Usage: opf3p <case_id> [accuracy] [excel|csv|docx]
Example: opf3p case3p_a excel
Physics/Algorithm:
Solves unbalanced three-phase AC Optimal Power Flow.
Optimizes generator dispatch at the phase level (a-b-c) to minimize unbalanced distribution costs under operational constraints.""",
    
    "mpopf": """Multi-Period OPF with Energy Storage (MPOPF)
Usage: mpopf <case_id> [accuracy] [excel|csv|docx]
Example: mpopf case9 excel
Physics/Algorithm:
Co-optimizes generator active power dispatch and battery charging/discharging profiles over a multi-period horizon.
Integrates battery state-of-charge constraints and generator ramping limits.""",
    
    "stopf": """Stochastic DC Optimal Power Flow
Usage: stopf <case_id> [accuracy] [excel|csv|docx]
Example: stopf case9 csv
Physics/Algorithm:
Solves stochastic active dispatch optimization.
Minimizes the expected generation costs over multiple probabilistic renewable generation scenarios (wind/solar).""",
    
    "market": """Smart Market Auction Simulation
Usage: market <case_id> [accuracy] [excel|csv|docx]
Example: market case9 excel
Physics/Algorithm:
Simulates a competitive electricity market auction.
Clears generator step offers and load bids under network flow constraints, calculating cleared power and turnover.""",
    
    "varplan": """VAr Planning / Optimal Capacitor Placement
Usage: varplan <case_id> [accuracy] [excel|csv|docx]
Example: varplan case14 docx
Physics/Algorithm:
Solves optimal reactive power planning using AC-OPF models.
Places shunt susceptance (capacitors) at optimal candidate buses to keep voltages within limits at minimum installation cost.""",
    
    "contingency": """N-1 Contingency Analysis Screening
Usage: contingency <case_id> [accuracy] [excel|csv|docx]
Example: contingency case14 csv
Physics/Algorithm:
Performs systematic screening of single-line outage contingencies using PTDF and LODF sensitivity factors.
Quickly identifies potential line overload violations across all single line outages.""",
    
    "se": """Weighted Least Squares State Estimation (SE)
Usage: se <case_id> [accuracy] [excel|csv|docx]
Example: se case9 1e-6 docx
Physics/Algorithm:
Solves power system state estimation using Weighted Least Squares (WLS).
Filters noise from redundant measurements (power, voltage, flow) to estimate the true state variables (voltages).""",
    
    "cpf": """Continuation Power Flow (CPF)
Usage: cpf <case_id> [accuracy] [excel|csv|docx]
Example: cpf case9 excel
Physics/Algorithm:
Traces the grid's voltage loadability profile (PV curve) using predictor-corrector continuation steps.
Maintains numeric stability near bifurcation, identifying the maximum loadability nose point.""",
    
    "audit": """Physical Power Balance Audit
Usage: audit <case_id> [accuracy] [excel|csv|docx]
Example: audit case9 docx
Physics/Algorithm:
Checks physical power conservation in the network.
Computes absolute active and reactive residuals (Total Generation - Total Load - Losses) to verify case validity.""",
    
    "lmp": """LMP Energy/Congestion Decomposition
Usage: lmp <case_id> [accuracy] [excel|csv|docx]
Example: lmp case9 excel
Physics/Algorithm:
Decomposes Locational Marginal Prices (LMP) from DC-OPF dual variables.
Partitions nodal marginal costs into Energy and Congestion components to highlight transmission congestion pricing."""
}

def load_case_by_id(case_id):
    full_name = case_id if case_id.startswith("case") else f"case{case_id}"
    # Remove file extension if user typed it
    if full_name.endswith(".json"):
        full_name = full_name[:-5]
    elif full_name.endswith(".xlsx"):
        full_name = full_name[:-5]
        
    case_path = os.path.join(CASE_DIR, f"{full_name}.json")
    if not os.path.exists(case_path):
        print(f"Error: Case file not found at {case_path}")
        return None
        
    case = PowerCase()
    case.load_from_json(case_path)
    return case

def export_results_excel(case, filename, analysis, extra_results=None):
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    
    # Re-calculate generator PG and QG outputs first to ensure they are up to date in the exported case
    case.update_generator_power()
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Write General sheet if it has baseMVA
        if hasattr(case, 'baseMVA'):
            gen_df = pd.DataFrame({"baseMVA": [case.baseMVA]})
            gen_df.to_excel(writer, sheet_name='General', index=False)
            
        if hasattr(case, 'bus') and case.bus is not None and len(case.bus) > 0:
            # Bus sheet in MATLAB MATPOWER format
            bus_data = {
                "BUS_I": case.external_bus_ids.astype(int),
                "TYPE": case.bus[:, BUS_TYPE].astype(int),
                "PD": case.bus[:, PD],
                "QD": case.bus[:, QD],
                "GS": case.bus[:, GS],
                "BS": case.bus[:, BS],
                "BUS_AREA": case.bus[:, BUS_AREA].astype(int),
                "VM": case.bus[:, VM],
                "VA": case.bus[:, VA],
                "BASE_KV": case.bus[:, BASE_KV],
                "ZONE": case.bus[:, ZONE].astype(int),
                "VMAX": case.bus[:, VMAX],
                "VMIN": case.bus[:, VMIN],
            }
            if case.bus.shape[1] > 13:
                # Add OPF variables if they exist in the matrix
                bus_data["LAM_P"] = case.bus[:, LAM_P]
                bus_data["LAM_Q"] = case.bus[:, LAM_Q]
                bus_data["MU_VMAX"] = case.bus[:, MU_VMAX]
                bus_data["MU_VMIN"] = case.bus[:, MU_VMIN]
                
            bus_df = pd.DataFrame(bus_data)
            bus_df.to_excel(writer, sheet_name='Bus', index=False)
            
            # Generator sheet in MATLAB MATPOWER format
            gen_bus_ids = [int(case.external_bus_ids[int(b)]) for b in case.gen[:, GEN_BUS]]
            gen_data = {
                "GEN_BUS": gen_bus_ids,
                "PG": case.gen[:, PG],
                "QG": case.gen[:, QG],
                "QMAX": case.gen[:, QMAX],
                "QMIN": case.gen[:, QMIN],
                "VG": case.gen[:, VG],
                "MBASE": case.gen[:, MBASE],
                "GEN_STATUS": case.gen[:, GEN_STATUS].astype(int),
                "PMAX": case.gen[:, PMAX],
                "PMIN": case.gen[:, PMIN],
                "PC1": case.gen[:, PC1],
                "PC2": case.gen[:, PC2],
                "QC1MIN": case.gen[:, QC1MIN],
                "QC1MAX": case.gen[:, QC1MAX],
                "QC2MIN": case.gen[:, QC2MIN],
                "QC2MAX": case.gen[:, QC2MAX],
                "RAMP_AGC": case.gen[:, RAMP_AGC],
                "RAMP_10": case.gen[:, RAMP_10],
                "RAMP_30": case.gen[:, RAMP_30],
                "RAMP_Q": case.gen[:, RAMP_Q],
                "APF": case.gen[:, APF],
            }
            if case.gen.shape[1] > 21:
                gen_data["MU_PMAX"] = case.gen[:, MU_PMAX]
                gen_data["MU_PMIN"] = case.gen[:, MU_PMIN]
                gen_data["MU_QMAX"] = case.gen[:, MU_QMAX]
                gen_data["MU_QMIN"] = case.gen[:, MU_QMIN]
                
            gen_df = pd.DataFrame(gen_data)
            gen_df.to_excel(writer, sheet_name='Generator', index=False)
            
            # Branch sheet in MATLAB MATPOWER format
            f_bus_ids = [int(case.external_bus_ids[int(b)]) for b in case.branch[:, F_BUS]]
            t_bus_ids = [int(case.external_bus_ids[int(b)]) for b in case.branch[:, T_BUS]]
            branch_data = {
                "F_BUS": f_bus_ids,
                "T_BUS": t_bus_ids,
                "BR_R": case.branch[:, BR_R],
                "BR_X": case.branch[:, BR_X],
                "BR_B": case.branch[:, BR_B],
                "RATE_A": case.branch[:, RATE_A],
                "RATE_B": case.branch[:, RATE_B],
                "RATE_C": case.branch[:, RATE_C],
                "TAP": case.branch[:, TAP],
                "SHIFT": case.branch[:, SHIFT],
                "BR_STATUS": case.branch[:, BR_STATUS].astype(int),
                "ANGMIN": case.branch[:, ANGMIN],
                "ANGMAX": case.branch[:, ANGMAX],
                "PF": case.branch[:, PF],
                "QF": case.branch[:, QF],
                "PT": case.branch[:, PT],
                "QT": case.branch[:, QT],
            }
            if case.branch.shape[1] > 17:
                branch_data["MU_SF"] = case.branch[:, MU_SF]
                branch_data["MU_ST"] = case.branch[:, MU_ST]
                branch_data["MU_ANGMIN"] = case.branch[:, MU_ANGMIN]
                branch_data["MU_ANGMAX"] = case.branch[:, MU_ANGMAX]
                
            branch_df = pd.DataFrame(branch_data)
            branch_df.to_excel(writer, sheet_name='Branch', index=False)
            
            # Generator Cost sheet if present and not empty
            if hasattr(case, 'gencost') and case.gencost is not None and len(case.gencost) > 0:
                gencost_cols = ["MODEL", "STARTUP", "SHUTDOWN", "NCOST"] + [f"COST_{i}" for i in range(case.gencost.shape[1] - 4)]
                num_cols = min(len(gencost_cols), case.gencost.shape[1])
                gencost_df = pd.DataFrame(case.gencost[:, :num_cols], columns=gencost_cols[:num_cols])
                # Format integer columns
                for col in ["MODEL", "NCOST"]:
                    if col in gencost_df:
                        gencost_df[col] = gencost_df[col].astype(int)
                gencost_df.to_excel(writer, sheet_name='Generator Cost', index=False)
                
        # Write 3-Phase sheets if present
        if hasattr(case, 'bus3p') and case.bus3p is not None and len(case.bus3p) > 0:
            bus3p_df = pd.DataFrame(case.bus3p, columns=["Bus_ID", "Type", "BaseKV", "Vm_a", "Vm_b", "Vm_c", "Va_a", "Va_b", "Va_c"])
            bus3p_df.to_excel(writer, sheet_name='Bus3P', index=False)
            
            if hasattr(case, 'line3p') and case.line3p is not None and len(case.line3p) > 0:
                pd.DataFrame(case.line3p).to_excel(writer, sheet_name='Line3P', index=False)
            if hasattr(case, 'xfmr3p') and case.xfmr3p is not None and len(case.xfmr3p) > 0:
                pd.DataFrame(case.xfmr3p).to_excel(writer, sheet_name='Xfmr3P', index=False)
            if hasattr(case, 'load3p') and case.load3p is not None and len(case.load3p) > 0:
                pd.DataFrame(case.load3p).to_excel(writer, sheet_name='Load3P', index=False)
            if hasattr(case, 'gen3p') and case.gen3p is not None and len(case.gen3p) > 0:
                pd.DataFrame(case.gen3p).to_excel(writer, sheet_name='Gen3P', index=False)
            if hasattr(case, 'lc') and case.lc is not None and len(case.lc) > 0:
                pd.DataFrame(case.lc).to_excel(writer, sheet_name='LineConst', index=False)
                
        # Write Extra / Analysis results
        if extra_results is not None:
            if isinstance(extra_results, pd.DataFrame):
                extra_results.to_excel(writer, sheet_name='Analysis_Results', index=False)
            elif isinstance(extra_results, dict):
                for k, v in extra_results.items():
                    sheet_name = f"Analysis_{k}"[:31]
                    if isinstance(v, pd.DataFrame):
                        v.to_excel(writer, sheet_name=sheet_name, index=False)
                    else:
                        pd.DataFrame(v).to_excel(writer, sheet_name=sheet_name, index=False)

    # Re-open the excel file with openpyxl to apply gorgeous styling & formatting
    wb = openpyxl.load_workbook(filename)
    
    # Styles definition
    hdr_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    hdr_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    data_font = Font(name="Segoe UI", size=10)
    
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    
    # Columns that should be centered (integer IDs, types, codes)
    center_cols = {
        "BUS_I", "TYPE", "BUS_AREA", "ZONE", "GEN_BUS", "GEN_STATUS",
        "F_BUS", "T_BUS", "BR_STATUS", "MODEL", "NCOST", "Bus_ID", "Type"
    }
    
    # Columns that should be formatted as 4-decimal floats (voltage magnitudes)
    v_cols = {"VM", "VMAX", "VMIN", "VG", "Vm_a", "Vm_b", "Vm_c"}
    
    # Columns that should be formatted as 2-decimal floats (angles)
    ang_cols = {"VA", "Va_a", "Va_b", "Va_c", "SHIFT", "ANGMIN", "ANGMAX"}
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        ws.sheet_view.showGridLines = True
        
        # Determine number of rows and columns
        max_row = ws.max_row
        max_col = ws.max_column
        
        if max_row == 0 or max_col == 0:
            continue
            
        # Freeze headers
        ws.freeze_panes = "A2"
        
        # Read header names
        headers = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]
        
        # Style Header Row
        ws.row_dimensions[1].height = 26
        for c in range(1, max_col + 1):
            cell = ws.cell(row=1, column=c)
            cell.font = hdr_font
            cell.fill = hdr_fill
            cell.alignment = center_align
            
        # Style Data Rows
        for r in range(2, max_row + 1):
            ws.row_dimensions[r].height = 20
            for c in range(1, max_col + 1):
                cell = ws.cell(row=r, column=c)
                cell.font = data_font
                
                col_name = headers[c - 1]
                val = cell.value
                
                # Check alignment and number formats
                if col_name in center_cols:
                    cell.alignment = center_align
                    if val is not None:
                        try:
                            cell.value = int(float(val))
                            cell.number_format = "0"
                        except ValueError:
                            pass
                elif isinstance(val, (int, float)):
                    cell.alignment = right_align
                    if col_name in v_cols:
                        cell.number_format = "0.0000"
                    elif col_name in ang_cols:
                        cell.number_format = "0.00"
                    else:
                        cell.number_format = "#,##0.00"
                else:
                    cell.alignment = left_align
                    
        # Auto-adjust column widths with some padding
        for c in range(1, max_col + 1):
            col_letter = openpyxl.utils.get_column_letter(c)
            max_len = 0
            for r in range(1, max_row + 1):
                val = ws.cell(row=r, column=c).value
                if val is not None:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
            
    wb.save(filename)
    print(f"Results exported to Excel: {filename}")

def export_results_csv(case, prefix, extra_results=None):
    case.update_generator_power()
    if hasattr(case, 'bus') and case.bus is not None:
        bus_df = pd.DataFrame({
            "Bus_ID": case.external_bus_ids.astype(int),
            "VM_pu": case.bus[:, VM],
            "VA_deg": case.bus[:, VA]
        })
        bus_df.to_csv(f"{prefix}_bus.csv", index=False)
        
        gen_bus_ids = [int(case.external_bus_ids[int(b)]) for b in case.gen[:, GEN_BUS]]
        gen_df = pd.DataFrame({
            "Bus_ID": gen_bus_ids,
            "PG_MW": case.gen[:, PG],
            "QG_MVAr": case.gen[:, QG]
        })
        gen_df.to_csv(f"{prefix}_gen.csv", index=False)
        
        f_bus_ids = [int(case.external_bus_ids[int(b)]) for b in case.branch[:, F_BUS]]
        t_bus_ids = [int(case.external_bus_ids[int(b)]) for b in case.branch[:, T_BUS]]
        branch_df = pd.DataFrame({
            "From_Bus": f_bus_ids,
            "To_Bus": t_bus_ids,
            "P_MW": case.branch[:, PF],
            "Q_MVAr": case.branch[:, QF]
        })
        branch_df.to_csv(f"{prefix}_branch.csv", index=False)
        print(f"Results exported to CSV: {prefix}_bus.csv, {prefix}_gen.csv, {prefix}_branch.csv")
        
    if hasattr(case, 'bus3p') and case.bus3p is not None:
        bus3p_df = pd.DataFrame(case.bus3p, columns=["Bus_ID", "Type", "BaseKV", "Vm1", "Vm2", "Vm3", "Va1", "Va2", "Va3"])
        bus3p_df.to_csv(f"{prefix}_bus3p.csv", index=False)
        print(f"Results exported to CSV: {prefix}_bus3p.csv")
        
    if extra_results is not None:
        if isinstance(extra_results, pd.DataFrame):
            extra_results.to_csv(f"{prefix}_extra.csv", index=False)
        elif isinstance(extra_results, dict):
            for k, v in extra_results.items():
                pd.DataFrame(v).to_csv(f"{prefix}_{k}.csv", index=False)
        print(f"Extra results exported to CSV.")

def export_results_docx(case, filename, analysis, success, accuracy, extra_results=None, extra_info=None):
    doc = docx.Document()
    
    # Header
    title = doc.add_paragraph()
    run = title.add_run("PowerPython Simulation Report")
    run.font.size = Pt(24)
    run.font.bold = True
    
    # Subtitle
    sub = doc.add_paragraph()
    grid_size = case.external_bus_ids.size if hasattr(case, 'external_bus_ids') else len(case.bus3p)
    run_sub = sub.add_run(f"Method: {analysis.upper()} | Case Size: {grid_size}-Bus Grid")
    run_sub.font.size = Pt(14)
    run_sub.italic = True
    
    # Section 1: Summary
    doc.add_heading("1.0 Simulation Summary", level=1)
    
    p = doc.add_paragraph()
    p.add_run("Convergence Status: ").bold = True
    p.add_run("SUCCESS\n" if success else "FAILED\n")
    p.add_run("Accuracy/Tolerance: ").bold = True
    p.add_run(f"{accuracy:.2e}\n")
    
    if hasattr(case, 'bus') and case.bus is not None:
        vm = case.bus[:, VM]
        p.add_run("Voltage Range: ").bold = True
        p.add_run(f"Min: {np.min(vm):.4f} p.u. | Max: {np.max(vm):.4f} p.u.\n")
        
        p_loss = np.sum(case.branch[:, PF] + case.branch[:, PT])
        q_loss = np.sum(case.branch[:, QF] + case.branch[:, QT])
        p.add_run("System Losses: ").bold = True
        p.add_run(f"P_loss: {p_loss:.4f} MW | Q_loss: {q_loss:.4f} MVAr\n")
        
        p_gen = np.sum(case.gen[:, PG])
        p.add_run("Total Generation: ").bold = True
        p.add_run(f"P_gen: {p_gen:.2f} MW\n")
        
    if extra_info:
        for k, v in extra_info.items():
            p.add_run(f"{k}: ").bold = True
            p.add_run(f"{v}\n")
            
    # Section 2: Tables
    if hasattr(case, 'bus') and case.bus is not None:
        doc.add_heading("2.0 Bus Voltages (First 30)", level=1)
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Light Shading Accent 1'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Bus ID'
        hdr_cells[1].text = 'Type'
        hdr_cells[2].text = 'V Magnitude (pu)'
        hdr_cells[3].text = 'V Angle (deg)'
        
        for i in range(min(30, len(case.bus))):
            row_cells = table.add_row().cells
            row_cells[0].text = str(int(case.external_bus_ids[i]))
            row_cells[1].text = str(int(case.bus[i, BUS_TYPE]))
            row_cells[2].text = f"{case.bus[i, VM]:.4f}"
            row_cells[3].text = f"{case.bus[i, VA]:.2f}"
            
        doc.add_heading("3.0 Generator Dispatch", level=1)
        table_gen = doc.add_table(rows=1, cols=4)
        table_gen.style = 'Light Shading Accent 1'
        hdr_gen = table_gen.rows[0].cells
        hdr_gen[0].text = 'Gen ID'
        hdr_gen[1].text = 'Bus ID'
        hdr_gen[2].text = 'PG (MW)'
        hdr_gen[3].text = 'QG (MVAr)'
        
        for i in range(len(case.gen)):
            row_cells = table_gen.add_row().cells
            row_cells[0].text = str(i + 1)
            row_cells[1].text = str(int(case.external_bus_ids[int(case.gen[i, GEN_BUS])]))
            row_cells[2].text = f"{case.gen[i, PG]:.2f}"
            row_cells[3].text = f"{case.gen[i, QG]:.2f}"
            
    elif hasattr(case, 'bus3p') and case.bus3p is not None:
        doc.add_heading("2.0 3-Phase Bus Voltages", level=1)
        table = doc.add_table(rows=1, cols=7)
        table.style = 'Light Shading Accent 1'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Bus ID'
        hdr_cells[1].text = 'Va (pu)'
        hdr_cells[2].text = 'Vb (pu)'
        hdr_cells[3].text = 'Vc (pu)'
        hdr_cells[4].text = 'AngA'
        hdr_cells[5].text = 'AngB'
        hdr_cells[6].text = 'AngC'
        
        for i in range(len(case.bus3p)):
            row_cells = table.add_row().cells
            row_cells[0].text = str(int(case.bus3p[i, 0]))
            row_cells[1].text = f"{case.bus3p[i, 3]:.4f}"
            row_cells[2].text = f"{case.bus3p[i, 4]:.4f}"
            row_cells[3].text = f"{case.bus3p[i, 5]:.4f}"
            row_cells[4].text = f"{case.bus3p[i, 6]:.2f}"
            row_cells[5].text = f"{case.bus3p[i, 7]:.2f}"
            row_cells[6].text = f"{case.bus3p[i, 8]:.2f}"
            
    # Section 4: Extra Results if present
    if extra_results is not None:
        doc.add_heading("4.0 Optimization / Extra Outputs", level=1)
        if isinstance(extra_results, pd.DataFrame):
            # Render first 20 rows of DataFrame
            table_extra = doc.add_table(rows=1, cols=len(extra_results.columns))
            table_extra.style = 'Light Shading Accent 1'
            for col_idx, col_name in enumerate(extra_results.columns):
                table_extra.rows[0].cells[col_idx].text = str(col_name)
            for r_idx in range(min(20, len(extra_results))):
                row_cells = table_extra.add_row().cells
                for col_idx, col_name in enumerate(extra_results.columns):
                    row_cells[col_idx].text = f"{extra_results.iloc[r_idx, col_idx]}"
        elif isinstance(extra_results, dict):
            for k, v in extra_results.items():
                doc.add_paragraph().add_run(f"Data: {k}").bold = True
                p_dict = doc.add_paragraph()
                p_dict.add_run(str(v)[:800])
                
    doc.save(filename)
    print(f"Results exported to Word Document: {filename}")

def print_help_console(analysis):
    help_text = HELP_DICT.get(analysis, f"No detailed help available for {analysis}.")
    print("\n" + "="*80)
    print(f"{analysis.upper()} SOLVER HELP")
    print("="*80)
    print(help_text)
    print("="*80 + "\n")

def export_help_docx(analysis):
    help_text = HELP_DICT.get(analysis, f"No detailed help available for {analysis}.")
    filename = f"{analysis}_help.docx"
    doc = docx.Document()
    doc.add_heading(f"PowerPython Solver Help: {analysis.upper()}", level=0)
    
    for line in help_text.split('\n'):
        if line.startswith("Usage:"):
            doc.add_heading("Usage", level=1)
            doc.add_paragraph(line)
        elif line.startswith("Example:"):
            p = doc.add_paragraph()
            p.add_run("Example: ").bold = True
            p.add_run(line[8:])
        elif line.startswith("Physics/Algorithm:"):
            doc.add_heading("Physics & Algorithm", level=1)
        else:
            doc.add_paragraph(line)
            
    doc.save(filename)
    print(f"Help content exported to Word Document: {filename}")

def run_cli_command(analysis, args):
    is_help = any(h in args for h in ["--help", "-h", "help"])
    if is_help:
        if "docx" in args:
            export_help_docx(analysis)
        else:
            print_help_console(analysis)
        return
        
    if len(args) < 1:
        print(f"Error: Missing case_id parameter.")
        print_help_console(analysis)
        return
        
    case_id = args[0]
    
    # Parse accuracy dynamically (e.g. 1e-4, 0.0001, 1.0e-5)
    accuracy = 1e-8
    for arg in args[1:]:
        try:
            if ("e" in arg or "." in arg or arg.isdigit()) and not any(ext in arg.lower() for ext in ["excel", "xlsx", "csv", "docx", "word"]):
                accuracy = float(arg)
                break
        except ValueError:
            pass
            
    # Parse export format
    export_format = None
    for arg in args[1:]:
        arg_lower = arg.lower()
        if arg_lower in ["excel", "xlsx"]:
            export_format = "excel"
            break
        elif arg_lower in ["csv"]:
            export_format = "csv"
            break
        elif arg_lower in ["docx", "word"]:
            export_format = "docx"
            break

    # Load case
    case = load_case_by_id(case_id)
    if case is None:
        return
        
    print(f"Running {analysis.upper()} on Case {case_id} (accuracy={accuracy:.2e})...")
    
    success = False
    extra_results = None
    extra_info = {}
    
    if analysis == 'acpf':
        case, success = run_power_flow(case, algorithm='nr', tol=accuracy, verbose=True)
    elif analysis == 'gausspf':
        case, success = run_power_flow(case, algorithm='gs', tol=accuracy, verbose=True)
    elif analysis == 'fdpf':
        case, success = run_power_flow(case, algorithm='fd', tol=accuracy, verbose=True)
    elif analysis == 'dcpf':
        case, success = run_dc_pf(case)
    elif analysis == 'hepf':
        # HEPF check accuracy dynamically by matching iterations
        case, success = run_hepf(case, verbose=True)
    elif analysis == 'cnr':
        case, success = run_complex_nr(case, tol=accuracy, verbose=True)
    elif analysis == 'pf3p':
        case, success = run_3p_pf(case, tol=accuracy, verbose=True)
    elif analysis == 'radial':
        case, success = run_radial_pf(case, tol=accuracy, verbose=True)
    elif analysis == 'dcopf':
        case, success = run_dc_opf(case, verbose=True)
        if success:
            extra_info["Total Optimized Cost"] = f"${calculate_total_cost(case):,.2f}"
    elif analysis == 'acopf':
        case, success = run_ac_opf(case, verbose=True)
        if success:
            extra_info["Total Optimized Cost"] = f"${calculate_total_cost(case):,.2f}"
    elif analysis == 'sdpopf':
        case, success = run_sdp_opf(case, verbose=True)
        if success:
            extra_info["Total Lower Bound Cost"] = f"${calculate_total_cost(case):,.2f}"
    elif analysis == 'uopf':
        case, success = run_uopf(case, solver='dcopf', verbose=True)
        if success:
            extra_info["Optimized Cost"] = f"${calculate_total_cost(case):,.2f}"
            extra_info["Generators Online"] = f"{np.sum(case.gen[:, GEN_STATUS] > 0)} / {len(case.gen)}"
    elif analysis == 'scopf':
        case, success = run_sc_opf(case, verbose=True)
    elif analysis == 'opf3p':
        case, success = run_3p_opf(case, verbose=True)
    elif analysis == 'mpopf':
        nt = 6
        if not case.profiles.get('load'): case.profiles['load'] = [1.0, 1.2, 1.5, 1.3, 1.1, 0.9]
        if not case.storage: case.storage = {'idx': [0], 'MaxCharge': [10.0], 'MaxDischarge': [10.0], 'InEff': [0.95], 'OutEff': [0.95], 'MinSOC': [0.0], 'MaxSOC': [50.0], 'InitialSOC': [25.0]}
        results, success = run_mp_opf(case, nt=nt, verbose=True)
        if success:
            ng = len(case.gen)
            extra_results = pd.DataFrame(results['Pg'], columns=[f"Gen {i+1}" for i in range(ng)])
            extra_info["Total Operating Cost"] = f"${results['Cost']:,.2f}"
    elif analysis == 'stopf':
        results, success = run_stochastic_opf(case, verbose=True)
        if success:
            extra_results = pd.DataFrame(results['Pg'])
            extra_info["Expected Operating Cost"] = f"${results['Expected_Cost']:,.2f}"
    elif analysis == 'market':
        ng = len(case.gen)
        offers = {'qty': [[50, 50, 50]] * ng, 'prc': [[20, 40, 60]] * ng}
        case, mkt_df = run_market_auction(case, offers, verbose=True)
        if mkt_df is not None:
            success = True
            extra_results = mkt_df
            extra_info["Total Market Turnover"] = f"${mkt_df['Revenue_$'].sum():,.2f}"
    elif analysis == 'varplan':
        case, success = run_var_planning(case, verbose=True)
        if success:
            extra_info["Total Compensation Added"] = f"{np.sum(case.bus[:, BS]):.2f} MVAr"
    elif analysis == 'contingency':
        df = run_contingency_analysis(case, verbose=True)
        if not df.empty:
            success = True
            extra_results = df
            extra_info["Violations Detected"] = f"{len(df)} outages exceeded limits"
        else:
            success = True
            print("No line flow violations detected.")
    elif analysis == 'se':
        case, success = run_state_estimation(case, verbose=True)
    elif analysis == 'cpf':
        results = run_cpf(case, verbose=True)
        if results:
            success = True
            extra_results = pd.DataFrame(results, columns=['lambda', 'vm_avg'])
            extra_info["Maximum System Loadability (Lambda)"] = f"{results[-1][0]:.4f}"
    elif analysis == 'audit':
        case.to_internal()
        balance = calculate_system_balance(case)
        success = True
        extra_info["P Residual"] = f"{balance['residual_p']:.4f} MW"
        extra_info["Q Residual"] = f"{balance['residual_q']:.4f} MVAr"
        print(f"Audit Residual P: {balance['residual_p']:.4f} MW | Q: {balance['residual_q']:.4f} MVAr")
    elif analysis == 'lmp':
        case, success = run_dc_opf(case, verbose=False)
        if success:
            df = decompose_dc_lmp(case)
            extra_results = df
            extra_info["Reference Energy Price"] = f"${df['Energy'].iloc[0]:.2f} / MWh"
            extra_info["Max Congestion component"] = f"${df['Congestion'].max():.2f} / MWh"
            
    # Export results
    if success:
        if export_format == "excel":
            export_results_excel(case, f"{analysis}_{case_id}.xlsx", analysis, extra_results)
        elif export_format == "csv":
            export_results_csv(case, f"{analysis}_{case_id}", extra_results)
        elif export_format == "docx":
            export_results_docx(case, f"{analysis}_{case_id}.docx", analysis, success, accuracy, extra_results, extra_info)
        else:
            # Print basic report
            if hasattr(case, 'bus') and case.bus is not None and len(case.bus) > 0:
                vm = case.bus[:, VM]
                print(f"\n{analysis.upper()} Success! Voltages: Min={np.min(vm):.4f} pu, Max={np.max(vm):.4f} pu")
            elif hasattr(case, 'bus3p') and case.bus3p is not None and len(case.bus3p) > 0:
                vm = case.bus3p[:, 3:6]
                print(f"\n{analysis.upper()} Success! Phase Voltages: Min={np.min(vm):.4f} pu, Max={np.max(vm):.4f} pu")
    else:
        print(f"Simulation failed or did not converge for case {case_id}")

# 23 Console Entry Points
def cli_acpf(): run_cli_command('acpf', sys.argv[1:])
def cli_gausspf(): run_cli_command('gausspf', sys.argv[1:])
def cli_fdpf(): run_cli_command('fdpf', sys.argv[1:])
def cli_dcpf(): run_cli_command('dcpf', sys.argv[1:])
def cli_hepf(): run_cli_command('hepf', sys.argv[1:])
def cli_cnr(): run_cli_command('cnr', sys.argv[1:])
def cli_pf3p(): run_cli_command('pf3p', sys.argv[1:])
def cli_radial(): run_cli_command('radial', sys.argv[1:])
def cli_dcopf(): run_cli_command('dcopf', sys.argv[1:])
def cli_acopf(): run_cli_command('acopf', sys.argv[1:])
def cli_sdpopf(): run_cli_command('sdpopf', sys.argv[1:])
def cli_uopf(): run_cli_command('uopf', sys.argv[1:])
def cli_scopf(): run_cli_command('scopf', sys.argv[1:])
def cli_opf3p(): run_cli_command('opf3p', sys.argv[1:])
def cli_mpopf(): run_cli_command('mpopf', sys.argv[1:])
def cli_stopf(): run_cli_command('stopf', sys.argv[1:])
def cli_market(): run_cli_command('market', sys.argv[1:])
def cli_varplan(): run_cli_command('varplan', sys.argv[1:])
def cli_contingency(): run_cli_command('contingency', sys.argv[1:])
def cli_se(): run_cli_command('se', sys.argv[1:])
def cli_cpf(): run_cli_command('cpf', sys.argv[1:])
def cli_audit(): run_cli_command('audit', sys.argv[1:])
def cli_lmp(): run_cli_command('lmp', sys.argv[1:])

def main():
    if len(sys.argv) < 3:
        print("\n" + "="*80)
        print(f"{'POWERPYTHON UNIFIED COMMAND LINE INTERFACE':^80}")
        print("="*80)
        print("\nUsage: power-cli <analysis> <case_id> [accuracy] [export_format]")
        print("Or run directly: <analysis> <case_id> [accuracy] [export_format]")
        print("\nAVAILABLE COMMANDS:")
        print(f"  Power Flows : acpf, gausspf, fdpf, dcpf, hepf, cnr, radial, pf3p")
        print(f"  Economics   : dcopf, acopf, sdpopf, uopf, scopf, opf3p, mpopf, stopf, market, lmp")
        print(f"  Grid Tools  : contingency, se, cpf, audit, varplan")
        print("\nExamples:")
        print("  acpf case14 1e-5 excel")
        print("  hepf case9 docx")
        print("  hepf --help docx")
        print("="*80 + "\n")
        return
        
    analysis = sys.argv[1].lower()
    run_cli_command(analysis, sys.argv[2:])

if __name__ == "__main__":
    main()
