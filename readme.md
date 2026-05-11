\# MATPOWER Data Migration Project (Stage 1)



\## Overview

This repository provides a modernized, accessible version of the standard MATPOWER power system test cases. The goal is to remove the "Matlab/Octave Hurdle" for power system researchers working in \*\*Python\*\*, \*\*Rust\*\*, and \*\*AI/Machine Learning\*\*.



The original `.m` files from the MATPOWER project have been converted into three high-accessibility formats, preserving all original numerical data and dimensions.



\## Data Formats

\- \*\*Excel (.xlsx)\*\*: Human-readable with standard IEEE headers. Each case contains separate sheets for `Bus`, `Generator`, `Branch`, and `GenCost`.

\- \*\*JSON (.json)\*\*: Programmatic-friendly nested structures. Ideal for web-based tools and rapid prototyping in Python.

\- \*\*Parquet (.parquet)\*\*: High-performance columnar storage. Optimized for Large-Scale Power System Analysis and Machine Learning dataloaders.



\## Project Structure

\- `outputs/excel/`: Validated Excel workbooks with column descriptors.

\- `outputs/json/`: Standardized JSON objects.

\- `outputs/parquet/`: Compressed binary data for high-speed I/O.



\## Accessibility for Visually Impaired Researchers

The Excel files are structured with distinct sheet landmarks and standard headers, making them compatible with Screen Readers (NVDA/JAWS) for quick navigation between system components (e.g., jumping from Bus data to Branch data).



\## Usage in Python (Example)

```python

import pandas as pd



\# Load a case instantly without Matlab

bus\_data = pd.read\_parquet('outputs/parquet/case118.parquet')

print(bus\_data.head())

