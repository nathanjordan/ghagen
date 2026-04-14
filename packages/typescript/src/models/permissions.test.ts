import { describe, it, expect } from "vitest";
import { permissions } from "./permissions.js";
import { PERMISSIONS_KEY_ORDER } from "../emitter/key-order.js";

describe("permissions", () => {
  it("creates permissions with contents and pullRequests", () => {
    const p = permissions({ contents: "read", pullRequests: "write" });
    expect(p._data).toEqual({ contents: "read", "pull-requests": "write" });
  });

  it("handles all 13 scopes", () => {
    const p = permissions({
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
    });
    expect(Object.keys(p._data)).toHaveLength(13);
    expect(p._data.actions).toBe("read");
    expect(p._data.statuses).toBe("read");
  });

  it("maps idToken to id-token", () => {
    const p = permissions({ idToken: "write" });
    expect(p._data["id-token"]).toBe("write");
    expect(p._data).not.toHaveProperty("idToken");
  });

  it("maps pullRequests to pull-requests", () => {
    const p = permissions({ pullRequests: "read" });
    expect(p._data["pull-requests"]).toBe("read");
    expect(p._data).not.toHaveProperty("pullRequests");
  });

  it("maps repositoryProjects to repository-projects", () => {
    const p = permissions({ repositoryProjects: "write" });
    expect(p._data["repository-projects"]).toBe("write");
    expect(p._data).not.toHaveProperty("repositoryProjects");
  });

  it("maps securityEvents to security-events", () => {
    const p = permissions({ securityEvents: "read" });
    expect(p._data["security-events"]).toBe("read");
    expect(p._data).not.toHaveProperty("securityEvents");
  });

  it("omits undefined scopes", () => {
    const p = permissions({ contents: "read" });
    expect(Object.keys(p._data)).toEqual(["contents"]);
  });

  it("has correct _kind and _keyOrder", () => {
    const p = permissions({ contents: "read" });
    expect(p._kind).toBe("permissions");
    expect(p._keyOrder).toEqual(PERMISSIONS_KEY_ORDER);
  });
});
