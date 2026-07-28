# actionlint pinned at three versions in two places

**Status:** open — from round 1 tooling review

`.pre-commit-config.yaml` pins actionlint v1.7.11; `.github/ghagen_workflows.py` pins
rhysd/actionlint@v1.7.12 (feeding ci.yml). Local pre-commit and CI lint against different
versions. Single-home the version (renovate covers the workflow pin; align pre-commit).
