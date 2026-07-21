/**
 * Model transform pipeline for synthesis-time transformations.
 *
 * Transforms operate on deep clones of Models between user code and YAML
 * serialization. Each transform receives a Model, mutates it in place (or
 * returns a replacement), and the result is serialized to YAML.
 *
 * Pipeline:
 *
 *     models → cloneModel → [Transform₁] → … → toYaml → disk
 */

import type { Document } from "./models/_base.js";

/**
 * A model-level transform applied during synthesis.
 *
 * Implementations receive a deep clone of the original model and may
 * mutate it freely. The returned value (which may be the same object)
 * is passed to the next transform in the pipeline.
 */
export type Transform = (item: Document) => Document;
