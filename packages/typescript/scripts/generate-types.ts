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
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const REPO_ROOT = resolve(ROOT, "../..");
// Canonical schema snapshot (single source of truth) lives at the repo root.
const SCHEMA_DIR = resolve(REPO_ROOT, "schema");
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

/** One entry of the shared schema registry (`schema/manifest.json`). */
interface SchemaManifestEntry {
  url: string;
  filename: string;
}

// Shared schema registry (name -> upstream URL -> snapshot filename), also read
// by packages/python/scripts/schema_sync.py. Adding a schema is a single edit
// there. The generated-types filename is derived from the snapshot filename:
// `<name>_schema.json` -> `<name>-types.generated.ts`.
const MANIFEST_PATH = resolve(SCHEMA_DIR, "manifest.json");
const manifest: Record<string, SchemaManifestEntry> = JSON.parse(
  readFileSync(MANIFEST_PATH, "utf8"),
);

const TARGETS: SchemaTarget[] = Object.values(manifest).map((entry) => ({
  schemaFile: entry.filename,
  outputFile: entry.filename.replace(/_schema\.json$/, "-types.generated.ts"),
}));

async function main() {
  for (const target of TARGETS) {
    const schemaPath = resolve(SCHEMA_DIR, target.schemaFile);
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
