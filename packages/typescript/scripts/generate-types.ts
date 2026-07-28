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
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { REPO_ROOT, SCHEMA_DIR } from "../src/paths.js";

const TS_PACKAGE_DIR = resolve(REPO_ROOT, "packages/typescript");
const OUTPUT_DIR = resolve(TS_PACKAGE_DIR, "src/schema");

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

const SCHEMA_SUFFIX = "_schema.json";
const GENERATED_SUFFIX = "-types.generated.ts";

/**
 * Derive the generated-types filename from a Snapshot filename, mirroring the
 * validated rule that `scripts/ghagen_schema/manifest.py` owns. Unlike the old
 * silent `String.replace` regex, this throws loudly if the manifest filename
 * does not follow the `<name>_schema.json` convention, so a bad entry cannot
 * make the codegen overwrite its own source.
 */
function deriveGeneratedFilename(snapshotFilename: string): string {
  if (!snapshotFilename.endsWith(SCHEMA_SUFFIX)) {
    throw new Error(
      `manifest filename "${snapshotFilename}" must end in "${SCHEMA_SUFFIX}" ` +
        "so the generated-types name can be derived; fix schema/manifest.json.",
    );
  }
  const stem = snapshotFilename.slice(0, -SCHEMA_SUFFIX.length);
  return stem + GENERATED_SUFFIX;
}

// Shared schema registry (name -> upstream URL -> snapshot filename), also read
// by the Python orchestrator (scripts/ghagen_schema/). Adding a schema is a
// single edit there.
const MANIFEST_PATH = resolve(SCHEMA_DIR, "manifest.json");
const manifest: Record<string, SchemaManifestEntry> = JSON.parse(
  readFileSync(MANIFEST_PATH, "utf8"),
);

const TARGETS: SchemaTarget[] = Object.values(manifest).map((entry) => ({
  schemaFile: entry.filename,
  outputFile: deriveGeneratedFilename(entry.filename),
}));

async function main() {
  const outputPaths: string[] = [];
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
    outputPaths.push(outputPath);
    console.log(`  -> ${outputPath}`);
  }

  // json-schema-to-typescript formats with its bundled prettier, which
  // disagrees with the repo's oxfmt style — reformat so regeneration is
  // stable under `fmt.sh` and CI's format check.
  execFileSync("npx", ["oxfmt", ...outputPaths], { cwd: TS_PACKAGE_DIR, stdio: "inherit" });

  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
