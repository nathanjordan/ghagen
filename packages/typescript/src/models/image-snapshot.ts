import type { Snapshot as SchemaSnapshot } from "../schema/workflow-types.generated.js";
import { buildModel, extractMeta } from "./_base.js";
import type { WithMeta, ModelSpec, ImageSnapshotModel } from "./_base.js";

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

/** Serialization spec for {@link ImageSnapshotModel}. */
export const IMAGE_SNAPSHOT_SPEC: ModelSpec = {
  kind: "imageSnapshot",
  fieldMap: IMAGE_SNAPSHOT_FIELD_MAP,
  order: ["image-name", "version"],
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
 */
export function imageSnapshot(input: WithMeta<ImageSnapshotInput>): ImageSnapshotModel {
  const [data, meta] = extractMeta(input);
  return buildModel<ImageSnapshotModel>(IMAGE_SNAPSHOT_SPEC, data as Record<string, unknown>, meta);
}
