# Working in Foundation Robotics

Read [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), and the relevant
contract before editing. Use [SUPPORT.md](SUPPORT.md) for help and
[SECURITY.md](SECURITY.md) for sensitive reports.

## Scope and contracts

This is a Python 3.11+ source-tree project using only the standard library.
Run the documented workflow from the repository root; no package installation
is needed.

- `foundation_robotics/` contains pure motion checks over caller-supplied values:
  scale timing, gait, balance, kinematics, mechanisms, and squash and stretch.
- `foundation_robotics/data/` holds defaults and calibration data; preserve their
  provenance and qualification in results.
- `foundation_robotics_bridge/` provides the line-delimited stdio JSON-RPC bridge;
  `schemas.py` defines the tool inventory and input/output schemas.
- `tests/` contains unit and bridge tests using Python's `unittest` runner.
- `docs/` holds requirements, architecture, interface control, and verification.

Preserve read-only observations: a verdict is not an acceptance decision, formal
proof, or control action. Keep Evidence and the input hash in tool receipts,
including tool errors. Do not turn uncalibrated thresholds or caller-supplied
judgments into established facts.

Read [the architecture](docs/architecture/architecture.md) and
[the interface contract](docs/icd/icd-cstack.md) for bridge changes. Preserve
bounded input validation, schema-defined numeric representations, and execution
without network access or caller-controlled paths. The bridge starts with
`python -B -m foundation_robotics_bridge`; it is JSON-RPC, not MCP.
Every new requirement needs a row in
[the verification matrix](docs/verification/verification-matrix.md).

## Verification

Run from the repository root after every change, in this order:

```sh
python -B tools/build_manifest.py
python -B -m unittest discover -s tests -t .
python -B -O -m unittest discover -s tests -t .
```

CI uses Python 3.12 and runs both test modes, Gitleaks, and manifest regeneration
followed by `git diff --exit-code SOURCE-MANIFEST.json`.
See [the workflow](.github/workflows/ci.yml). Report the revision, Python version,
commands, results, and any checks not run. Do not claim missing or failed checks
passed, or treat passing tests as domain acceptance.

## Source and release boundaries

[SOURCE-MANIFEST.json](SOURCE-MANIFEST.json) records SHA-256 hashes of shipped
files. Regenerate it with [the manifest tool](tools/build_manifest.py) after edits,
including documentation and this file; do not hand-edit hashes. The tool scans
the working tree, excluding `.git`, bytecode, and the manifest itself, so keep
temporary artifacts and local environments outside the repository.

The manifest tool prints the file count, manifest SHA-256, and canonical tool
inventory SHA-256. Shipped-file changes alter the manifest pin; consumers repin
in the same change that updates their vendored copy. Follow
[configuration management](docs/configuration/configuration-management.md).
Releases and tags require owner approval.

Keep one concern per pull request, about 400 changed lines or less. Open an issue
first for work beyond a small fix. Use Conventional Commits with an imperative
`type(scope): summary` of at most 72 characters and an `Assisted-by: <tool>`
trailer for AI-written changes.

Preserve GPL-3.0-only terms and [NOTICE.md](NOTICE.md). Keep secrets out of commits.
Put rationale in `docs/`; add no code comments. Never edit expected test results
or weaken checks to obtain a pass. If behavior changes, follow CONTRIBUTING.md's
regeneration and PR disclosure rule for generated results.
