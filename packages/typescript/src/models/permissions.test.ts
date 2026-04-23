import { describe, it, expect } from "vitest";
import { permissions } from "./permissions.js";
import { PERMISSIONS_KEY_ORDER } from "../emitter/key-order.js";

describe("permissions", () => {
  it("creates permissions with contents and pullRequests", () => {
    const p = permissions({ contents: "read", pullRequests: "write" });
    expect(p.data).toEqual({ contents: "read", "pull-requests": "write" });
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
    expect(Object.keys(p.data)).toHaveLength(13);
    expect(p.data.actions).toBe("read");
    expect(p.data.statuses).toBe("read");
  });

  it("maps idToken to id-token", () => {
    const p = permissions({ idToken: "write" });
    expect(p.data["id-token"]).toBe("write");
    expect(p.data).not.toHaveProperty("idToken");
  });

  it("maps pullRequests to pull-requests", () => {
    const p = permissions({ pullRequests: "read" });
    expect(p.data["pull-requests"]).toBe("read");
    expect(p.data).not.toHaveProperty("pullRequests");
  });

  it("maps repositoryProjects to repository-projects", () => {
    const p = permissions({ repositoryProjects: "write" });
    expect(p.data["repository-projects"]).toBe("write");
    expect(p.data).not.toHaveProperty("repositoryProjects");
  });

  it("maps securityEvents to security-events", () => {
    const p = permissions({ securityEvents: "read" });
    expect(p.data["security-events"]).toBe("read");
    expect(p.data).not.toHaveProperty("securityEvents");
  });

  it("omits undefined scopes", () => {
    const p = permissions({ contents: "read" });
    expect(Object.keys(p.data)).toEqual(["contents"]);
  });

  it("has correct kind and keyOrder", () => {
    const p = permissions({ contents: "read" });
    expect(p.kind).toBe("permissions");
    expect(p.keyOrder).toEqual(PERMISSIONS_KEY_ORDER);
  });
});
