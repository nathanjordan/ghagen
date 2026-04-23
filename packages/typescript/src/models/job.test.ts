import { describe, it, expect } from "vitest";
import { job, strategy, matrix, concurrency, defaults, environment } from "./job.js";
import { isModel } from "./_base.js";
import { step } from "./step.js";
import { permissions } from "./permissions.js";
import {
  JOB_KEY_ORDER,
  STRATEGY_KEY_ORDER,
  MATRIX_KEY_ORDER,
  CONCURRENCY_KEY_ORDER,
  DEFAULTS_KEY_ORDER,
  ENVIRONMENT_KEY_ORDER,
} from "../emitter/key-order.js";

describe("job", () => {
  it("creates a basic job with runsOn and steps", () => {
    const s = step({ run: "echo hi" });
    const j = job({ runsOn: "ubuntu-latest", steps: [s] });
    expect(j.data["runs-on"]).toBe("ubuntu-latest");
    expect(j.data.steps).toEqual([s]);
  });

  it("maps runsOn to runs-on", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    expect(j.data).toHaveProperty("runs-on");
    expect(j.data).not.toHaveProperty("runsOn");
  });

  it("handles needs as a string", () => {
    const j = job({ runsOn: "ubuntu-latest", needs: "build", steps: [] });
    expect(j.data.needs).toBe("build");
  });

  it("handles needs as an array", () => {
    const j = job({ runsOn: "ubuntu-latest", needs: ["build", "lint"], steps: [] });
    expect(j.data.needs).toEqual(["build", "lint"]);
  });

  it("maps if_ to if", () => {
    const j = job({ runsOn: "ubuntu-latest", if_: "always()", steps: [] });
    expect(j.data["if"]).toBe("always()");
    expect(j.data).not.toHaveProperty("if_");
  });

  it("maps with_ to with", () => {
    const j = job({ uses: "org/repo/.github/workflows/ci.yml@main", with_: { foo: "bar" } });
    expect(j.data["with"]).toEqual({ foo: "bar" });
    expect(j.data).not.toHaveProperty("with_");
  });

  it("maps timeoutMinutes to timeout-minutes", () => {
    const j = job({ runsOn: "ubuntu-latest", timeoutMinutes: 30, steps: [] });
    expect(j.data["timeout-minutes"]).toBe(30);
    expect(j.data).not.toHaveProperty("timeoutMinutes");
  });

  it("maps continueOnError to continue-on-error", () => {
    const j = job({ runsOn: "ubuntu-latest", continueOnError: true, steps: [] });
    expect(j.data["continue-on-error"]).toBe(true);
    expect(j.data).not.toHaveProperty("continueOnError");
  });

  it("supports uses with secrets inherit for reusable workflows", () => {
    const j = job({ uses: "org/repo/.github/workflows/ci.yml@main", secrets: "inherit" });
    expect(j.data.uses).toBe("org/repo/.github/workflows/ci.yml@main");
    expect(j.data.secrets).toBe("inherit");
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

  it("has correct kind and keyOrder", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [] });
    expect(j.kind).toBe("job");
    expect(j.keyOrder).toEqual(JOB_KEY_ORDER);
  });
});

describe("strategy", () => {
  it("maps failFast to fail-fast", () => {
    const s = strategy({ failFast: false });
    expect(s.data["fail-fast"]).toBe(false);
    expect(s.data).not.toHaveProperty("failFast");
  });

  it("maps maxParallel to max-parallel", () => {
    const s = strategy({ maxParallel: 3 });
    expect(s.data["max-parallel"]).toBe(3);
    expect(s.data).not.toHaveProperty("maxParallel");
  });

  it("auto-wraps matrix_ plain object with matrix()", () => {
    const s = strategy({ matrix_: { os: ["ubuntu-latest", "macos-latest"] } });
    expect(isModel(s.data.matrix)).toBe(true);
  });

  it("has correct kind and keyOrder", () => {
    const s = strategy({ failFast: false });
    expect(s.kind).toBe("strategy");
    expect(s.keyOrder).toEqual(STRATEGY_KEY_ORDER);
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
    expect(m.data.os).toEqual(["ubuntu-latest"]);
    expect(m.data.node).toEqual([18, 20]);
    expect(m.data.include).toEqual([{ os: "windows-latest", node: 20 }]);
    expect(m.data.exclude).toEqual([{ os: "ubuntu-latest", node: 18 }]);
    expect(m.kind).toBe("matrix");
    expect(m.keyOrder).toEqual(MATRIX_KEY_ORDER);
  });
});

describe("concurrency", () => {
  it("maps cancelInProgress to cancel-in-progress", () => {
    const c = concurrency({ group: "ci", cancelInProgress: true });
    expect(c.data.group).toBe("ci");
    expect(c.data["cancel-in-progress"]).toBe(true);
    expect(c.data).not.toHaveProperty("cancelInProgress");
    expect(c.kind).toBe("concurrency");
    expect(c.keyOrder).toEqual(CONCURRENCY_KEY_ORDER);
  });
});

describe("defaults", () => {
  it("maps run.workingDirectory to run.working-directory", () => {
    const d = defaults({ run: { shell: "bash", workingDirectory: "/app" } });
    const run = d.data.run as Record<string, unknown>;
    expect(run.shell).toBe("bash");
    expect(run["working-directory"]).toBe("/app");
    expect(run).not.toHaveProperty("workingDirectory");
    expect(d.kind).toBe("defaults");
    expect(d.keyOrder).toEqual(DEFAULTS_KEY_ORDER);
  });
});

describe("environment", () => {
  it("creates an environment with name and url", () => {
    const e = environment({ name: "production", url: "https://example.com" });
    expect(e.data.name).toBe("production");
    expect(e.data.url).toBe("https://example.com");
    expect(e.kind).toBe("environment");
    expect(e.keyOrder).toEqual(ENVIRONMENT_KEY_ORDER);
  });
});
