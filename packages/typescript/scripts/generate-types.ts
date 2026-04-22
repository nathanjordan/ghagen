/**
 * Generate TypeScript reference types from GitHub Actions JSON schemas.
 *
 * These generated types are used for compile-time drift detection only —
 * they are NOT the user-facing API. The hand-written input interfaces in
 * src/models/ are the public API.
 *
 * Usage: npx tsx scripts/generate-types.ts
 */

import { compileFromFile } from "json-schema-to-typescript";
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const SNAPSHOT_DIR = resolve(ROOT, "src/schema/snapshot");
const OUTPUT_DIR = resolve(ROOT, "src/schema");

const BANNER = `/* eslint-disable */
// @ts-nocheck — generated types may contain circular references from the JSON schema
/**
 * AUTO-GENERATED — DO NOT EDIT
 *
 * Generated from GitHub Actions JSON schemas via json-schema-to-typescript.
 * These types are used for compile-time drift detection against hand-written
 * model interfaces. Re-generate with: npm run generate-types
 */

`;

interface SchemaTarget {
  schemaFile: string;
  outputFile: string;
}

const TARGETS: SchemaTarget[] = [
  {
    schemaFile: "workflow_schema.json",
    outputFile: "workflow-types.generated.ts",
  },
  {
    schemaFile: "action_schema.json",
    outputFile: "action-types.generated.ts",
  },
];

async function main() {
  for (const target of TARGETS) {
    const schemaPath = resolve(SNAPSHOT_DIR, target.schemaFile);
    const outputPath = resolve(OUTPUT_DIR, target.outputFile);

    console.log(`Generating ${target.outputFile} from ${target.schemaFile}...`);

    const ts = await compileFromFile(schemaPath, {
      bannerComment: "",
      additionalProperties: false,
      strictIndexSignatures: true,
      enableConstEnums: false,
      style: {
        semi: true,
        singleQuote: false,
      },
    });

    writeFileSync(outputPath, BANNER + ts);
    console.log(`  -> ${outputPath}`);
  }

  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
