import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { EXPECTED_DIR, loadFixture } from "../integration/test-utils.js";
import { Lockfile, LockfileError, readLockfile, writeLockfile } from "./lockfile.js";
import type { PinEntry } from "./lockfile.js";

/**
 * The exact entries `fixtures/expected/lockfile_golden.yml` encodes. Both ports
 * write these to the golden's bytes and read the golden back to them.
 */
const GOLDEN_ENTRIES: ReadonlyArray<readonly [string, PinEntry]> = [
  [
    "actions/checkout@v4",
    {
      sha: "3df4ab11eba7bda6032a0b82a6bb43b11571feac",
      resolvedAt: new Date("2026-04-09T14:30:00Z"),
    },
  ],
  // An all-digit SHA: the case where ruamel and the `yaml` package pick
  // different quotes when left to their own heuristics.
  [
    "docker://alpine:3.19",
    {
      sha: "1234567890123456789012345678901234567890",
      resolvedAt: new Date("2026-04-09T14:30:00Z"),
    },
  ],
  [
    "pypa/gh-action-pypi-publish@release/v1",
    { sha: "b".repeat(40), resolvedAt: new Date("2026-04-08T00:00:00Z") },
  ],
];

/** A one-entry lockfile document with `literal` as the `resolved_at` value. */
function lockDoc(literal: string): string {
  return [
    "pins:",
    "  actions/checkout@v4:",
    `    sha: "${"a".repeat(40)}"`,
    `    resolved_at: ${literal}`,
    "",
  ].join("\n");
}

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-lockfile-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

describe("Lockfile", () => {
  it("get/set/prune", () => {
    const lf = new Lockfile();
    lf.set("actions/checkout@v4", { sha: "a".repeat(40), resolvedAt: new Date() });
    lf.set("actions/setup-node@v4", { sha: "b".repeat(40), resolvedAt: new Date() });
    expect(lf.get("actions/checkout@v4")?.sha).toBe("a".repeat(40));
    expect(lf.size).toBe(2);
    expect(lf.prune(new Set(["actions/checkout@v4"]))).toBe(1);
    expect(lf.size).toBe(1);
  });

  it("set replaces an existing entry", () => {
    const lf = new Lockfile();
    lf.set("actions/checkout@v4", { sha: "a".repeat(40), resolvedAt: new Date() });
    lf.set("actions/checkout@v4", { sha: "b".repeat(40), resolvedAt: new Date() });
    expect(lf.get("actions/checkout@v4")?.sha).toBe("b".repeat(40));
    expect(lf.size).toBe(1);
  });

  it("has and keys", () => {
    const lf = new Lockfile([
      ["actions/checkout@v4", { sha: "a".repeat(40), resolvedAt: new Date() }],
      ["actions/setup-node@v4", { sha: "b".repeat(40), resolvedAt: new Date() }],
    ]);
    expect(lf.has("actions/checkout@v4")).toBe(true);
    expect(lf.has("actions/nope@v1")).toBe(false);
    expect(new Set(lf.keys())).toEqual(new Set(["actions/checkout@v4", "actions/setup-node@v4"]));
  });
});

describe("readLockfile validation", () => {
  it("throws LockfileError on a missing sha", () => {
    const path = join(tmp, "lock.yml");
    writeFileSync(
      path,
      ["pins:", "  actions/checkout@v4:", '    resolved_at: "2026-04-09T14:30:00+00:00"', ""].join(
        "\n",
      ),
    );
    expect(() => readLockfile(path)).toThrow(LockfileError);
    expect(() => readLockfile(path)).toThrow(/sha/);
  });

  it("throws LockfileError on a non-table entry", () => {
    const path = join(tmp, "lock.yml");
    writeFileSync(path, ["pins:", "  actions/checkout@v4: just-a-string", ""].join("\n"));
    expect(() => readLockfile(path)).toThrow(LockfileError);
    expect(() => readLockfile(path)).toThrow(/actions\/checkout@v4/);
  });

  it("throws LockfileError on a bad resolved_at", () => {
    const path = join(tmp, "lock.yml");
    writeFileSync(
      path,
      [
        "pins:",
        "  actions/checkout@v4:",
        `    sha: "${"a".repeat(40)}"`,
        '    resolved_at: "not-a-timestamp"',
        "",
      ].join("\n"),
    );
    expect(() => readLockfile(path)).toThrow(LockfileError);
    expect(() => readLockfile(path)).toThrow(/resolved_at/);
  });

  it("throws LockfileError when 'pins' is not a table", () => {
    const path = join(tmp, "lock.yml");
    writeFileSync(path, ["pins:", "  - actions/checkout@v4", ""].join("\n"));
    expect(() => readLockfile(path)).toThrow(LockfileError);
    expect(() => readLockfile(path)).toThrow(/pins/);
  });
});

describe("readLockfile / writeLockfile", () => {
  it("returns empty lockfile when file missing", () => {
    const lf = readLockfile(join(tmp, "missing.yml"));
    expect(lf.size).toBe(0);
  });

  it("round-trips entries with sorted keys and snake_case on disk", () => {
    const path = join(tmp, "lock.yml");
    const lf = new Lockfile([
      [
        "owner/repo-b@v2",
        {
          sha: "b".repeat(40),
          resolvedAt: new Date("2026-04-09T14:30:00Z"),
        },
      ],
      [
        "owner/repo-a@v1",
        {
          sha: "a".repeat(40),
          resolvedAt: new Date("2026-04-08T00:00:00Z"),
        },
      ],
    ]);
    writeLockfile(lf, path);
    const text = readFileSync(path, "utf8");

    // Header is exact.
    expect(
      text.startsWith("# Auto-generated by `ghagen deps pin`. Do not edit manually.\n\n"),
    ).toBe(true);
    // Snake_case keys on disk.
    expect(text).toContain("sha:");
    expect(text).toContain("resolved_at:");
    // Sorted: a-pin before b-pin.
    const idxA = text.indexOf("owner/repo-a");
    const idxB = text.indexOf("owner/repo-b");
    expect(idxA).toBeGreaterThan(0);
    expect(idxB).toBeGreaterThan(idxA);

    const round = readLockfile(path);
    expect(round.size).toBe(2);
    const a = round.get("owner/repo-a@v1");
    expect(a?.sha).toBe("a".repeat(40));
    expect(a?.resolvedAt.toISOString()).toBe("2026-04-08T00:00:00.000Z");
  });

  it("read -> write is byte-identical", () => {
    const path1 = join(tmp, "lock1.yml");
    const lf = new Lockfile([
      ["owner/repo-b@v2", { sha: "b".repeat(40), resolvedAt: new Date("2026-04-09T14:30:00Z") }],
      ["owner/repo-a@v1", { sha: "a".repeat(40), resolvedAt: new Date("2026-04-08T00:00:00Z") }],
    ]);
    writeLockfile(lf, path1);
    const first = readFileSync(path1);

    const path2 = join(tmp, "lock2.yml");
    writeLockfile(readLockfile(path1), path2);
    expect(readFileSync(path2).equals(first)).toBe(true);
  });

  it("reads a Python-written lockfile (string-typed resolved_at)", () => {
    // The Python port writes exactly the golden's bytes; this is the real
    // artefact, not a hand-written approximation of the docstring's form.
    const path = join(tmp, "py.yml");
    writeFileSync(path, loadFixture("lockfile_golden.yml"));
    const lf = readLockfile(path);
    const entry = lf.get("actions/checkout@v4");
    expect(entry?.sha).toBe("3df4ab11eba7bda6032a0b82a6bb43b11571feac");
    expect(entry?.resolvedAt.toISOString()).toBe("2026-04-09T14:30:00.000Z");
  });
});

describe("golden conformance", () => {
  it("writes the golden's bytes exactly", () => {
    const path = join(tmp, "lock.yml");
    writeLockfile(new Lockfile(GOLDEN_ENTRIES), path);
    expect(
      readFileSync(path).equals(readFileSync(resolve(EXPECTED_DIR, "lockfile_golden.yml"))),
    ).toBe(true);
  });

  it("reads the golden back to the same entries", () => {
    const path = join(tmp, "lock.yml");
    writeFileSync(path, loadFixture("lockfile_golden.yml"));
    const lf = readLockfile(path);
    expect([...lf.keys()].sort()).toEqual(GOLDEN_ENTRIES.map(([uses]) => uses).sort());
    for (const [uses, expected] of GOLDEN_ENTRIES) {
      const entry = lf.get(uses);
      expect(entry?.sha).toBe(expected.sha);
      expect(entry?.resolvedAt.toISOString()).toBe(expected.resolvedAt.toISOString());
    }
  });

  it("truncates sub-second precision to whole seconds", () => {
    const path = join(tmp, "lock.yml");
    const lf = new Lockfile([
      [
        "actions/checkout@v4",
        { sha: "a".repeat(40), resolvedAt: new Date("2026-04-09T14:30:00.123Z") },
      ],
    ]);
    writeLockfile(lf, path);
    expect(readFileSync(path, "utf8")).toContain('    resolved_at: "2026-04-09T14:30:00+00:00"\n');
  });

  it("double-quotes an all-digit sha", () => {
    const path = join(tmp, "lock.yml");
    const lf = new Lockfile([
      [
        "docker://alpine:3.19",
        { sha: "1".repeat(40), resolvedAt: new Date("2026-04-09T14:30:00Z") },
      ],
    ]);
    writeLockfile(lf, path);
    expect(readFileSync(path, "utf8")).toContain(`    sha: "${"1".repeat(40)}"\n`);
  });

  it("double-quotes an ordinary sha", () => {
    const path = join(tmp, "lock.yml");
    const lf = new Lockfile([
      [
        "actions/checkout@v4",
        { sha: "a".repeat(40), resolvedAt: new Date("2026-04-09T14:30:00Z") },
      ],
    ]);
    writeLockfile(lf, path);
    expect(readFileSync(path, "utf8")).toContain(`    sha: "${"a".repeat(40)}"\n`);
  });

  it("writes a header naming the real command", () => {
    const path = join(tmp, "lock.yml");
    writeLockfile(new Lockfile(), path);
    expect(readFileSync(path, "utf8")).toBe(
      "# Auto-generated by `ghagen deps pin`. Do not edit manually.\n\npins: {}\n",
    );
  });
});

describe("key quoting (LATENT — docs/issues/23 item 4)", () => {
  // No fixture reaches this through the CLI -- every realistic `uses:`
  // string already contains a `/`, an `@`, or a `docker://` prefix, none of
  // which is YAML-ambiguous. `Lockfile`'s public API accepts any `string`
  // key, though, so this constructs the input directly: "123456" parses as a
  // YAML int unless quoted. Before the fix, the `yaml` package double-quoted
  // it while ruamel single-quoted it -- same semantic key, different bytes.
  //
  // fixtures/expected/lockfile_key_quoting.yml is the shared oracle: both
  // ports write this exact Lockfile and must produce identical bytes.
  it("writes the golden's bytes exactly for an ambiguous key", () => {
    const path = join(tmp, "lock.yml");
    const lf = new Lockfile([
      ["123456", { sha: "a".repeat(40), resolvedAt: new Date("2026-04-09T14:30:00Z") }],
      [
        "actions/checkout@v4",
        { sha: "b".repeat(40), resolvedAt: new Date("2026-04-09T14:30:00Z") },
      ],
    ]);
    writeLockfile(lf, path);
    expect(
      readFileSync(path).equals(readFileSync(resolve(EXPECTED_DIR, "lockfile_key_quoting.yml"))),
    ).toBe(true);
  });

  it("reads the quoted key back", () => {
    const path = join(tmp, "lock.yml");
    writeFileSync(path, loadFixture("lockfile_key_quoting.yml"));
    const lf = readLockfile(path);
    expect(new Set(lf.keys())).toEqual(new Set(["123456", "actions/checkout@v4"]));
    expect(lf.get("123456")?.sha).toBe("a".repeat(40));
  });
});

describe("decode grammar (rule 7)", () => {
  const accepted: ReadonlyArray<readonly [string, string]> = [
    ["2026-04-09T14:30:00+00:00", "2026-04-09T14:30:00.000Z"],
    ['"2026-04-09T14:30:00+00:00"', "2026-04-09T14:30:00.000Z"],
    ['"2026-04-09T14:30:00Z"', "2026-04-09T14:30:00.000Z"],
    ['"2026-04-09T14:30:00.123456+00:00"', "2026-04-09T14:30:00.000Z"],
  ];
  it.each(accepted)("accepts %s", (literal, iso) => {
    const path = join(tmp, "lock.yml");
    writeFileSync(path, lockDoc(literal));
    expect(readLockfile(path).get("actions/checkout@v4")?.resolvedAt.toISOString()).toBe(iso);
  });

  const rejected: readonly string[] = [
    "2026-04-09", // bare date
    '"2026-04-09"', // quoted date
    '"April 9, 2026"', // non-ISO
    '"2026/04/09"', // non-ISO
    '"2026-04-09T14:30:00"', // quoted, naive
    "2026-04-09T14:30:00", // bare, naive
    '"2026-04-09T14:30:00+02:00"', // explicit non-UTC offset
    // This port already rejected all of the following (TIMESTAMP_RE is the
    // reference side); the Python peer's `datetime.fromisoformat` accepted
    // every one of them on its own, and the pre-fix implementation therefore
    // silently accepted them too -- docs/issues/23 item 3. Pinned here so a
    // regression in either port's regex shows up as a parity break.
    '"2026-04-09 14:30:00+00:00"', // space separator, not T
    '"2026-04-09T14:30:00+0000"', // offset without a colon
    '"2026-04-09T14:30:00+00"', // offset with no minutes
    '"2026-04-09T14:30:00,123456+00:00"', // comma decimal separator
    '"20260409T143000+0000"', // basic format, no separators
    '"2026-04-09T14:30:00+00:00:00"', // offset carrying seconds
    '"2026-04-09T14:30:00-00:00"', // negative-zero offset
  ];
  it.each(rejected)("rejects %s", (literal) => {
    const path = join(tmp, "lock.yml");
    writeFileSync(path, lockDoc(literal));
    expect(() => readLockfile(path)).toThrow(LockfileError);
    expect(() => readLockfile(path)).toThrow(/resolved_at/);
  });
});

describe("decode grammar fixture (rule 7, one shared file)", () => {
  // fixtures/expected/lockfile_space_separator_rejected.yml pins the
  // space-separator form (accepted by Python's `datetime.fromisoformat`
  // alone, rejected by the shared `TIMESTAMP_RE` -- docs/issues/23 item 3)
  // as an actual on-disk document, read by both ports, rather than only as
  // an in-process literal. Flipping the space to `T` (one byte) makes the
  // fixture a valid timestamp and the read no longer throws, so the test
  // goes from a pass to a failure -- proof the fixture is load-bearing.
  it("rejects the golden space-separator document", () => {
    expect(() =>
      readLockfile(resolve(EXPECTED_DIR, "lockfile_space_separator_rejected.yml")),
    ).toThrow(/resolved_at/);
  });
});

describe("readLockfile error mode", () => {
  const notMappings: readonly string[] = [
    "just-a-string\n", // top-level scalar
    "- a\n- b\n", // top-level sequence
    "0\n", // top-level int
    '""\n', // top-level empty string
    "false\n", // top-level bool
  ];
  it.each(notMappings)("throws LockfileError on top-level %j", (document) => {
    const path = join(tmp, "lock.yml");
    writeFileSync(path, document);
    expect(() => readLockfile(path)).toThrow(LockfileError);
    expect(() => readLockfile(path)).toThrow(/mapping/);
  });

  it("throws LockfileError on a YAML syntax error", () => {
    const path = join(tmp, "lock.yml");
    writeFileSync(path, "pins:\n  - [unclosed\n");
    expect(() => readLockfile(path)).toThrow(LockfileError);
  });

  it("returns an empty lockfile for an empty document", () => {
    const path = join(tmp, "lock.yml");
    writeFileSync(path, "");
    expect(readLockfile(path).size).toBe(0);
  });

  it("returns an empty lockfile for a missing file", () => {
    expect(readLockfile(join(tmp, "nope.yml")).size).toBe(0);
  });
});
