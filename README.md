# bambu-gitops

Reusable, **read-only initially**, GitOps-oriented tooling for Bambu Studio configurations.

## Boundaries

The engine provides generic discovery, auditing, inheritance resolution, validation, and eventual controlled export/reconciliation. It contains **no R2-3D-specific profiles or configuration**, physical spool inventories, account data, or device secrets.

Printer-specific desired state belongs in a separate, private configuration repository.

## Current capabilities

- `tools/audit.py`: local-only filament preset audit (names, parent references, potential duplicates).
- `tools/resolve.py`: provisional inheritance resolution, including per-variant `nil` overrides.
- `tests/`: inheritance smoke tests run in CI.

### Usage (local-only snapshot inputs)

```bash
python3 tools/audit.py /path/to/filaments.tgz --json
python3 tools/resolve.py --user /path/to/filaments.tgz --system /path/to/bs-system.tgz --output /tmp/effective.json
python3 -m unittest discover -s tests -v
```

**Important:** This resolver is a prototype, **not** a guaranteed reproduction of Bambu Studio's `include` templates, variant/compatibility semantics, or device-side Flow Dynamics records. Do not use it to generate or apply live printer profiles.

## Safety

- Never commit raw full Bambu Studio configuration directories or unreviewed source archives.
- Never automatically change startup/end/filament-change G-code, exclusion zones, thermal limits or geometry.
- K-factor calibration has distinct stages: measured → saved → assigned → verified applied.
- The engine does not synchronize inventory or AMS state to Git.

See [engine roadmap](docs/roadmap.md) and [schema contract](schemas/README.md).

## License

No open-source license has been selected yet. Public visibility alone **does not grant reuse/distribution rights**. A license will be chosen explicitly before advertising this project as a reusable third-party tool.
