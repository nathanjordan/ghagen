import { Document, YAMLMap, YAMLSeq, Scalar, Pair } from "yaml";
import {
  cloneModel,
  isCommented,
  isRaw,
  Model,
  type Document as GhagenDocument,
} from "../models/_base.js";
import { attachFieldComment, attachModelComment } from "./comments.js";
import { formatHeader, type HeaderVariables } from "./header.js";
import { dedentScript } from "../_dedent.js";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

/** Options for controlling YAML serialization output. */
export interface ToYamlOptions {
  /**
   * Header comment for the generated file.
   *
   * - omit / `undefined` — emit ghagen's default header.
   * - `null`             — emit no header.
   * - `string`           — emit the string verbatim. No `{variable}`
   *   substitution; literal braces are preserved.
   * - `(vars) => string` — invoke the closure with a fully-populated
   *   {@link HeaderVariables} and emit the returned string.
   */
  header?: string | null | ((vars: HeaderVariables) => string);
  /**
   * Dedent each step's `run` script at emit time. Defaults to `true`.
   * Set `false` to emit the raw `run` strings verbatim.
   */
  autoDedent?: boolean;
}

/**
 * Return a deep clone of *model* with every step's `run` dedented.
 *
 * Dedent is a serialization-time normalization (ADR-0002): a step's `run`
 * holds the raw string until emit, so this pass walks the tree — steps nested
 * inside jobs *and* composite-action runs — and rewrites `run` on the clone,
 * leaving the caller's model untouched.
 */
function dedentSteps(model: GhagenDocument): GhagenDocument {
  const clone = cloneModel(model);
  clone.walk((node) => {
    if (node.kind === "step" && typeof node.data["run"] === "string") {
      node.data["run"] = dedentScript(node.data["run"] as string);
    }
  });
  return clone;
}

// ---- value → YAML node recursion (the emitter owns it end to end) ----
//
// The single home for turning any Model value into a `yaml` node. Recursion
// never leaves the emitter: models carry only `data` + spec, and the container
// decision for a model's own comment (`atSeqItem`) is made here, at each of the
// three recursion contexts — document root (see `toYaml`), nested map value,
// and list entry — and nowhere else.

/**
 * Render a {@link Model} to a `YAMLMap` with canonical key ordering, per-field
 * comment attachment, extras merging, and postProcess support. The emitter's
 * successor to the old `Model.toYamlMap` method.
 */
export function modelToYamlMap(model: Model): YAMLMap {
  const map = new YAMLMap();
  const orderedKeys = getOrderedKeys(Object.keys(model.data), model.spec.order);

  // Emit each field, attaching any Commented-wrapper comment inline at the
  // point of emission (no collect-then-reattach two-pass). The comment module
  // owns the actual placement.
  const entries: [string, unknown][] = orderedKeys.map((key) => [key, model.data[key]]);
  if (model.meta.extras) {
    entries.push(...Object.entries(model.meta.extras));
  }

  for (const [key, value] of entries) {
    if (isCommented(value)) {
      const pair = new Pair(new Scalar(key), toYamlValue(value.value));
      map.items.push(pair);
      attachFieldComment(pair, value.comment, value.eolComment);
    } else {
      map.items.push(new Pair(new Scalar(key), toYamlValue(value)));
    }
  }

  if (model.meta.postProcess) {
    model.meta.postProcess(map);
  }

  return map;
}

/** Convert any Model value to a YAML node. */
function toYamlValue(value: unknown): unknown {
  if (value === null || value === undefined) {
    return null;
  }

  // Commented values — unwrap and recurse
  if (isCommented(value)) {
    return toYamlValue(value.value);
  }

  // Raw values — unwrap and emit as plain scalar
  if (isRaw(value)) {
    const scalar = new Scalar(value.value);
    scalar.type = Scalar.PLAIN;
    return scalar;
  }

  // Nested Model as a map value — its own comment renders on the map as a
  // whole (block before first key, EOL on last value).
  if (value instanceof Model) {
    const childMap = modelToYamlMap(value);
    attachModelComment(childMap, value.meta.comment, value.meta.eolComment, {
      atSeqItem: false,
    });
    return childMap;
  }

  // Arrays
  if (Array.isArray(value)) {
    const seq = new YAMLSeq();
    for (const item of value) {
      // A Model list entry is built directly and its own comment attached on
      // the seq entry (block above the dash). It never routes through the
      // nested-Model branch above, so there is no wrong attach to undo — the
      // container decision is made here, once.
      if (item instanceof Model) {
        const node = modelToYamlMap(item);
        attachModelComment(node, item.meta.comment, item.meta.eolComment, {
          atSeqItem: true,
        });
        seq.add(node);
      } else {
        seq.add(toYamlValue(item));
      }
    }
    return seq;
  }

  // Plain objects (Record<string, unknown>)
  if (typeof value === "object" && value !== null) {
    const map = new YAMLMap();
    for (const [k, v] of Object.entries(value)) {
      if (v === undefined) {
        continue;
      }
      const pair = new Pair(new Scalar(k), toYamlValue(v));
      map.items.push(pair);
    }
    return map;
  }

  // Strings — use block literal for multiline
  if (typeof value === "string" && value.includes("\n")) {
    const scalar = new Scalar(value);
    scalar.type = Scalar.BLOCK_LITERAL;
    return scalar;
  }

  // Primitives (string, number, boolean)
  return value;
}

/**
 * Sort keys by canonical order: ordered keys first (in specified order),
 * then remaining keys in their original insertion order.
 */
function getOrderedKeys(keys: string[], keyOrder: readonly string[]): string[] {
  const orderSet = new Set(keyOrder);
  const ordered: string[] = [];
  const remaining: string[] = [];

  // Add keys that appear in the canonical order
  for (const key of keyOrder) {
    if (keys.includes(key)) {
      ordered.push(key);
    }
  }

  // Add remaining keys in insertion order
  for (const key of keys) {
    if (!orderSet.has(key)) {
      remaining.push(key);
    }
  }

  return [...ordered, ...remaining];
}

/** Format a YAML comment by prefixing each line with `#`. */
function formatYamlComment(comment: string): string {
  return comment
    .split("\n")
    .map((line) => (line ? `# ${line}` : "#"))
    .join("\n");
}

/**
 * Widen the gap before inline `#` comments from 1 space to 2 to match
 * ruamel.yaml's convention. The lookbehind condition (non-whitespace,
 * non-colon) leaves block comments (indented `#`) and key-only comments
 * (`key: #`) alone.
 */
function fixInlineCommentSpacing(yaml: string): string {
  return yaml.replace(/([^\s:]) (# )/g, "$1  $2");
}

/**
 * Serialize a workflow or action model to a YAML string.
 *
 * Keys are emitted in canonical order, comments are attached, and multiline
 * strings use block-literal style. A header comment identifying the
 * generating tool is prepended by default.
 *
 * @param model   - The model to serialize (e.g. from {@link workflow} or {@link action}).
 * @param options - Optional settings for header customization.
 * @returns The rendered YAML string, including a trailing newline.
 *
 * @example
 * ```ts
 * const yaml = toYaml(myWorkflow);
 * console.log(yaml);
 * ```
 */
export function toYaml(model: GhagenDocument, options?: ToYamlOptions): string {
  const target = (options?.autoDedent ?? true) ? dedentSteps(model) : model;

  const doc = new Document();
  doc.contents = modelToYamlMap(target);

  const headerStr = formatHeader(options?.header, target.sourceLocation);
  if (headerStr !== null) {
    doc.commentBefore = headerStr;
  }

  if (doc.contents instanceof YAMLMap) {
    // The root model's OWN comment, rendered on the map as a whole — the same
    // helper that closes the nested map-value gap.
    attachModelComment(doc.contents, target.meta.comment, target.meta.eolComment, {
      atSeqItem: false,
    });
  }

  const yaml = doc.toString({
    lineWidth: 0,
    indentSeq: false,
    singleQuote: true,
    commentString: formatYamlComment,
  });

  return fixInlineCommentSpacing(yaml);
}

/**
 * Serialize a model to a YAML file.
 *
 * Creates any intermediate directories that do not yet exist and writes the
 * YAML output synchronously. This is a convenience wrapper around
 * {@link toYaml} for the common "write to disk" use case.
 *
 * @param model   - The model to serialize.
 * @param path    - Destination file path (absolute or relative to cwd).
 * @param options - Optional settings forwarded to {@link toYaml}.
 *
 * @example
 * ```ts
 * toYamlFile(myWorkflow, ".github/workflows/ci.yml");
 *
 * // With a custom header — strings are emitted verbatim:
 * toYamlFile(myAction, "action.yml", { header: "Hand-written header" });
 *
 * // For interpolation, pass a closure:
 * toYamlFile(myAction, "action.yml", {
 *   header: (v) => `Generated by ${v.tool} v${v.version}`,
 * });
 * ```
 */
export function toYamlFile(model: GhagenDocument, path: string, options?: ToYamlOptions): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, toYaml(model, options));
}
