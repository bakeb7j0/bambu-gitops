# Security

This public repo must never contain raw Bambu Studio account exports, private machine configuration, device access codes, spool inventory or secrets.

Contributions may contain **synthetic**, minimized and scrubbed fixtures only. Be especially careful about printer startup/end/filament-change G-code, network addresses, and personal identifiers.

The tools currently operate read-only. They do not call Bambu Cloud or write to connected printers.

The `.gitignore` is defense in depth; before publishing, also review staged diffs and scan for secrets.
