import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parse } from "yaml";
// Both packages are CommonJS, so under `moduleResolution: "node16"` a default
// import binds the module namespace rather than the value: `new Ajv(...)` is
// `TS2351: has no construct signatures` and `addFormats(...)` is `TS2349: not
// callable`. Ajv publishes a named `Ajv` export; ajv-formats publishes only a
// default, and its CJS entry sets both `module.exports = plugin` and
// `exports.default = plugin`, so `.default` is the callable under either
// interpretation. Neither line was checked before docs/issues/09.
import { Ajv } from "ajv";
import addFormatsPlugin from "ajv-formats";

const addFormats = addFormatsPlugin.default;
import { EXPECTED_DIR, SCHEMA_DIR } from "../paths.js";

export { EXPECTED_DIR, SCHEMA_DIR };

export function loadFixture(name: string): string {
  return readFileSync(resolve(EXPECTED_DIR, name), "utf-8");
}

export function parseYaml(yamlStr: string): unknown {
  return parse(yamlStr);
}

function createValidator(schemaFile: string) {
  const schema = JSON.parse(readFileSync(resolve(SCHEMA_DIR, schemaFile), "utf-8"));
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
