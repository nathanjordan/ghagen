"""ghagen — Generate GitHub Actions workflow YAML from Python code."""

from ghagen._dedent import dedent_script as dedent
from ghagen._raw import Raw
from ghagen.app import App
from ghagen.helpers.expressions import expr
from ghagen.lint import LintConfig, Severity, SourceLocation, Violation
from ghagen.models.action import (
    Action,
    ActionInput,
    ActionOutput,
    Branding,
    CompositeRuns,
    DockerRuns,
    NodeRuns,
)
from ghagen.models.common import ExpressionStr
from ghagen.models.container import Container, Service
from ghagen.models.job import Job, Matrix, Strategy
from ghagen.models.permissions import Permissions
from ghagen.models.step import Step
from ghagen.models.trigger import (
    On,
    PRTrigger,
    PushTrigger,
    ScheduleTrigger,
    WorkflowCallTrigger,
    WorkflowDispatchTrigger,
)
from ghagen.models.workflow import Workflow
from ghagen.transforms import SynthContext, Transform

__all__ = [
    "App",
    "Raw",
    "dedent",
    "ExpressionStr",
    "Action",
    "ActionInput",
    "ActionOutput",
    "Branding",
    "CompositeRuns",
    "DockerRuns",
    "NodeRuns",
    "Container",
    "Service",
    "Job",
    "Matrix",
    "Strategy",
    "Permissions",
    "Step",
    "On",
    "PRTrigger",
    "PushTrigger",
    "ScheduleTrigger",
    "WorkflowCallTrigger",
    "WorkflowDispatchTrigger",
    "Workflow",
    # Lint
    "LintConfig",
    "Severity",
    "SourceLocation",
    "Violation",
    # Transforms
    "SynthContext",
    "Transform",
    # Helpers
    "expr",
]
