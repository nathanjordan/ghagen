# Schema sync is dev-only; Python conformance is test-based

**Status:** accepted

Fetching the upstream GitHub Actions JSON schema, detecting drift, and generating types are
**maintainer/dev-only** concerns, not shipped runtime features. There is one **canonical schema
snapshot** (single copy) consumed by both test suites, TypeScript codegen, and drift detection.
ghagen **hand-writes** its ergonomic models and treats the schema as a **conformance target**, not
a generation source.

## Why

End users writing workflows never fetch schemas or check drift — that is ghagen-maintainer work.
The Python `schema/` package already imported dev-only `httpx`, so it never functioned as a shipped
feature; it is moved to dev tooling. The auto-generated Python models (`datamodel-code-generator`
output) were imported by no production code — only diffed — so drift is detected from the schema
JSON directly and the generated models are deleted, dropping the `datamodel-code-generator`
dependency.

## Considered options

- **Generate-and-use-directly** (Kubernetes clients, AWS CDK L1, Pulumi, cdktf): regenerate models
  from the schema on every change. Works cleanly when you *control or version* the schema — CDK's
  team owns the CloudFormation spec, so it needs no drift detection. ghagen does **not** control
  SchemaStore's schema, which is exactly why it needs drift detection instead.
- **Hand-written models + schema as conformance target** (chosen): far better DX than the hideous
  generated identifiers (`HttpsJsonSchemastoreOrgGithubWorkflowJson`).

## Consequences

The two languages enforce **different** things, by nature — do not "fix" this into false parity:

- **TypeScript**: compile-time author-conformance. Generated types are imported into the
  hand-written models; `tsc` fails if they diverge from the schema. No runtime validation.
- **Python**: runtime user-input validation via Pydantic on the hand-written models. Python lacks
  the structural typing to import a generated type and check a hand-written class against it, so its
  *schema faithfulness* rests on integration tests that validate emitted YAML against the canonical
  snapshot.

Do not re-suggest wiring the generated Python models back in for conformance — it was deliberately
removed. A coarser test-based conformance check (walk schema properties, assert models cover them,
with an explicit allow-list for gaps) is a tracked stretch item and needs no code generation.
