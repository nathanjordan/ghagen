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

  it("returns an empty report when there are no refs", async () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        on: { push: { branches: ["main"] } },
        jobs: { test: job({ runsOn: "ubuntu-latest", steps: [step({ run: "echo hi" })] }) },
      }),
      "ci.yml",
    );
    const client = new GitHubClient(new FakeTransport({}));

    const report = await upgrade(app, client, new Set(), { mode: "all", apply: true });

    expect(report.versionBumps).toEqual([]);
    expect(report.lockfileStale).toEqual([]);
    expect(report.changedFiles).toEqual([]);
  });
});
