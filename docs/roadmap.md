# Engine roadmap

1. **Discovery** — audit filament, process and printer exports without modifying sources.
2. **Resolution** — reproduce Bambu Studio inheritance, `include` templates and per-extruder variants, with fixture-based tests.
3. **Validation** — flag dangerous changes in machine start/end/change G-code, exclusion zones, geometry, cooling, temperature limits.
4. **Desired-state contract** — versioned generic schema with calibration provenance and observed-state status.
5. **Reconciliation** — compare installed vs desired; initially read-only.
6. **Export/apply** — deterministic generation after round-trip verification; manual backups, review and explicit approval before changing anything.

No R2-3D printer-specific values or user account data belong here.
