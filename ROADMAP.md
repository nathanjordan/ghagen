# ghagen Roadmap

These items are not gated on the initial release but represent the longer-term vision.

### VSCode Extension

A language server / extension that provides:
- Stale file detection (indicator when generated YAML is out of sync with Python source)
- Action version resolution (convert `actions/checkout@v4` to `actions/checkout@<commit-sha>` with a
  preserving comment)
- Go-to-definition from generated YAML back to the Python source
- IntelliSense for ghagen Python files (model field completion, step factory signatures)

### Import from YAML (Migration Tool)

A `ghagen import` command that parses an existing `.github/workflows/*.yml` file and generates the
equivalent ghagen Python code. Useful for migrating existing repos to ghagen.
