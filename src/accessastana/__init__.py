"""AccessAstana: climate-adjusted accessibility of social infrastructure.

Modular monolith. Sub-packages are modules with one-way dependencies:
    ingestion -> db            (writes)
    analysis  -> (pure numpy/pandas; no DB imports)
    api       -> analysis, db  (reads + on-demand recomputation)
"""

__version__ = "0.1.0"
