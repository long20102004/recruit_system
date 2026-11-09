"""Compatibility CLI: seed generation now uses public snapshots exclusively.

Use ``python -m kb.build_external``. Dataset/curated-input arguments are no longer
accepted; they must never silently reintroduce training-derived knowledge.
"""
from kb.build_external import CATEGORIES, build_external, main

__all__ = ["CATEGORIES", "build_external", "main"]

if __name__ == "__main__":
    main()
