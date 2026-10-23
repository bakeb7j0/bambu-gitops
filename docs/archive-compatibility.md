# Bambu Studio archive compatibility — milestone 1 (read-only)

> [!CAUTION]
> **DO NOT RUN YOUR PRINTER ON THESE SETTINGS.** Synthetic test fixtures are not certified or even intended as printable settings. A passing parser or CI check never means a machine is safe. Your hotend does not have a `git revert` button.

## Guarantee implemented

The `archive-audit` command can inspect Bambu Studio export ZIP and local system/user TAR/TGZ snapshots **without writing, importing, or applying anything**.

For each JSON object it checks that:

- UTF-8 JSON decodes successfully.
- A canonical JSON serialization can be decoded back to the **same JSON values**, including nested G-code strings, newlines, Unicode, string-encoded numerics, per-variant arrays and explicit `nil` values.
- Aggregate diagnostics include missing names, duplicate names, inherited profiles, multi-value arrays, and embedded G-code-bearing fields.
- No individual profile names, identifiers, G-code bodies, temperature values, or calibration results appear in emitted audit reports.
- Archive members are read in memory only, under per-entry, file-count and aggregate size limits. Parent-path traversals are rejected.

This is **JSON semantic fidelity only**. It does **not** guarantee raw byte-for-byte ZIP fidelity; JSON whitespace, property order and formatting may change. It does **not** prove Bambu Studio recognizes the exported data, honors `include` templates, resolves inheritance identically, or safely operates hardware. No preset export/write-back is implemented.

## CLI

```bash
python -m pip install -e '.[test]'
bambu-gitops archive-audit --kind filament "/path/to/Filament presets.zip"
bambu-gitops archive-audit --kind process "/path/to/Process presets.zip"
bambu-gitops archive-audit --kind printer "/path/to/Printer presets.zip"
bambu-gitops archive-audit --kind system "/path/to/bs-system.tgz"
```

**Note:** `--kind` tags the source snapshot for reporting; the parser does not yet assign a category by interpreting Bambu Studio's complete object model. Installed `system/` snapshots contain non-filament JSON documents, so counts should not be interpreted as number of print presets.

## Offline compatibility observations, 2026-10-23

The following aggregates were obtained from an owner's **local, private** export archives; originals and raw values are not committed.

| Source | JSON documents | Semantic JSON round trips | Inheritance references | Multi-element arrays | G-code-containing documents |
| --- | ---: | ---: | ---: | ---: | ---: |
| Filament preset ZIP | 41 | 41 | 39 | 35 | 2 |
| Process preset ZIP | 2 | 2 | 2 | 2 | 0 |
| Printer preset ZIP | 5 | 5 | 5 | 5 | 5 |
| Installed system TAR.GZ | 2,496 | 2,496 | 2,380 | 1,988 | 1,516 |
| Local user TAR.GZ | 49 | 49 | 47 | 42 | 2 |

System and user TAR snapshots include supporting configuration documents, not only active printer/process/filament presets. These figures validate only parse/re-encode fidelity across the observed files; they do not certify imported behavior.

## CI coverage

Synthetic tests generate ZIP and TAR files at test time and check:

- G-code text including multi-line strings and Unicode
- Distinct Standard/High Flow values and the literal `nil` placeholder
- Duplicate names without disclosing source names
- Missing names, malformed JSON, non-object JSON
- Malicious `../` paths and oversized entries
- Valid empty archives rejected as an export source
- Normal ZIP and compressed TAR paths

These checks are part of the Python 3.10/3.12 engine CI test matrix. The independently maintained public example repo stays **schema-only** and intentionally offers no importable printer configurations.

## Next compatibility gates (not yet implemented)

1. **Semantic Bambu preset model**: classify installed system/user and exported filament/process/printer definitions; resolve parent chains, `include` templates, variants, name collisions and Bambu Studio format/version-dependent behavior.
2. **Golden effective-value fixtures**: synthetic, independently reviewed expected values for each tricky inheritance case; profile equivalence should mean more than identical JSON.
3. **Import/export acceptance testing**: an isolated installed Bambu Studio executable or trusted reference implementation must accept the generated preset and return semantically equivalent settings before we claim a real round trip. Keep tests detached from any physical printer.
4. **Safety gate**: detect and require explicit review for changes to machine G-code, excluded bed geometry, hotend/nozzle identity, thermal limits and motion settings.
5. **Reconciliation**: calibration saved/assigned/applied status remains distinct from filament profiles; do not infer K from a user preset export.

**Never deploy merely because a test passes. The molten-plastic production environment has no staging cluster.**
