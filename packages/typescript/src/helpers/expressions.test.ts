import { describe, it, expect } from "vitest";
import { expr, secrets, github, vars } from "./expressions.js";

describe("expr", () => {
  it("wraps a simple context reference", () => {
    expect(expr`github.ref`).toBe("${{ github.ref }}");
  });

  it("wraps a function call", () => {
    expect(expr`always()`).toBe("${{ always() }}");
  });

  it("wraps an expression with operators", () => {
    expect(expr`github.ref == 'refs/heads/main'`).toBe(
      "${{ github.ref == 'refs/heads/main' }}",
    );
  });

  it("supports interpolation", () => {
    const v = "foo";
    expect(expr`secrets.${v}`).toBe("${{ secrets.foo }}");
  });
});

describe("secrets", () => {
  it("produces a GITHUB_TOKEN expression", () => {
    expect(secrets.GITHUB_TOKEN).toBe("${{ secrets.GITHUB_TOKEN }}");
  });

  it("produces a PYPI_TOKEN expression", () => {
    expect(secrets.PYPI_TOKEN).toBe("${{ secrets.PYPI_TOKEN }}");
  });
});

describe("github", () => {
  it("produces a github.ref expression", () => {
    expect(github.ref).toBe("${{ github.ref }}");
  });

  it("produces a github.event_name expression", () => {
    expect(github.event_name).toBe("${{ github.event_name }}");
  });
});

describe("vars", () => {
  it("produces a vars expression", () => {
    expect(vars.MY_VAR).toBe("${{ vars.MY_VAR }}");
  });
});
