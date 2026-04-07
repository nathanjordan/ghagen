# Helpers

Convenience utilities for building workflows: step factory functions for common actions, an expression builder for GitHub Actions expressions, and escape hatch types for raw YAML injection.

## Step Factories

Factory functions that return pre-configured `Step` instances for widely-used GitHub Actions.

::: ghagen.helpers.steps.checkout

::: ghagen.helpers.steps.setup_python

::: ghagen.helpers.steps.setup_node

::: ghagen.helpers.steps.setup_uv

::: ghagen.helpers.steps.cache

::: ghagen.helpers.steps.upload_artifact

::: ghagen.helpers.steps.download_artifact

## Expression Builder

The expression builder provides a Pythonic interface for constructing GitHub Actions `${{ }}` expressions. Import the singleton `expr` object rather than the class directly:

```python
from ghagen.helpers.expressions import expr

expr.github.ref        # "${{ github.ref }}"
expr.secrets.API_KEY   # "${{ secrets.API_KEY }}"
```

::: ghagen.helpers.expressions._ExprBuilder
    options:
      show_root_heading: true

## Escape Hatch Types

Types for bypassing ghagen's model validation when you need to emit arbitrary YAML or literal expression strings.

### Raw

::: ghagen._raw.Raw

### ExpressionStr

::: ghagen.models.common.ExpressionStr
