# Removed from version control

Three groups of files were tracked in git but should not have been. They were
untracked (`git rm --cached`) and added to `.gitignore`. Nothing was deleted
from anyone's working copy by that change.

## `apps/web/` — removed

The directory contained **3617 files of `node_modules` and 39 files of `.next`
build cache, and zero source files**. There was no `package.json`, no
`app/page.tsx`, no component — only committed dependencies and build output of an
application whose source is not in this repository.

It also carried a macOS-only binary (`next-swc.darwin-arm64.node`) through Git
LFS, via the `.gitattributes` that was removed with it.

If the web UI is revived, start it fresh; there is nothing here to build on. Per
`reports/evaluation/casp15_expanded_digest.md`, the project's own conclusion was
that the next work is scoring, not UI.

## `RhoFold/` — removed

A 39 MB vendored checkout of upstream RhoFold, including its `build/lib/`
directory and a nested git object pack (`RhoFold_git_internal_objects/`).

**Nothing in this codebase imports it.** The only occurrence of the string
anywhere outside that directory is a filename-prefix comparison used to label a
candidate's generator:

```python
# riborank/structure.py
"rhofold": "rhofold",
```

To use the real thing, clone it beside this repository rather than inside it:

```bash
git clone https://github.com/ml4bio/RhoFold.git ../RhoFold
```

## `data/casp15_rna/{candidates,downloads,natives}` — removed

674 MB, fully reproducible from two scripts already in the repository:

```bash
python scripts/download_casp15_predictions.py   # candidates + downloads
python scripts/download_casp15_natives.py       # natives + native_map.csv
```

`data/casp15_rna/native_map.csv` is small and stays tracked so the target-to-PDB
mapping survives even when the structures are absent.

The smaller benchmark sets (`data/real`, `data/processed`, `data/demo`,
`data/external`, `data/final`, `data/jobs`, ~51 MB total) have no download script
and remain tracked.

## History

Untracking stops these files growing the repository further; it does **not**
remove them from past commits, so a fresh `git clone` still transfers the old
blobs. Shrinking the clone requires rewriting history, which changes every commit
hash and breaks existing checkouts. That is a deliberate, coordinated operation
and has not been done:

```bash
# Only with every collaborator's agreement, and after a backup.
git filter-repo --invert-paths \
  --path apps --path RhoFold --path RhoFold_git_internal_objects \
  --path data/casp15_rna/candidates \
  --path data/casp15_rna/downloads \
  --path data/casp15_rna/natives
```
