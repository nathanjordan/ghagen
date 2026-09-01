/**
 * Unit tests for the pin engine (pin / checkSync / upgrade).
 *
 * `checkSync` needs no client; `pin` and `upgrade` are driven through a
 * `GitHubClient` backed by a canned `FakeTransport` (no network) plus tmp dirs.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { App } from "../app.js";
import { workflow } from "../models/workflow.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import { GitHubClient, type HttpResponse } from "./github.js";
import { Lockfile, readLockfile, writeLockfile } from "./lockfile.js";
import { checkSync, pin, upgrade } from "./engine.js";
import { FakeTransport, canned } from "./transport-contract.js";
import { EXPECTED_DIR } from "../paths.js";

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-engine-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

function appWithRefs(root: string, ...uses: string[]): App {
  const app = new App({ root });
  app.addWorkflow(
    workflow({
      name: "CI",
      on: { push: { branches: ["main"] } },
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: uses.map((u) => step({ uses: u })),
        }),
      },
    }),
    "ci.yml",
  );
  return app;
}

/** An App whose only step is a `run:` — no pinnable `uses` refs. */
function appWithoutRefs(root: string): App {
  const app = new App({ root });
  app.addWorkflow(
    workflow({
      name: "CI",
      on: { push: { branches: ["main"] } },
      jobs: { test: job({ runsOn: "ubuntu-latest", steps: [step({ run: "echo hi" })] }) },
    }),
    "ci.yml",
  );
  return app;
}

function writeLock(root: string, pins: Record<string, string>): void {
  const lf = new Lockfile();
  for (const [uses, sha] of Object.entries(pins)) {
    lf.set(uses, { sha, resolvedAt: new Date("2026-04-09T00:00:00Z") });
  }
  writeLockfile(lf, join(root, ".ghagen.lock.yml"));
}

function commit(sha: string): HttpResponse {
  return canned({ object: { type: "commit", sha } });
}

function tags(...names: string[]): HttpResponse {
  return canned(names.map((n) => ({ ref: `refs/tags/${n}` })));
}

// ---- checkSync (no client) ----

describe("checkSync()", () => {
  it("reports in sync when the lockfile covers every ref", () => {
    writeLock(tmp, { "actions/checkout@v4": "a".repeat(40) });
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const report = checkSync(app, { prune: true });
    expect(report.inSync).toBe(true);
    expect(report.missing).toEqual([]);
    expect(report.extra).toEqual([]);
  });

  it("reports missing entries", () => {
    writeLock(tmp, {});
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const report = checkSync(app, { prune: true });
    expect(report.inSync).toBe(false);
    expect(report.missing).toEqual(["actions/checkout@v4"]);
    expect(report.extra).toEqual([]);
  });

  it("reports extra entries when pruning", () => {
    writeLock(tmp, {
      "actions/checkout@v4": "a".repeat(40),
      "actions/stale@v1": "b".repeat(40),
    });
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const report = checkSync(app, { prune: true });
    expect(report.inSync).toBe(false);
    expect(report.extra).toEqual(["actions/stale@v1"]);
  });

  it("ignores extra entries without prune", () => {
    writeLock(tmp, {
      "actions/checkout@v4": "a".repeat(40),
      "actions/stale@v1": "b".repeat(40),
    });
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const report = checkSync(app, { prune: false });
    expect(report.inSync).toBe(true);
    expect(report.extra).toEqual([]);
  });
});

// ---- pin ----

describe("pin()", () => {
  it("resolves unpinned refs, writes, and prunes", async () => {
    const sha = "c".repeat(40);
    writeLock(tmp, {
      "actions/setup-node@v4": "d".repeat(40),
      "actions/stale@v1": "e".repeat(40),
    });
    const app = appWithRefs(tmp, "actions/checkout@v4", "actions/setup-node@v4");
    const client = new GitHubClient(new FakeTransport({ "git/ref/tags/v4": commit(sha) }));

    const report = await pin(app, client, { update: false, prune: true });

    expect(report.resolved.map((r) => r.uses)).toEqual(["actions/checkout@v4"]);
    expect(report.resolved[0]!.sha).toBe(sha);
    expect(report.pruned).toBe(1);
    expect(report.written).toBe(true);
    expect(report.upToDate).toBe(false);

    const lockfile = readLockfile(join(tmp, ".ghagen.lock.yml"));
    expect(lockfile.get("actions/checkout@v4")?.sha).toBe(sha);
    expect(lockfile.has("actions/stale@v1")).toBe(false);
  });

  it("reports up to date when nothing changes", async () => {
    writeLock(tmp, { "actions/checkout@v4": "a".repeat(40) });
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const client = new GitHubClient(new FakeTransport({}));

    const report = await pin(app, client, { update: false, prune: true });

    expect(report.resolved).toEqual([]);
    expect(report.pruned).toBe(0);
    expect(report.written).toBe(false);
    expect(report.upToDate).toBe(true);
  });
});

// ---- upgrade ----

describe("upgrade()", () => {
  it("detects a version bump without applying", async () => {
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const source = join(tmp, "wf.ts");
    writeFileSync(source, 'step({ uses: "actions/checkout@v4" });\n');
    const client = new GitHubClient(new FakeTransport({ "git/refs/tags": tags("v4", "v5") }));

    const report = await upgrade(app, client, new Set([source]), {
      mode: "versions",
      apply: false,
    });

    expect(report.versionBumps).toHaveLength(1);
    const bump = report.versionBumps[0]!;
    expect(bump.uses).toBe("actions/checkout@v4");
    expect(bump.latest).toBe("v5");
    expect(bump.severity).toBe("major");
    expect(bump.source_files).toContain(source);
    expect(report.changedFiles).toEqual([]);
    expect(readFileSync(source, "utf8")).toContain("actions/checkout@v4");
  });

  it("applies a version bump to the source file", async () => {
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const source = join(tmp, "wf.ts");
    writeFileSync(source, 'step({ uses: "actions/checkout@v4" });\n');
    const client = new GitHubClient(new FakeTransport({ "git/refs/tags": tags("v4", "v5") }));

    const report = await upgrade(app, client, new Set([source]), {
      mode: "versions",
      apply: true,
    });

    expect(report.changedFiles).toEqual([source]);
    expect(readFileSync(source, "utf8")).toContain("actions/checkout@v5");
  });

  // Python's counterpart is test_cli/test_deps.py::TestUpgradeApply's
  // multi-repo case (`_mock_list_tags`, `:156-162`) — the only multi-repo
  // upgrade() coverage on either port before docs/issues/16. That test drives
  // the CLI with a mocked `GitHubClient.list_tags`; this one drives the engine
  // directly against the shared canned transport (proposal 16), one entry per
  // repo, to prove a second loop iteration over a distinct repo is exercised.
  it("detects and applies version bumps across more than one repository", async () => {
    const app = appWithRefs(tmp, "actions/checkout@v4", "actions/setup-python@v5");
    const source = join(tmp, "wf.ts");
    writeFileSync(
      source,
      'step({ uses: "actions/checkout@v4" });\nstep({ uses: "actions/setup-python@v5" });\n',
    );
    const client = new GitHubClient(
      new FakeTransport({
        "repos/actions/checkout/git/refs/tags": tags("v1", "v2", "v3", "v4", "v5", "v6", "v7"),
        "repos/actions/setup-python/git/refs/tags": tags("v4", "v5", "v5.1.0", "v6", "v7"),
      }),
    );

    const report = await upgrade(app, client, new Set([source]), {
      mode: "versions",
      apply: true,
    });

    expect(report.versionBumps.map((b) => b.uses)).toEqual([
      "actions/checkout@v4",
      "actions/setup-python@v5",
    ]);
    expect(report.changedFiles).toEqual([source]);
    const content = readFileSync(source, "utf8");
    expect(content).toContain("actions/checkout@v7");
    expect(content).toContain("actions/setup-python@v7");
  });

  // A four-segment tag is a version tag, end to end, in both ports. The shared
  // grammar (schema/tag-grammar.yml) accepts arity > 3, so v4.1.2.3 is a real
  // upgrade candidate. This is the source-file mutation guard: before 14,
  // SemVer rejected the tag here and left the file untouched while Python
  // rewrote it.
  it("detects a bump to a divergent-shape tag", async () => {
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const source = join(tmp, "wf.ts");
    writeFileSync(source, 'step({ uses: "actions/checkout@v4" });\n');
    const client = new GitHubClient(new FakeTransport({ "git/refs/tags": tags("v4", "v4.1.2.3") }));

    const report = await upgrade(app, client, new Set([source]), {
      mode: "versions",
      apply: false,
    });

    expect(report.versionBumps).toHaveLength(1);
    const bump = report.versionBumps[0]!;
    expect(bump.latest).toBe("v4.1.2.3");
    expect(bump.severity).toBe("minor");
  });

  it("detects a stale lockfile entry", async () => {
    const oldSha = "a".repeat(40);
    const newSha = "f".repeat(40);
    writeLock(tmp, { "actions/checkout@v4": oldSha });
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const client = new GitHubClient(new FakeTransport({ "git/ref/tags/v4": commit(newSha) }));

    const report = await upgrade(app, client, new Set(), { mode: "lockfile", apply: false });

    expect(report.lockfileStale).toHaveLength(1);
    const stale = report.lockfileStale[0]!;
    expect(stale.uses).toBe("actions/checkout@v4");
    expect(stale.current_sha).toBe(oldSha);
    expect(stale.latest_sha).toBe(newSha);
  });

  // Moved here from src/cli/deps.test.ts's non-semver test, which asserted it
  // through a JSON payload. The grammar itself is pinned by
  // schema/tag-grammar.yml (`main` -> null); this is the engine's half — a ref
  // the grammar rejects yields no bump even when newer version tags exist.
  it("never bumps a ref whose tag is not a version tag", async () => {
    const app = appWithRefs(tmp, "actions/checkout@main");
    const source = join(tmp, "wf.ts");
    writeFileSync(source, 'step({ uses: "actions/checkout@main" });\n');
    const client = new GitHubClient(
      new FakeTransport({ "git/refs/tags": tags("v1", "v2", "v3", "v4", "v5") }),
    );

    const report = await upgrade(app, client, new Set([source]), {
      mode: "versions",
      apply: true,
    });

    expect(report.versionBumps).toEqual([]);
    expect(report.changedFiles).toEqual([]);
    expect(readFileSync(source, "utf8")).toContain("actions/checkout@main");
  });

  it("returns an empty report when there are no refs", async () => {
    const app = appWithoutRefs(tmp);
    const client = new GitHubClient(new FakeTransport({}));

    const report = await upgrade(app, client, new Set(), { mode: "all", apply: true });

    expect(report.versionBumps).toEqual([]);
    expect(report.lockfileStale).toEqual([]);
    expect(report.changedFiles).toEqual([]);
  });

  // Moved from src/cli/deps.test.ts: it asserts an engine fact
  // (report.warnings), and a canned transport scripted to answer the tag list
  // with a 500 covers it without driving the command.
  it("continues with a warning when the tag API fails", async () => {
    const app = appWithRefs(tmp, "actions/checkout@v4");
    const client = new GitHubClient(
      new FakeTransport({
        "git/refs/tags": canned(
          { message: "boom" },
          { status: 500, statusText: "Internal Server Error" },
        ),
      }),
    );

    const report = await upgrade(app, client, new Set(), { mode: "versions", apply: false });

    expect(report.versionBumps).toEqual([]);
    expect(report.warnings).toHaveLength(1);
    expect(report.warnings[0]).toContain("failed to list tags for actions/checkout");
  });

  // Regression for docs/issues/23 item 1: repos used to be grouped for the
  // `listTags` sweep by `.sort((a, b) => a.localeCompare(b))`, which is
  // locale-dependent -- not just wrong for astral-plane/non-BMP keys but
  // actively non-reproducible: the same input can order differently on two
  // machines with different default locales. "Zulu/repo" < "apple/repo" by
  // code point (`Z` is 0x5A, `a` is 0x61) but every locale collation tested,
  // including the process's own default (en-US, asserted below so this test
  // fails loudly if that ever changes), orders them the other way --
  // dictionary order ignores case. versionBumps order follows the grouping
  // order, so it is the observable surface for this.
  it("groups repos by code point, not locale collation (non-reproducible across machines)", async () => {
    expect("Zulu/repo".localeCompare("apple/repo")).toBeGreaterThan(0); // apple < Zulu, locale-wise
    expect("Zulu/repo" < "apple/repo").toBe(true); // Zulu < apple, code-point-wise

    const app = appWithRefs(tmp, "Zulu/repo@v4", "apple/repo@v4");
    const client = new GitHubClient(
      new FakeTransport({
        "repos/Zulu/repo/git/refs/tags": tags("v4", "v5"),
        "repos/apple/repo/git/refs/tags": tags("v4", "v9"),
      }),
    );

    const report = await upgrade(app, client, new Set(), { mode: "versions", apply: false });

    const expected = readFileSync(join(EXPECTED_DIR, "pin_repo_group_order.txt"), "utf8")
      .split("\n")
      .filter((s) => s.length > 0);
    expect(report.versionBumps.map((b) => b.uses)).toEqual(expected);
  });
});

// ---- upgrade: what the run was asked to check ----

/**
 * `checkedVersions` / `checkedLockfile` are pure functions of `mode`. They
 * record what the run was *asked for*, so the renderer never re-derives it
 * from the CLI's `--mode`. "Asked for" is not "ran": with no lockfile
 * configured the lockfile stage is skipped and the flag stays true.
 */
describe("upgrade() checked flags", () => {
  const cases = [
    { mode: "versions", versions: true, lockfile: false },
    { mode: "lockfile", versions: false, lockfile: true },
    { mode: "all", versions: true, lockfile: true },
  ] as const;

  for (const { mode, versions, lockfile } of cases) {
    it(`reports checkedVersions=${versions} checkedLockfile=${lockfile} for --mode ${mode}`, async () => {
      const app = appWithRefs(tmp, "actions/checkout@v4");
      const client = new GitHubClient(new FakeTransport({ "git/refs/tags": tags("v4") }));

      const report = await upgrade(app, client, new Set(), { mode, apply: false });

      expect(report.checkedVersions).toBe(versions);
      expect(report.checkedLockfile).toBe(lockfile);
    });

    // The flags are set *before* the no-refs early return. This ordering is
    // the fact the whole renderer design turns on: a project with no pinnable
    // refs must render the same JSON key set as any other.
    it(`a no-refs report still reports the checked flags for --mode ${mode}`, async () => {
      const app = appWithoutRefs(tmp);
      const client = new GitHubClient(new FakeTransport({}));

      const report = await upgrade(app, client, new Set(), { mode, apply: true });

      expect(report.versionBumps).toEqual([]);
      expect(report.lockfileStale).toEqual([]);
      expect(report.checkedVersions).toBe(versions);
      expect(report.checkedLockfile).toBe(lockfile);
    });
  }

  it('is true without a lockfile — "asked for" is not "ran"', async () => {
    const app = new App({ root: tmp, lockfile: null });
    app.addWorkflow(
      workflow({
        name: "CI",
        on: { push: { branches: ["main"] } },
        jobs: {
          test: job({ runsOn: "ubuntu-latest", steps: [step({ uses: "actions/checkout@v4" })] }),
        },
      }),
      "ci.yml",
    );
    const client = new GitHubClient(new FakeTransport({}));

    const report = await upgrade(app, client, new Set(), { mode: "lockfile", apply: false });

    expect(report.checkedLockfile).toBe(true);
    expect(report.lockfileStale).toEqual([]);
  });
});
