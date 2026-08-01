import type { Snapshot as SchemaSnapshot } from "../schema/workflow-types.generated.js";
import { defineFactory } from "./_base.js";
import type { ModelSpec, ImageSnapshotModel } from "./_base.js";

/** The mapping-syntax half of the schema `Snapshot` union (string | object). */
type SchemaSnapshotObject = Extract<SchemaSnapshot, { "image-name": string }>;

/**
 * Input properties for a custom runner-image generation request on a job
 * (`jobs.<job_id>.snapshot`, mapping syntax).
 *
 * The string syntax (image name only) is expressed by passing a plain string
 * to `JobInput.snapshot`; this interface adds the optional `version`.
 */
export interface ImageSnapshotInput {
  /** Name of the image to create or add a version to. Serialized as `image-name`. */
  imageName: string;
  /** Optional image version (e.g. `"1"`, `"1.2"`, `"1*"`). Patch versions are not supported. */
  version?: string;
}

const IMAGE_SNAPSHOT_FIELD_MAP = {
  imageName: "image-name",
  version: "version",
} satisfies Record<keyof ImageSnapshotInput, keyof SchemaSnapshotObject>;

/**
 * Serialization spec for {@link ImageSnapshotModel}.
 *
 * `patterns.version` is the mapping-syntax `version` grammar, copied verbatim
 * from the canonical Snapshot (`schema/workflow_schema.json`,
 * `definitions.snapshot.oneOf[1].properties.version.pattern`) and bound back to
 * it by `schema/conformance-values.yml`. No flags: `RegExp.test` is stateful
 * under `/g`, and `\d` is ASCII-only in ECMA-262 (Python mirrors that with
 * `re.ASCII`).
 */
export const IMAGE_SNAPSHOT_SPEC: ModelSpec = {
  kind: "imageSnapshot",
  fieldMap: IMAGE_SNAPSHOT_FIELD_MAP,
  order: { kind: "explicit", keys: ["image-name", "version"] },
  patterns: { version: /^\d+(\.\d+|\*)?$/ },
};

/**
 * Create an image-snapshot model for a job's `snapshot` key (mapping syntax).
 *
 * The returned model maps to `jobs.<job_id>.snapshot` in a GitHub Actions
 * workflow YAML. For the string syntax (image name only), pass a plain string
 * to `job({ snapshot: "..." })` instead.
 *
 * @param input - Image name, optional version, and optional metadata.
 * @returns A branded {@link ImageSnapshotModel}.
 *
 * @example
 * ```ts
 * imageSnapshot({ imageName: "custom-ubuntu", version: "1.0" });
 * ```
 * @function
 */
export const imageSnapshot = defineFactory<ImageSnapshotModel, ImageSnapshotInput>(
  IMAGE_SNAPSHOT_SPEC,
);
