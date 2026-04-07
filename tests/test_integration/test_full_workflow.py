"""Integration tests: build workflows, generate YAML, validate against schema, round-trip."""

from __future__ import annotations

from typing import Any

from ruamel.yaml.comments import CommentedMap

from ghagen import (
    Container,
    Job,
    Matrix,
    On,
    Permissions,
    PRTrigger,
    PushTrigger,
    Raw,
    ScheduleTrigger,
    Service,
    Step,
    Strategy,
    Workflow,
    WorkflowCallTrigger,
    WorkflowDispatchTrigger,
    checkout,
)
from ghagen.models.common import PermissionLevel
from ghagen.models.job import Concurrency, Environment
from ghagen.models.trigger import (
    WorkflowCallInput,
    WorkflowCallOutput,
    WorkflowCallSecret,
    WorkflowDispatchInput,
)

from .conftest import validate_and_roundtrip


def test_simple_ci(workflow_schema: dict[str, Any]):
    """Simple CI workflow: push + PR triggers, single job, checkout + test steps."""
    wf = Workflow(
        name="CI",
        on=On(
            push=PushTrigger(branches=["main"]),
            pull_request=PRTrigger(branches=["main"]),
        ),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(name="Run tests", run="echo 'tests pass'"),
                ],
            ),
        },
    )

    yaml_str = wf.to_yaml(include_header=False)
    data = validate_and_roundtrip(yaml_str, workflow_schema)

    assert data["name"] == "CI"
    assert "push" in data["on"]
    assert "pull_request" in data["on"]
    assert data["jobs"]["test"]["runs-on"] == "ubuntu-latest"
    assert len(data["jobs"]["test"]["steps"]) == 2
    assert data["jobs"]["test"]["steps"][0]["uses"] == "actions/checkout@v4"
    assert data["jobs"]["test"]["steps"][1]["run"] == "echo 'tests pass'"


def test_matrix_build(workflow_schema: dict[str, Any]):
    """Matrix build: multi-version Python, multi-OS, with exclude."""
    wf = Workflow(
        name="Matrix CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on=Raw("${{ matrix.os }}"),
                strategy=Strategy(
                    matrix=Matrix(
                        extras={
                            "python-version": ["3.11", "3.12", "3.13"],
                            "os": ["ubuntu-latest", "macos-latest"],
                        },
                        exclude=[
                            {"os": "macos-latest", "python-version": "3.11"},
                        ],
                    ),
                    fail_fast=False,
                ),
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(
                        uses="actions/setup-python@v5",
                        with_={"python-version": "${{ matrix.python-version }}"},
                    ),
                    Step(name="Test", run="python -m pytest"),
                ],
            ),
        },
    )

    yaml_str = wf.to_yaml(include_header=False)
    data = validate_and_roundtrip(yaml_str, workflow_schema)

    matrix = data["jobs"]["test"]["strategy"]["matrix"]
    assert "3.11" in matrix["python-version"]
    assert "3.12" in matrix["python-version"]
    assert "3.13" in matrix["python-version"]
    assert "ubuntu-latest" in matrix["os"]
    assert len(matrix["exclude"]) == 1
    assert data["jobs"]["test"]["strategy"]["fail-fast"] is False


def test_reusable_workflow_call(workflow_schema: dict[str, Any]):
    """Reusable workflow call: job with `uses` field (no steps)."""
    wf = Workflow(
        name="Deploy",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "deploy": Job(
                uses="octo-org/example-repo/.github/workflows/reusable.yml@main",
                with_={"deploy_target": "production"},
                secrets={"envPAT": "${{ secrets.envPAT }}"},
            ),
        },
    )

    yaml_str = wf.to_yaml(include_header=False)
    data = validate_and_roundtrip(yaml_str, workflow_schema)

    job = data["jobs"]["deploy"]
    assert job["uses"] == "octo-org/example-repo/.github/workflows/reusable.yml@main"
    assert job["with"]["deploy_target"] == "production"
    assert job["secrets"]["envPAT"] == "${{ secrets.envPAT }}"
    assert "steps" not in job


def test_containers_and_services(workflow_schema: dict[str, Any]):
    """Workflow with job containers and services."""
    wf = Workflow(
        name="Container CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                container=Container(
                    image="node:20",
                    env={"NODE_ENV": "test"},
                    ports=[8080],
                    volumes=["/tmp/data:/data"],
                ),
                services={
                    "postgres": Service(
                        image="postgres:16",
                        env={
                            "POSTGRES_PASSWORD": "postgres",
                            "POSTGRES_DB": "test",
                        },
                        ports=[5432],
                    ),
                    "redis": Service(image="redis:7"),
                },
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(name="Test", run="npm test"),
                ],
            ),
        },
    )

    yaml_str = wf.to_yaml(include_header=False)
    data = validate_and_roundtrip(yaml_str, workflow_schema)

    job = data["jobs"]["test"]
    assert job["container"]["image"] == "node:20"
    assert job["container"]["env"]["NODE_ENV"] == "test"
    assert job["services"]["postgres"]["image"] == "postgres:16"
    assert job["services"]["redis"]["image"] == "redis:7"


def test_all_permissions(workflow_schema: dict[str, Any]):
    """Workflow with all 13 permission scopes set."""
    wf = Workflow(
        name="Full Permissions",
        on=On(push=PushTrigger(branches=["main"])),
        permissions=Permissions(
            actions=PermissionLevel.READ,
            checks=PermissionLevel.WRITE,
            contents=PermissionLevel.READ,
            deployments=PermissionLevel.WRITE,
            discussions=PermissionLevel.READ,
            id_token=PermissionLevel.WRITE,
            issues=PermissionLevel.READ,
            packages=PermissionLevel.WRITE,
            pages=PermissionLevel.READ,
            pull_requests=PermissionLevel.WRITE,
            repository_projects=PermissionLevel.READ,
            security_events=PermissionLevel.WRITE,
            statuses=PermissionLevel.READ,
        ),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@v4")],
            ),
        },
    )

    yaml_str = wf.to_yaml(include_header=False)
    data = validate_and_roundtrip(yaml_str, workflow_schema)

    perms = data["permissions"]
    assert perms["actions"] == "read"
    assert perms["checks"] == "write"
    assert perms["id-token"] == "write"
    assert perms["pull-requests"] == "write"
    assert perms["repository-projects"] == "read"
    assert perms["security-events"] == "write"
    assert len(perms) == 13


def test_complex_triggers(workflow_schema: dict[str, Any]):
    """Complex triggers: schedule, workflow_dispatch with inputs, workflow_call."""
    wf = Workflow(
        name="Complex Triggers",
        on=On(
            schedule=[ScheduleTrigger(cron="0 9 * * 1")],
            workflow_dispatch=WorkflowDispatchTrigger(
                inputs={
                    "environment": WorkflowDispatchInput(
                        description="Target environment",
                        required=True,
                        default="staging",
                        type="choice",
                        options=["staging", "production"],
                    ),
                    "log_level": WorkflowDispatchInput(
                        description="Log verbosity level",
                        required=False,
                        default="info",
                        type="choice",
                        options=["debug", "info", "warn", "error"],
                    ),
                },
            ),
            workflow_call=WorkflowCallTrigger(
                inputs={
                    "tag": WorkflowCallInput(
                        description="Release tag",
                        required=True,
                        type="string",
                    ),
                },
                outputs={
                    "artifact_url": WorkflowCallOutput(
                        description="URL of the built artifact",
                        value="${{ jobs.build.outputs.url }}",
                    ),
                },
                secrets={
                    "deploy_key": WorkflowCallSecret(
                        description="Deployment SSH key",
                        required=True,
                    ),
                },
            ),
        ),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@v4")],
            ),
        },
    )

    yaml_str = wf.to_yaml(include_header=False)
    data = validate_and_roundtrip(yaml_str, workflow_schema)

    on = data["on"]
    # Schedule
    assert on["schedule"][0]["cron"] == "0 9 * * 1"
    # workflow_dispatch
    dispatch_inputs = on["workflow_dispatch"]["inputs"]
    assert dispatch_inputs["environment"]["type"] == "choice"
    assert dispatch_inputs["environment"]["options"] == ["staging", "production"]
    assert dispatch_inputs["log_level"]["type"] == "choice"
    assert dispatch_inputs["log_level"]["options"] == ["debug", "info", "warn", "error"]
    # workflow_call
    call = on["workflow_call"]
    assert call["inputs"]["tag"]["type"] == "string"
    assert call["outputs"]["artifact_url"]["value"] == "${{ jobs.build.outputs.url }}"
    assert call["secrets"]["deploy_key"]["required"] is True


def test_escape_hatches():
    """Escape hatches: Raw, extras, post_process, CommentedMap passthrough.

    Schema validation is skipped because extras may inject keys that violate
    the schema's additionalProperties: false constraint.
    """
    # 1. Raw: bypass type constraints
    raw_step = Step(uses="actions/checkout@v4", shell=Raw("custom-shell"))

    # 2. extras: inject arbitrary keys
    job_with_extras = Job(
        runs_on="ubuntu-latest",
        steps=[raw_step],
        extras={"custom-field": "custom-value"},
    )

    # 3. post_process: modify CommentedMap before emission
    def add_annotation(cm: CommentedMap) -> None:
        cm["x-generated"] = True

    wf = Workflow(
        name="Escape Hatches",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "build": job_with_extras,
        },
        post_process=add_annotation,
    )

    yaml_str = wf.to_yaml(include_header=False)

    # Verify all escape hatches produced output
    assert "custom-shell" in yaml_str  # Raw
    assert "custom-field: custom-value" in yaml_str  # extras
    assert "x-generated: true" in yaml_str  # post_process

    # 4. CommentedMap passthrough: raw YAML structure in place of typed model
    cm_job = CommentedMap()
    cm_job["runs-on"] = "ubuntu-latest"
    cm_job["steps"] = [{"uses": "actions/checkout@v4"}]

    wf2 = Workflow(
        name="CM Passthrough",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={"raw-job": cm_job},
    )

    yaml_str2 = wf2.to_yaml(include_header=False)
    assert "runs-on: ubuntu-latest" in yaml_str2
    assert "actions/checkout@v4" in yaml_str2
