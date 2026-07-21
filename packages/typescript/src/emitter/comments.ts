import { YAMLMap, YAMLSeq, Scalar, Pair } from "yaml";

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
 * This is the TypeScript peer of `emitter/comments.py`.
 */

/**
 * Attach a block and/or EOL comment from a `Commented` wrapper to one mapping
 * field's pair.
 *
 * - block comment → `key.commentBefore` (renders above the field).
 * - EOL comment → on the value for scalars; on the key for complex values
 *   (map / seq) so it renders on the key line rather than swallowed by the
 *   nested block.
 */
export function attachFieldComment(pair: Pair, comment?: string, eolComment?: string): void {
  if (comment) {
    const key = pair.key instanceof Scalar ? pair.key : new Scalar(pair.key);
    key.commentBefore = comment;
    pair.key = key;
  }

  if (eolComment) {
    if (pair.value instanceof YAMLMap || pair.value instanceof YAMLSeq) {
      // For complex values, set comment on the key so it appears on the key line.
      const key = pair.key instanceof Scalar ? pair.key : new Scalar(pair.key);
      key.comment = eolComment;
      pair.key = key;
    } else if (pair.value instanceof Scalar) {
      pair.value.comment = eolComment;
    } else {
      const val = new Scalar(pair.value);
      val.comment = eolComment;
      pair.value = val;
    }
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
 *   value.
 * - `true` → the map is a `- ` list entry: the block comment goes on the map
 *   node itself (`map.commentBefore`) so it renders above the dash, and the EOL
 *   comment goes on the FIRST value so it renders on the dash/entry-point line
 *   (the peer of ruamel's seq-index EOL redirect to the item's first key).
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
      map.commentBefore = comment;
    } else {
      const firstPair = map.items[0];
      if (firstPair) {
        const key = firstPair.key instanceof Scalar ? firstPair.key : new Scalar(firstPair.key);
        const existing = key.commentBefore;
        key.commentBefore = existing ? `${comment}\n${existing}` : comment;
        firstPair.key = key;
      }
    }
  }

  if (eolComment) {
    // Seq item → the entry-point (first) line; map value / root → the last
    // value. This mirrors ruamel's seq-index EOL redirect on the Python side.
    const target = opts.atSeqItem ? map.items[0] : map.items[map.items.length - 1];
    if (target) {
      if (
        target.value instanceof Scalar ||
        target.value instanceof YAMLMap ||
        target.value instanceof YAMLSeq
      ) {
        target.value.comment = eolComment;
      } else {
        const val = new Scalar(target.value);
        val.comment = eolComment;
        target.value = val;
      }
    }
  }
}
