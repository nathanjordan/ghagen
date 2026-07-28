import { describe, it, expect } from "vitest";
import { permissions } from "./permissions.js";
import { toData } from "../emitter/yaml-writer.js";

describe("permissions", () => {
  it("creates permissions with contents and pullRequests", () => {
    expect(toData(permissions({ contents: "read", pullRequests: "write" }))).toEqual({
      contents: "read",
      "pull-requests": "write",
    });
  });

  it("handles all 13 scopes", () => {
    const data = toData(
      permissions({
        actions: "read",
        checks: "write",
        contents: "read",
        deployments: "write",
        discussions: "read",
        idToken: "write",
        issues: "read",
        packages: "write",
        pages: "read",
        pullRequests: "write",
        repositoryProjects: "read",
        securityEvents: "write",
        statuses: "read",
      }),
    ) as Record<string, unknown>;
    expect(Object.keys(data)).toHaveLength(13);
    expect(data.actions).toBe("read");
    expect(data.statuses).toBe("read");
  });

  it("maps idToken to id-token", () => {
    const data = toData(permissions({ idToken: "write" })) as Record<string, unknown>;
    expect(data["id-token"]).toBe("write");
    expect(data).not.toHaveProperty("idToken");
  });

  it("maps pullRequests to pull-requests", () => {
    const data = toData(permissions({ pullRequests: "read" })) as Record<string, unknown>;
    expect(data["pull-requests"]).toBe("read");
    expect(data).not.toHaveProperty("pullRequests");
  });

  it("maps repositoryProjects to repository-projects", () => {
    const data = toData(permissions({ repositoryProjects: "write" })) as Record<string, unknown>;
    expect(data["repository-projects"]).toBe("write");
    expect(data).not.toHaveProperty("repositoryProjects");
  });

  it("maps securityEvents to security-events", () => {
    const data = toData(permissions({ securityEvents: "read" })) as Record<string, unknown>;
    expect(data["security-events"]).toBe("read");
    expect(data).not.toHaveProperty("securityEvents");
  });

  it("omits undefined scopes", () => {
    expect(
      Object.keys(toData(permissions({ contents: "read" })) as Record<string, unknown>),
    ).toEqual(["contents"]);
  });

  it("has correct kind", () => {
    expect(permissions({ contents: "read" }).kind).toBe("permissions");
  });
});
