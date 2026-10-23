# Contract & Conformance, milestone 1

Version **0.1** is intentionally small and read-only, with **no compatibility promise for actual Bambu Studio import/export yet**.

## Contracts

- `schemas/config-v0.1.schema.json`: hardware identity, references to active printer/process/filament profiles, optional calibration evidence.
- `schemas/profile-v0.1.schema.json`: typed profile with stable ID, optional parent, and explicitly reviewed settings.
- Values in these schemas describe **desired configuration**, not raw Bambu Studio preset syntax.

## Enforcement

The engine is a warning/error reporter: an **error** produces a failing exit code; a **warning** identifies a condition requiring review but does not imply automatic rejection. Neither category applies changes.

- Unknown profile IDs and parents, cross-kind inheritance, cycles, duplicated IDs, incompatible active nozzle sizes → errors.
- Unvalidated material volumetric limit, machine-sensitive overrides (G-code, exclusion area, geometry), mismatched calibration nozzle, status claiming applied without verifiable evidence → warnings.

## Test boundary

The `fixtures/example/` reference instance and all negative test mutations are **synthetic**; no real printer, Bambu account, hardware endpoint, cloud account or Filament Manager is accessed.

### Execute locally

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest -q
bambu-gitops validate fixtures/example
```

## Not yet implemented

Exact Bambu Studio `include` semantics; safe round-trip with vendor/system profile definitions; versioned compatibility matrix; independent printer-side K-factor readback; physical-spool inventory export; export/apply controls. These need additional fixtures and validation against Bambu Studio itself before claiming production readiness.
