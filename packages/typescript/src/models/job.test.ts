import { describe, it, expect } from "vitest";
import { job, strategy, matrix, concurrency, defaults, environment } from "./job.js";
import { isModel } from "./_base.js";
import { toData } from "../emitter/yaml-writer.js";
import { step } from "./step.js";
import { permissions } from "./permissions.js";

describe("job", () => {
  it("creates a basic job with runsOn and steps", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [step({ run: "echo hi" })] });
    expect(toData(j)).toEqual({ "runs-on": "ubuntu-latest", steps: [{ run: "echo hi" }] });
  });

  it("maps runsOn to runs-on", () => {
    const data = toData(job({ runsOn: "ubuntu-latest", steps: [] })) as Record<string, unknown>;
    expect(data).toHaveProperty("runs-on");
    expect(data).not.toHaveProperty("runsOn");
  });

  it("handles needs as a string", () => {
    const data = toData(job({ runsOn: "ubuntu-latest", needs: "build", steps: [] })) as Record<
      string,
      unknown
    >;
    expect(data.needs).toBe("build");
  });

  it("handles needs as an array", () => {
    const data = toData(
      job({ runsOn: "ubuntu-latest", needs: ["build", "lint"], steps: [] }),
    ) as Record<string, unknown>;
    expect(data.needs).toEqual(["build", "lint"]);
  });

  it("maps if_ to if", () => {
    const data = toData(job({ runsOn: "ubuntu-latest", if_: "always()", steps: [] })) as Record<
      string,
      unknown
    >;
    expect(data["if"]).toBe("always()");
    expect(data).not.toHaveProperty("if_");
  });

  it("maps with_ to with", () => {
    const data = toData(
      job({ uses: "org/repo/.github/workflows/ci.yml@main", with_: { foo: "bar" } }),
    ) as Record<string, unknown>;
    expect(data["with"]).toEqual({ foo: "bar" });
    expect(data).not.toHaveProperty("with_");
  });

  it("maps timeoutMinutes to timeout-minutes", () => {
    const data = toData(job({ runsOn: "ubuntu-latest", timeoutMinutes: 30, steps: [] })) as Record<
      string,
      unknown
    >;
    expect(data["timeout-minutes"]).toBe(30);
    expect(data).not.toHaveProperty("timeoutMinutes");
  });

  it("maps continueOnError to continue-on-error", () => {
    const data = toData(
      job({ runsOn: "ubuntu-latest", continueOnError: true, steps: [] }),
    ) as Record<string, unknown>;
    expect(data["continue-on-error"]).toBe(true);
    expect(data).not.toHaveProperty("continueOnError");
  });

  it("supports uses with secrets inherit for reusable workflows", () => {
    const data = toData(
      job({ uses: "org/repo/.github/workflows/ci.yml@main", secrets: "inherit" }),
    ) as Record<string, unknown>;
    expect(data.uses).toBe("org/repo/.github/workflows/ci.yml@main");
    expect(data.secrets).toBe("inherit");
  });

  it("auto-wraps permissions plain object into a model", () => {
    const j = job({ runsOn: "ubuntu-latest", permissions: { contents: "read" }, steps: [] });
    expect(isModel(j.data.permissions)).toBe(true);
  });

  it("auto-wraps strategy plain object into a model", () => {
    const j = job({ runsOn: "ubuntu-latest", strategy: { failFast: false }, steps: [] });
    expect(isModel(j.data.strategy)).toBe(true);
  });

  it("auto-wraps concurrency plain object into a model", () => {
    const j = job({
      runsOn: "ubuntu-latest",
      concurrency: { group: "ci-${{ github.ref }}", cancelInProgress: true },
      steps: [],
    });
    expect(isModel(j.data.concurrency)).toBe(true);
  });

  it("auto-wraps defaults plain object into a model", () => {
    const j = job({
      runsOn: "ubuntu-latest",
      defaults: { run: { shell: "bash" } },
      steps: [],
    });
    expect(isModel(j.data.defaults)).toBe(true);
  });

  it("auto-wraps container plain object into a model", () => {
    const j = job({
      runsOn: "ubuntu-latest",
      container: { image: "node:20" },
      steps: [],
    });
    expect(isModel(j.data.container)).toBe(true);
  });

  it("auto-wraps services plain objects into service models, strings pass through", () => {
    const j = job({
      runsOn: "ubuntu-latest",
      services: {
        db: { image: "postgres:15", ports: [5432] },
        redis: "redis:7",
      },
      steps: [],
    });
    const services = j.data.services as Record<string, unknown>;
    expect(isModel(services.db)).toBe(true);
    expect(services.redis).toBe("redis:7");
  });

  it("passes through pre-built models unchanged", () => {
    const p = permissions({ contents: "read" });
    const j = job({ runsOn: "ubuntu-latest", permissions: p, steps: [] });
    expect(j.data.permissions).toBe(p);
  });

  it("passes through permissions as read-all string", () => {
    const j = job({ runsOn: "ubuntu-latest", permissions: "read-all", steps: [] });
    expect(j.data.permissions).toBe("read-all");
  });

  it("passes through concurrency as a string", () => {
    const j = job({ runsOn: "ubuntu-latest", concurrency: "ci-group", steps: [] });
    expect(j.data.concurrency).toBe("ci-group");
  });

  it("has correct kind", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    expect(j.kind).toBe("job");
  });
});

describe("strategy", () => {
  it("maps failFast to fail-fast", () => {
    const data = toData(strategy({ failFast: false })) as Record<string, unknown>;
    expect(data["fail-fast"]).toBe(false);
    expect(data).not.toHaveProperty("failFast");
  });

  it("maps maxParallel to max-parallel", () => {
    const data = toData(strategy({ maxParallel: 3 })) as Record<string, unknown>;
    expect(data["max-parallel"]).toBe(3);
    expect(data).not.toHaveProperty("maxParallel");
  });

  it("auto-wraps matrix_ plain object with matrix()", () => {
    const s = strategy({ matrix_: { os: ["ubuntu-latest", "macos-latest"] } });
    expect(isModel(s.data.matrix)).toBe(true);
  });

  it("has correct kind", () => {
    expect(strategy({ failFast: false }).kind).toBe("strategy");
  });
});

describe("matrix", () => {
  it("stores include, exclude, and custom axis keys", () => {
    const m = matrix({
      os: ["ubuntu-latest"],
      node: [18, 20],
      include: [{ os: "windows-latest", node: 20 }],
      exclude: [{ os: "ubuntu-latest", node: 18 }],
    });
    expect(toData(m)).toEqual({
      os: ["ubuntu-latest"],
      node: [18, 20],
      include: [{ os: "windows-latest", node: 20 }],
      exclude: [{ os: "ubuntu-latest", node: 18 }],
    });
    expect(m.kind).toBe("matrix");
  });
});

describe("concurrency", () => {
  it("maps cancelInProgress to cancel-in-progress", () => {
    const c = concurrency({ group: "ci", cancelInProgress: true });
    const data = toData(c) as Record<string, unknown>;
    expect(data.group).toBe("ci");
    expect(data["cancel-in-progress"]).toBe(true);
    expect(data).not.toHaveProperty("cancelInProgress");
    expect(c.kind).toBe("concurrency");
  });
});

describe("defaults", () => {
  it("maps run.workingDirectory to run.working-directory", () => {
    const d = defaults({ run: { shell: "bash", workingDirectory: "/app" } });
    const run = (toData(d) as Record<string, unknown>).run as Record<string, unknown>;
    expect(run.shell).toBe("bash");
    expect(run["working-directory"]).toBe("/app");
    expect(run).not.toHaveProperty("workingDirectory");
    expect(d.kind).toBe("defaults");
  });
});

describe("environment", () => {
  it("creates an environment with name and url", () => {
    const e = environment({ name: "production", url: "https://example.com" });
    expect(toData(e)).toEqual({ name: "production", url: "https://example.com" });
    expect(e.kind).toBe("environment");
  });
});
