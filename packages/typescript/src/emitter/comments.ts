import { YAMLMap, YAMLSeq, Scalar, Pair } from "yaml";
import { renderBlockComment, renderEolComment } from "./comment-geometry.js";

/**
 * Comment attachment: the single owner of how a comment lands on a `yaml` node.
 *
 * Every path by which a YAML comment reaches a node routes through this module:
 *
 * - {@link attachFieldComment} — a block/EOL comment from a `Commented` wrapper
 *   on one mapping field, attached to that field's pair.
 * - {@link attachModelComment} — a model's OWN block/EOL comment, rendered on
 *   the map as a whole. `atSeqItem` is the one container decision that the old
 *   duplicate-comment workaround hacked around.
 *
 * This module decides WHICH node a comment lands on; `emitter/comment-geometry.ts`
 * decides what the payload looks like. Every write below goes through a
 * renderer from that module — nothing here writes raw comment text.
 *
 * This is the TypeScript peer of `emitter/comments.py`.
 */

/** The pair's key as a `Scalar`, promoting a non-`Scalar` key in place. */
function keyScalar(pair: Pair): Scalar {
  const key = pair.key instanceof Scalar ? pair.key : new Scalar(pair.key);
  pair.key = key;
  return key;
}

/** Add a block comment before *pair*'s key, after any block comment already there. */
function addBlockComment(pair: Pair, text: string): void {
  const key = keyScalar(pair);
  const rendered = renderBlockComment(text);
  key.commentBefore = key.commentBefore ? `${key.commentBefore}\n${rendered}` : rendered;
}

/**
 * Put an EOL comment on *pair*, or — when the payload cannot sit at
 * end-of-line — above it as a block comment.
 *
 * The EOL comment goes on the value for scalars and on the KEY for complex
 * values (map / seq), so it renders on the key line rather than being
 * swallowed into the nested block. That container rule is the same in both
 * containers and in both ports; it is also what keeps `lineComment`'s
 * no-column branch out of the reachable set (see `comment-geometry.ts`).
 */
function addEolComment(pair: Pair, text: string): void {
  const rendered = renderEolComment(text);
  if (rendered === null) {
    // Multi-line payload: it cannot sit at end-of-line in either backend, so
    // it degrades to a block comment on the same item.
    addBlockComment(pair, text);
    return;
  }
  if (pair.value instanceof YAMLMap || pair.value instanceof YAMLSeq) {
    keyScalar(pair).comment = rendered;
  } else if (pair.value instanceof Scalar) {
    pair.value.comment = rendered;
  } else {
    const val = new Scalar(pair.value);
    val.comment = rendered;
    pair.value = val;
  }
}

/**
 * Attach a block and/or EOL comment from a `Commented` wrapper to one mapping
 * field's pair.
 *
 * - block comment → `key.commentBefore` (renders above the field).
 * - EOL comment → on the value for scalars; on the key for complex values
 *   (map / seq) so it renders on the key line rather than swallowed by the
 *   nested block; above the field as a block comment when the payload is
 *   multi-line.
 */
export function attachFieldComment(pair: Pair, comment?: string, eolComment?: string): void {
  if (comment) {
    addBlockComment(pair, comment);
  }
  if (eolComment) {
    addEolComment(pair, eolComment);
  }
}

/**
 * Attach a model's OWN block/EOL comment, rendered on the map as a whole.
 *
 * `atSeqItem` is the one decision the old duplicate-comment workaround hacked
 * around — a model renders differently depending on its container:
 *
 * - `false` → the map is a field value or the document root: the block comment
 *   goes on the first key (`key.commentBefore`) and the EOL comment on the last
 *   entry's line.
 * - `true` → the map is a `- ` list entry: the block comment goes on the map
 *   node itself (`map.commentBefore`) so it renders above the dash, and the EOL
 *   comment goes on the FIRST entry's line so it renders on the dash/entry-point
 *   line (the peer of ruamel's seq-index EOL redirect to the item's first key).
 *
 * In both containers the EOL comment lands on the target pair's KEY when that
 * pair's value is a map or a seq — the same rule {@link attachFieldComment}
 * applies — so a `job({ eolComment })`, whose last key is `steps`, renders
 * `steps:  # …` rather than orphaning the comment below the step list.
 *
 * The container decision is made ONCE, by the caller — so no second call site
 * has to reverse a wrongly-placed attachment.
 */
export function attachModelComment(
  map: YAMLMap,
  comment: string | undefined,
  eolComment: string | undefined,
  opts: { atSeqItem: boolean },
): void {
  if (comment) {
    if (opts.atSeqItem) {
      map.commentBefore = renderBlockComment(comment);
    } else {
      const firstPair = map.items[0] as Pair | undefined;
      if (firstPair) {
        // A model's own comment precedes any field comment already on that key.
        const key = keyScalar(firstPair);
        const rendered = renderBlockComment(comment);
        key.commentBefore = key.commentBefore ? `${rendered}\n${key.commentBefore}` : rendered;
      }
    }
  }

  if (eolComment) {
    // Seq item → the entry-point (first) line; map value / root → the last
    // entry's line. This mirrors ruamel's seq-index EOL redirect on the Python
    // side.
    const target = (opts.atSeqItem ? map.items[0] : map.items[map.items.length - 1]) as
      | Pair
      | undefined;
    if (target) {
      addEolComment(target, eolComment);
    }
  }
}
