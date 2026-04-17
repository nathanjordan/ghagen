/**
 * Model transform pipeline for synthesis-time transformations.
 *
 * Transforms operate on deep clones of Models between user code and YAML
 * serialization. Each transform receives a Model and a SynthContext,
 * mutates the Model in place (or returns a replacement), and the result
 * is serialized to YAML.
 *
 * Pipeline:
 *
 *     models → cloneModel → [Transform₁] → … → toYaml → disk
 */

import type { ActionModel, WorkflowModel } from "./models/_base.js";

/** A workflow or action ready for synthesis. */
export type SynthItem = WorkflowModel | ActionModel;

/** Context available to transforms during synthesis. */
export interface SynthContext {
  /** Stem of the output filename (e.g. "ci" from "ci.yml"). */
  readonly workflowKey: string;
  /** Whether the item being transformed is a workflow or an action. */
  readonly itemType: "workflow" | "action";
  /** The `App.root` directory (absolute path). */
  readonly root: string;
}

/**
 * A model-level transform applied during synthesis.
 *
 * Implementations receive a deep clone of the original model and may
 * mutate it freely. The returned value (which may be the same object)
 * is passed to the next transform in the pipeline.
 */
export type Transform = (item: SynthItem, ctx: SynthContext) => SynthItem;
