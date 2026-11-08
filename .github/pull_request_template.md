<!-- Peer-review record, SWEHB 5.03 tailored. NPR SWE-087, 088, 089. -->

## Change

<!-- What and why. Link issues: Fixes #, Refs #. -->

## Requirements, design and interface impact

- Requirements added/changed/deleted:
- SDD / ICD / data dictionary updated: yes / no / not needed
- Verification matrix updated: yes / not needed
- `SOURCE-MANIFEST.json` regenerated (`python -B tools/build_manifest.py`): yes / not needed (only `.github/` changed)

## Verification

<!-- Commands run and result, at the head commit. Identical to CI where possible:
python -B -m unittest discover -s tests -t .
python -B -O -m unittest discover -s tests -t .
python -B tools/build_manifest.py && git diff --exit-code SOURCE-MANIFEST.json -->

## Peer review record

- Reviewers: <human approver>, <agent reviewers> (agent review is not independent)
- Review type: code / docs / requirements / design
- Findings: <count by severity; list or link resolved threads>
- Outcome: approved / changes requested / re-review

## Checklist

- [ ] Assisted-by trailer on AI-written commits
- [ ] No code comments
- [ ] No expected test results edited
- [ ] One concern, about 400 changed lines or fewer
- [ ] Docs whose derivation paths this PR touches are updated or confirmed still accurate
- [ ] For docs PRs: the family documentation checklist is pasted below and ticked
