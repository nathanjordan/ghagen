import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parse } from "yaml";
import Ajv from "ajv";
import addFormats from "ajv-formats";

export const FIXTURES_DIR = resolve(
  import.meta.dirname,
  "../../../../fixtures/expected",
);

export const SCHEMA_DIR = resolve(
  import.meta.dirname,
  "../../../../fixtures/schema",
);

export function loadFixture(name: string): string {
  return readFileSync(resolve(FIXTURES_DIR, name), "utf-8");
}

export function parseYaml(yamlStr: string): unknown {
  return parse(yamlStr);
}

function createValidator(schemaFile: string) {
  const schema = JSON.parse(
    readFileSync(resolve(SCHEMA_DIR, schemaFile), "utf-8"),
  );
  const ajv = new Ajv({ strict: false, allErrors: true });
  addFormats(ajv);
  return ajv.compile(schema);
}

let workflowValidate: ReturnType<typeof createValidator> | null = null;
let actionValidate: ReturnType<typeof createValidator> | null = null;

export function validateWorkflowYaml(yamlStr: string): void {
  if (!workflowValidate) {
    workflowValidate = createValidator("workflow_schema.json");
  }
  const data = parseYaml(yamlStr);
  const valid = workflowValidate(data);
  if (!valid) {
    throw new Error(
      `Workflow YAML schema validation failed:\n${JSON.stringify(workflowValidate.errors, null, 2)}`,
    );
  }
}

export function validateActionYaml(yamlStr: string): void {
  if (!actionValidate) {
    actionValidate = createValidator("action_schema.json");
  }
  const data = parseYaml(yamlStr);
  const valid = actionValidate(data);
  if (!valid) {
    throw new Error(
      `Action YAML schema validation failed:\n${JSON.stringify(actionValidate.errors, null, 2)}`,
    );
  }
}
