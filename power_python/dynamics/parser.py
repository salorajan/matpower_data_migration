# PowerPython Dynamics
# Copyright (c) 2026 PowerPython contributors
# Licensed under the 3-clause BSD License (see LICENSE file for details).

"""
Parser for PSS/E .dyr (Dynamics Data) files.
Reads plain-text dynamic model parameters and maps them to generators.
"""

import re

class DYRParser:
    """Object-oriented parser for PSS/E .dyr files."""
    
    def __init__(self):
        self.parsed_records = []

    def parse_file(self, file_path):
        """
        Parses a .dyr file and stores records.
        Returns a list of parsed dynamic model dictionaries.
        """
        self.parsed_records = []
        
        with open(file_path, 'r') as f:
            content = f.read()

        # Remove comments starting with //
        content = re.sub(r'//.*', '', content)
        
        # Remove comments starting with COM
        content = re.sub(r'(?i)COM.*', '', content)
        
        # PSS/E dyr records are separated by '/'
        # Split by '/' to get individual model records
        raw_records = content.split('/')
        
        for raw_rec in raw_records:
            raw_rec = raw_rec.strip()
            if not raw_rec:
                continue
                
            # Replace commas and tab characters with spaces, then split by whitespace
            raw_rec = raw_rec.replace(',', ' ').replace('\t', ' ')
            tokens = []
            
            # Use regex to find single-quoted strings or non-whitespace words
            # This handles strings with spaces like 'GENCLS' or '1 '
            pattern = r"'([^']*)'|(\S+)"
            matches = re.findall(pattern, raw_rec)
            
            for m in matches:
                # m is a tuple (quoted_val, unquoted_val)
                val = m[0] if m[0] else m[1]
                tokens.append(val.strip())
                
            if len(tokens) < 3:
                continue
                
            try:
                bus_id = int(tokens[0])
                model_name = tokens[1].upper()
                gen_id = tokens[2].strip()
                
                # Remaining tokens are parameters
                params = []
                for t in tokens[3:]:
                    # Handle cases where parameters might contain non-numeric placeholders
                    try:
                        params.append(float(t))
                    except ValueError:
                        # Skip or default to 0.0
                        params.append(0.0)
                        
                record = {
                    'bus_id': bus_id,
                    'model_name': model_name,
                    'gen_id': gen_id,
                    'params': params
                }
                self.parsed_records.append(record)
                
            except Exception as e:
                print(f"Warning: Failed to parse record line: '{raw_rec}'. Error: {e}")
                
        return self.parsed_records

    def get_parsed_records(self):
        return self.parsed_records
