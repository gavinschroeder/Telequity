"""Transform (silver layer): clean each source and roll everything up to the
county grain so it can be joined into the gold star schema.

The whole platform hinges on one shared key: **county_fips** (5-digit string).
Every transform module must emit that column.
"""
