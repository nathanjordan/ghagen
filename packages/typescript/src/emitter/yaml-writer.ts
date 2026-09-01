import { Document, YAMLMap, YAMLSeq, Scalar, Pair } from "yaml";
import {
  isCommented,
  isRaw,
  Model,
  unwrapCommented,
  type Document as GhagenDocument,
} from "../models/_base.js";
import { attachFieldComment, attachModelComment } from "./comments.js";
import { commentString } from "./comment-geometry.js";
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
 *
 * `autoDedent` dedents a Step's `run` here, at read time, exactly where
 * {@link modelToData} does it — no model mutation, no clone (ADR-0002; the
 * peer of Python's `collect_fields`, `emitter/nodes.py:107-110`). Applied
 * wherever a Step is encountered in the recursion, not gated on the document
 * kind, so a step nested in a job, a composite action's `runs`, or `extras`
 * dedents alike.
 *
 * Module-private: the supported way to observe a model's emitted structure is
 * {@link toData}. `modelToYamlMap` builds `yaml` backend nodes for file
 * emission and is an internal of that path.
 */
function modelToYamlMap(model: Model, autoDedent: boolean): YAMLMap {
  const map = new YAMLMap();
  const entries = orderedEntries(model);
  const presentNull = new Set(model.spec.presentNullWhenEmpty ?? []);
  const isStep = model.kind === "step";

  // Emit each field, attaching any Commented-wrapper comment inline at the
  // point of emission (no collect-then-reattach two-pass). The comment module
  // owns the actual placement.
  for (const [key, entryValue] of entries) {
    const value =
      autoDedent && isStep && key === "run" && typeof entryValue === "string"
        ? dedentScript(entryValue)
        : entryValue;

    // present-null-when-empty: an empty sub-map emits as a bare `key:` (null).
    if (presentNull.has(key) && isEmptyMapValue(value)) {
      const pair = new Pair(new Scalar(key), nullScalar());
      map.items.push(pair);
      const { comment, eolComment } = presentNullComments(value);
      if (comment !== undefined || eolComment !== undefined) {
        attachFieldComment(pair, comment, eolComment);
      }
      continue;
    }
    if (isCommented(value)) {
      const pair = new Pair(new Scalar(key), toYamlValue(unwrapCommented(value), autoDedent));
      map.items.push(pair);
      attachFieldComment(pair, value.comment, value.eolComment);
    } else {
      map.items.push(new Pair(new Scalar(key), toYamlValue(value, autoDedent)));
    }
  }

  if (model.meta.postProcess) {
    model.meta.postProcess(map);
  }

  return map;
}

/** Convert any Model value to a YAML node. `autoDedent` threads through to
 * every nested {@link modelToYamlMap} call so a Step reached at any depth
 * dedents alike. */
function toYamlValue(value: unknown, autoDedent: boolean): unknown {
  if (value === null || value === undefined) {
    return null;
  }

  // Commented values — unwrap and recurse
  if (isCommented(value)) {
    return toYamlValue(unwrapCommented(value), autoDedent);
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
    const childMap = modelToYamlMap(value, autoDedent);
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
        const node = modelToYamlMap(item, autoDedent);
        attachModelComment(node, item.meta.comment, item.meta.eolComment, {
          atSeqItem: true,
        });
        seq.add(node);
      } else {
        seq.add(toYamlValue(item, autoDedent));
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
      const pair = new Pair(new Scalar(k), toYamlValue(v, autoDedent));
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
 * Resolve a model's emitted `[key, value]` entries in canonical order, folding
 * in `meta.extras` per the spec's {@link OrderMode}.
 *
 * The single home for both Emitter passes ({@link modelToYamlMap} and
 * {@link modelToData}), so the YAML nodes and the observed data cannot disagree
 * on ordering. `alphabetical` sorts every key, extras included; `explicit` — the
 * default — emits `data` as it stands, then extras.
 *
 * "As it stands" *is* the spec's declaration order: `buildYamlData` populates
 * `data` by iterating `Object.entries(spec.fieldMap)`, and the dynamic-key
 * passthrough appends after that. There is no second key list to re-derive the
 * sequence from, and therefore none to disagree with it.
 */
function orderedEntries(model: Model): [string, unknown][] {
  const data = model.data;
  const extras = model.meta.extras ?? {};

  if (model.spec.order === "alphabetical") {
    const allKeys = [...new Set([...Object.keys(data), ...Object.keys(extras)])].sort();
    return allKeys.map((key) => [key, key in data ? data[key] : extras[key]]);
  }

  return [...Object.entries(data), ...Object.entries(extras)];
}

/**
 * True when *value* resolves to an empty map — an empty sub-Model (no `data`,
 * no extras) or a plain `{}`. Booleans, arrays, `Raw`, and non-empty maps are
 * not empty maps. Powers the `presentNullWhenEmpty` rule.
 */
function isEmptyMapValue(value: unknown): boolean {
  const v = unwrapCommented(value);
  if (v instanceof Model) {
    return (
      Object.keys(v.data).length === 0 &&
      (v.meta.extras === undefined || Object.keys(v.meta.extras).length === 0)
    );
  }
  if (v === null || v === undefined || isRaw(v) || Array.isArray(v)) {
    return false;
  }
  return typeof v === "object" && Object.keys(v).length === 0;
}

/** Join the defined comment payloads with newlines, or `undefined`. */
function joinComments(...parts: (string | undefined)[]): string | undefined {
  const present = parts.filter((p): p is string => p !== undefined);
  return present.length > 0 ? present.join("\n") : undefined;
}

/**
 * The comments a present-null entry carries: the field's own, then the
 * discarded sub-model's.
 *
 * A present-null collapse throws the sub-model away. When that sub-model
 * carried its OWN comment, the comment would have rendered inside the map,
 * below the key; the map is gone, so it renders below the field's comment on
 * the key that replaced it. Dropping it instead — which both ports used to
 * do — silently deleted the only content the user wrote, since an otherwise
 * empty commented sub-model is nothing but its comment. Peer of Python's
 * `emit_entries`.
 */
function presentNullComments(value: unknown): {
  comment: string | undefined;
  eolComment: string | undefined;
} {
  const wrapper = isCommented(value) ? value : undefined;
  const inner = unwrapCommented(value);
  const sub = inner instanceof Model ? inner.meta : undefined;
  return {
    comment: joinComments(wrapper?.comment, sub?.comment),
    eolComment: joinComments(wrapper?.eolComment, sub?.eolComment),
  };
}

/** A null scalar that emits as a bare `key:` (empty source), matching ruamel. */
function nullScalar(): Scalar {
  const scalar = new Scalar(null);
  scalar.source = "";
  return scalar;
}

// ---- public observation surface: model → plain data ----
//
// `toData` is THE supported way to observe a single model's emitted structure
// (keys, values, order, aliasing, extras, dynamic keys, and optionally comment
// placement) without reaching into `yaml` nodes, the `data` bag, or spec
// identity. It reads the same `spec.order` as `modelToYamlMap`, so the two
// renderings cannot disagree on structure.

/**
 * The backend-neutral representation of a value plus its attached comment.
 *
 * Produced by {@link toData} with `comments: true`, and only for nodes that
 * actually carry a comment — the observation-surface peer of the internal
 * `Commented` wrapper.
 */
export interface CommentNode {
  readonly value: unknown;
  readonly comment?: string;
  readonly eolComment?: string;
}

/** Options for {@link toData}. */
export interface ToDataOptions {
  /** Dedent each step's `run` script, as {@link toYaml} does. Defaults to false. */
  autoDedent?: boolean;
  /**
   * Surface commented nodes as {@link CommentNode} so comment placement is
   * observable as data. Defaults to false (comments unwrapped to their values).
   */
  comments?: boolean;
}

/**
 * Emit any {@link Model} to a plain POJO / array / scalar tree — the supported
 * observation surface. Keys are YAML keys in canonical order (from the spec),
 * extras merged after ordered keys, `Raw` unwrapped to its inner value.
 *
 * - `comments: false` (default): `Commented` wrappers are unwrapped to their
 *   values; the returned tree contains no framework wrapper types, so it is
 *   safe for `toEqual`.
 * - `comments: true`: a node that carries a comment is returned as a
 *   {@link CommentNode}.
 *
 * Any model may be passed (step, job, on, …). Unlike {@link toYaml}, this does
 * not run the `yaml`-backend passes (block-literal promotion, comment
 * geometry) or `postProcess`; assert those via the YAML string.
 */
export function toData(model: Model, options?: ToDataOptions): unknown {
  return modelToData(model, options?.comments ?? false, options?.autoDedent ?? false);
}

/** Walk a model's `data` bag to a plain object — the peer of `modelToYamlMap`. */
function modelToData(
  model: Model,
  comments: boolean,
  autoDedent: boolean,
): Record<string, unknown> {
  const entries = orderedEntries(model);
  const presentNull = new Set(model.spec.presentNullWhenEmpty ?? []);
  const isStep = model.kind === "step";

  const result: Record<string, unknown> = {};
  for (const [key, value] of entries) {
    // autoDedent is applied wherever a Step's `run` is encountered in the
    // recursion (matching Python), not gated on the document kind — so a bare
    // Step or a Step nested in a job both dedent.
    const field =
      autoDedent && isStep && key === "run" && typeof value === "string"
        ? dedentScript(value)
        : value;
    const emptyPresentNull = presentNull.has(key) && isEmptyMapValue(field);
    if (emptyPresentNull) {
      // The collapse discards the sub-model, so its own comment folds onto the
      // bare `key:` below the field's — the same resolution `modelToYamlMap`
      // makes, so the two passes cannot disagree about it.
      const { comment, eolComment } = presentNullComments(field);
      result[key] =
        comments && (comment !== undefined || eolComment !== undefined)
          ? commentNode(null, comment, eolComment)
          : null;
    } else if (isCommented(field)) {
      const inner = valueToData(field.value, comments, autoDedent);
      result[key] =
        comments && (field.comment !== undefined || field.eolComment !== undefined)
          ? commentNode(inner, field.comment, field.eolComment)
          : inner;
    } else {
      result[key] = valueToData(field, comments, autoDedent);
    }
  }
  return result;
}

/** Convert any Model value to plain data — the peer of `toYamlValue`. */
function valueToData(value: unknown, comments: boolean, autoDedent: boolean): unknown {
  if (value === null || value === undefined) {
    return null;
  }
  // A Commented not at a mapping-field position: unwrap, drop the comment
  // (matches toYamlValue).
  if (isCommented(value)) {
    return valueToData(value.value, comments, autoDedent);
  }
  if (isRaw(value)) {
    return valueToData(value.value, comments, autoDedent);
  }
  if (value instanceof Model) {
    const data = modelToData(value, comments, autoDedent);
    // A model's OWN comment is surfaced here (map value or seq item alike);
    // container placement differs in YAML but not in observed data.
    return comments && (value.meta.comment !== undefined || value.meta.eolComment !== undefined)
      ? commentNode(data, value.meta.comment, value.meta.eolComment)
      : data;
  }
  if (Array.isArray(value)) {
    return value.map((item) => valueToData(item, comments, autoDedent));
  }
  if (typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      if (v === undefined) {
        continue;
      }
      out[k] = valueToData(v, comments, autoDedent);
    }
    return out;
  }
  return value;
}

/** Build a {@link CommentNode}, omitting undefined comment fields for clean equality. */
function commentNode(value: unknown, comment?: string, eolComment?: string): CommentNode {
  const node: { value: unknown; comment?: string; eolComment?: string } = { value };
  if (comment !== undefined) {
    node.comment = comment;
  }
  if (eolComment !== undefined) {
    node.eolComment = eolComment;
  }
  return node;
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
  const autoDedent = options?.autoDedent ?? true;

  const doc = new Document();
  doc.contents = modelToYamlMap(model, autoDedent);

  if (doc.contents instanceof YAMLMap) {
    // The root model's OWN comment, rendered on the map as a whole — the same
    // helper that closes the nested map-value gap.
    attachModelComment(doc.contents, model.meta.comment, model.meta.eolComment, {
      atSeqItem: false,
    });
  }

  // No text pass runs over the result: every comment payload was rendered by
  // `comment-geometry.ts` at attach time, so `commentString` is the identity
  // and no `#` inside a scalar is ever mistaken for a comment. (This is
  // compatible with docs/specs/0003 either way: that spec ruled string-level
  // output normalization in scope to stay, and header text is now out of any
  // such pass's reach regardless of what the pass becomes.)
  const yaml = doc.toString({ lineWidth: 0, indentSeq: false, singleQuote: true, commentString });

  // The header never reaches the document node. `stringifyDocument` would
  // insert a blank line between a `commentBefore` and the body and drop a
  // falsy one outright — neither configurable, and neither what the Python
  // port emits. `formatHeader` returns the exact bytes; this concatenates.
  const headerStr = formatHeader(options?.header, model.sourceLocation);
  return headerStr === null ? yaml : headerStr + yaml;
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
