import { describe, it, expect } from "vitest";
import { YAMLMap, Scalar, Pair } from "yaml";
import { attachFieldComment, attachModelComment } from "./comments.js";

// ---------------------------------------------------------------------------
// helpers — build plain `yaml` nodes without any Model / Document
// ---------------------------------------------------------------------------

/** A YAMLMap from [key, value] entries, values wrapped as Scalars. */
function mapOf(entries: [string, unknown][]): YAMLMap {
  const map = new YAMLMap();
  for (const [k, v] of entries) {
    map.items.push(new Pair(new Scalar(k), v instanceof YAMLMap ? v : new Scalar(v)));
  }
  return map;
}

function firstPair(map: YAMLMap): Pair {
  return map.items[0] as Pair;
}
function lastPair(map: YAMLMap): Pair {
  return map.items[map.items.length - 1] as Pair;
}

// ---------------------------------------------------------------------------
// attachFieldComment
// ---------------------------------------------------------------------------
describe("attachFieldComment()", () => {
  it("attaches a block comment before the key", () => {
    const pair = new Pair(new Scalar("name"), new Scalar("ci"));
    attachFieldComment(pair, "The name", undefined);
    expect((pair.key as Scalar).commentBefore).toBe("The name");
  });

  it("attaches an EOL comment on a scalar value", () => {
    const pair = new Pair(new Scalar("name"), new Scalar("ci"));
    attachFieldComment(pair, undefined, "inline note");
    expect((pair.value as Scalar).comment).toBe("inline note");
    expect((pair.key as Scalar).commentBefore).toBeUndefined();
  });

  it("attaches both block and EOL comments", () => {
    const pair = new Pair(new Scalar("name"), new Scalar("ci"));
    attachFieldComment(pair, "above", "beside");
    expect((pair.key as Scalar).commentBefore).toBe("above");
    expect((pair.value as Scalar).comment).toBe("beside");
  });

  it("redirects an EOL comment for a complex value onto the key line", () => {
    const inner = mapOf([["a", 1]]);
    const pair = new Pair(new Scalar("obj"), inner);
    attachFieldComment(pair, undefined, "on the key");
    expect((pair.key as Scalar).comment).toBe("on the key");
  });

  it("is a no-op when neither comment is given", () => {
    const pair = new Pair(new Scalar("name"), new Scalar("ci"));
    attachFieldComment(pair, undefined, undefined);
    expect((pair.key as Scalar).commentBefore).toBeUndefined();
    expect((pair.value as Scalar).comment).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// attachModelComment — atSeqItem: false (map value / document root)
// ---------------------------------------------------------------------------
describe("attachModelComment() atSeqItem:false", () => {
  it("attaches a block comment to the first key", () => {
    const map = mapOf([
      ["name", "Lint"],
      ["runs-on", "ubuntu-latest"],
    ]);
    attachModelComment(map, "Run linters", undefined, { atSeqItem: false });
    expect((firstPair(map).key as Scalar).commentBefore).toBe("Run linters");
    expect(map.commentBefore).toBeUndefined();
  });

  it("attaches an EOL comment to the last value", () => {
    const map = mapOf([
      ["alpha", 1],
      ["zulu", 2],
    ]);
    attachModelComment(map, undefined, "end of block", { atSeqItem: false });
    expect((lastPair(map).value as Scalar).comment).toBe("end of block");
  });

  it("merges a block comment ahead of an existing first-key comment", () => {
    const map = mapOf([["name", "Lint"]]);
    (firstPair(map).key as Scalar).commentBefore = "field comment";
    attachModelComment(map, "model comment", undefined, { atSeqItem: false });
    expect((firstPair(map).key as Scalar).commentBefore).toBe("model comment\nfield comment");
  });

  it("is a no-op on an empty map", () => {
    const map = new YAMLMap();
    attachModelComment(map, "x", "y", { atSeqItem: false });
    expect(map.commentBefore).toBeUndefined();
    expect(map.items).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// attachModelComment — atSeqItem: true (list entry)
// ---------------------------------------------------------------------------
describe("attachModelComment() atSeqItem:true", () => {
  it("attaches the block comment to the map node, NOT the first key", () => {
    const map = mapOf([
      ["uses", "actions/checkout@v4"],
      ["with", "x"],
    ]);
    attachModelComment(map, "checkout step", undefined, { atSeqItem: true });
    expect(map.commentBefore).toBe("checkout step");
    // Regression guard for the deleted duplicate-comment workaround: the first
    // key must carry no block comment.
    expect((firstPair(map).key as Scalar).commentBefore ?? undefined).toBeUndefined();
  });

  it("attaches an EOL comment to the FIRST value (the dash/entry-point line)", () => {
    const map = mapOf([
      ["uses", "actions/checkout@v4"],
      ["with", "x"],
    ]);
    attachModelComment(map, undefined, "beside", { atSeqItem: true });
    expect((firstPair(map).value as Scalar).comment).toBe("beside");
    expect((lastPair(map).value as Scalar).comment ?? undefined).toBeUndefined();
    expect(map.commentBefore).toBeUndefined();
  });
});
