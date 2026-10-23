# Offline coding workspace

`--dry-run` copies this directory instead of cloning tenacity, then copies
`coding_overlay/` on top. A real run clones `coding_repo.url` at
`coding_repo.commit` and applies the same overlay. Tenacity is not vendored.
