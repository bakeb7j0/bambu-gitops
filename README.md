# bambu-gitops

> [!CAUTION]
> **🛑 DON'T RUN YOUR PRINTER ON THE EXAMPLE SETTINGS.**
> The [public example configuration](https://github.com/bakeb7j0/bambu-gitops-example) and this repository's test fixtures are **synthetic software-test data**, not calibrated printer recipes. **Do not import, deploy or copy them into Bambu Studio or hardware.** Passing CI proves software checks passed—not that your printer is safe. Your hotend doesn't support `git revert`.

Public **MIT-licensed**, read-only GitOps-oriented tooling for Bambu Studio configuration management.

The engine is generic. It contains **no R2-3D-specific data, private printer configurations, actual spool inventory, device credentials, or account information**.

## Contract and Conformance — v0.1 (experimental)

The first versioned desired-state contract is in [schemas/](schemas/), with synthetic fixtures and automated positive/negative tests. It models:

- Hardware identity and declared limits, with printer/process/filament profile references
- Stable profile identity, inheritance, and explicit settings
- Calibration evidence with **measured → saved → assigned → verified applied** state
- Diagnostic severity: schema/reference/nozzle errors vs explicit safety-review warnings

Run locally:

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest -q
bambu-gitops validate fixtures/example
```

The CLI prints machine-readable JSON findings and returns a nonzero exit status for **errors**. Warnings are reported without claiming that anything is safe to deploy.

Current [conformance documentation](docs/conformance.md) explains the contract and its limitations.

## Legacy snapshot investigation tools

```bash
python3 tools/audit.py /path/to/filament-export.tgz --json
python3 tools/resolve.py --user /path/to/user-export.tgz --system /path/to/system-export.tgz --output /tmp/effective.json
```

These remain **read-only analytical prototypes**. Bambu Studio `include` templates, all Standard/High Flow inheritance rules, hardware-specific compatibility, and round-trip exporter semantics are not yet validated.

## CI and adoption

CI validates the synthetic reference instance against JSON Schema, runs negative cases, checks reviewed golden output, and exercises the test suite on Python 3.10 and 3.12.

A standalone [`bambu-gitops-example` reference repository](https://github.com/bakeb7j0/bambu-gitops-example) is planned to exercise the same contract as an independent consumer. The engine will pin that example revision in its integration tests after the repository is created.

**Live configuration changes are intentionally unsupported.** Device-side K-factor, AMS loading, Bambu Cloud Filament Manager and per-project slicer state are independent observed systems; no automatic Git reconciliation or write-back exists yet.

## License and safety

[MIT License](LICENSE). See [SECURITY.md](SECURITY.md) and [development roadmap](docs/roadmap.md).
