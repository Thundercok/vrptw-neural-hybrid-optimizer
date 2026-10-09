# Research History

The Git tag `research-history-before-cleanup` (`d1a48ecc`) preserves historical
tracked experiments, elite-plan caches, old documents/posters, and duplicate
Overleaf sources. `history-manifest.json` lists the 5,225 removed files with
their original paths, byte counts, and SHA-256 checksums. Their contents were
checksum-verified before loose copies were removed.

The current manuscript, datasets, solver models, and publication-audit CSVs
remain directly accessible. History uses Git's existing objects, avoiding a
second large binary copy of material already on GitHub.

Export a historical folder without changing the active working tree:

```sh
git archive --format=zip --output=/tmp/vrptw-history.zip research-history-before-cleanup results elite_plans docs/legacy_archive posters/archive
```

`local-experiments.zip` preserves 4,428 previously ignored local output files.
It includes `archive/local-manifest.json` with the same checksum metadata.
Inspect it or restore into a separate directory:

```sh
python -m zipfile -l archive/local-experiments.zip
python -m zipfile -e archive/local-experiments.zip /tmp/vrptw-local-history
```

GNN retraining may need the historical elite plans. Keep restored caches out
of independent cold-start benchmarks. Earlier source versions remain in Git
history, while `main` is the only development branch.
