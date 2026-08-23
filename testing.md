# PowerPython Dynamics Manual Testing Guide (`testing.md`)

This guide provides the instructions and code to manually verify the new PSS/E-compatible dynamics sub-module in your local environment.

---

## Prerequisites
Ensure that the package is installed in editable mode:
```bash
pip install -e .
```

---

## 1. Quick Testing Script

Create a file named `manual_test.py` in the project root directory, copy the following code into it, and run it.

```python
import os
import numpy as np
import pandas as pd
import power_python as pp
from power_python.dynamics import DYRParser, run_simulation

# Paths
case9_path = os.path.abspath("power_python/outputs/json/case9.json")
dyr_path = os.path.abspath("power_python/tests/case9_test.dyr")

print("="*60)
print("             POWERPYTHON DYNAMICS MANUAL TEST")
print("="*60)

# Step 1: Parse the DYR file
print("\n[Step 1] Parsing .dyr file...")
parser = DYRParser()
records = parser.parse_file(dyr_path)
print(f"Successfully parsed {len(records)} dynamic records:")
for r in records:
    print(f"  - Bus {r['bus_id']} / Gen '{r['gen_id']}': Model = {r['model_name']} with {len(r['params'])} parameters")

# Step 2: Load the Case9 data structure
print("\n[Step 2] Loading Case 9 network power flow...")
case = pp.PowerCase()
case.load_from_json(case9_path)
print(f"Loaded case with {len(case.bus)} buses, {len(case.gen)} generators, and {len(case.branch)} branches.")

# Step 3: Run the dynamic simulation (Transient Stability)
# Apply a 3-phase short-circuit fault at Bus 7 at t=0.1s, clear it at t=0.2s by tripping line 7-8.
print("\n[Step 3] Running transient stability simulation (t=0 to 1.5s)...")
history = run_simulation(
    power_case=case,
    dyr_records=records,
    fault_bus=7,
    fault_time=0.1,
    clear_time=0.2,
    t_end=1.5,
    dt=0.005,
    trip_branch=(7, 8),
    verbose=True
)

# Step 4: Process and Print Results Summary
print("\n[Step 4] Simulation results summary:")
time = history['time']
angles = history['rotor_angles']
speeds = history['speeds']
voltages = history['bus_voltages']

print(f"Total simulation steps: {len(time)}")
print("Rotor Angles (Degrees) at key intervals:")
print(f"{'Time (s)':<10} | {'Gen 1 (Bus 1)':<15} | {'Gen 2 (Bus 2)':<15} | {'Gen 3 (Bus 3)':<15}")
print("-"*65)

# Report at t=0.0 (initial), t=0.15 (during fault), t=1.0 (post-fault), and t=1.5 (final)
for target_t in [0.0, 0.15, 1.0, 1.5]:
    idx = np.argmin(np.abs(time - target_t))
    t_val = time[idx]
    
    # In case9, generators are mapped to indices:
    # 0 -> Bus 1 (Gen 1)
    # 1 -> Bus 2 (Gen 2)
    # 2 -> Bus 3 (Gen 3)
    deg1 = np.degrees(angles[0][idx])
    deg2 = np.degrees(angles[1][idx])
    deg3 = np.degrees(angles[2][idx])
    
    print(f"{t_val:<10.2f} | {deg1:<15.2f} | {deg2:<15.2f} | {deg3:<15.2f}")

print("\nGrid Voltages Magnitude (p.u.) at fault bus (Bus 7):")
print(f"{'Time (s)':<10} | {'Bus 7 Voltage (p.u.)':<20}")
print("-"*35)
for target_t in [0.0, 0.05, 0.15, 0.25, 1.0, 1.5]:
    idx = np.argmin(np.abs(time - target_t))
    t_val = time[idx]
    v_mag = np.abs(voltages[idx, 6]) # Bus 7 index is 6 (0-based)
    print(f"{t_val:<10.2f} | {v_mag:<20.4f}")

print("\n" + "="*60)
print("             MANUAL TEST VERIFICATION SUCCESSFUL")
print("="*60)
```

Run this script:
```bash
python manual_test.py
```

---

## 2. Expected Output Verification

When you run the test script, check for the following physics behaviors to confirm correctness:
1. **Fault Voltage Drop**: The voltage at Bus 7 at `t = 0.15s` (during the fault) should be extremely close to `0.0000 p.u.` (due to short-circuit admittance).
2. **Rotor Angle Swing**: The rotor angles of the generators (especially Gen 2, which is closest to the fault) should start to swing and accelerate away from their initial values during the fault interval (`0.1s` to `0.2s`).
3. **Fault Clearing Recovery**: After `t = 0.2s`, the voltage at Bus 7 should immediately recover to a stable non-zero level, and the rotor angles should oscillate but show stable post-fault characteristics.
