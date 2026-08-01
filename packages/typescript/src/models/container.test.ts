import { describe, it, expect } from "vitest";
import { container, service } from "./container.js";
import { toData } from "../emitter/yaml-writer.js";

describe("container", () => {
  it("creates a container with image only", () => {
    const c = container({ image: "node:20" });
    expect(toData(c)).toEqual({ image: "node:20" });
    expect(c.kind).toBe("container");
  });

  it("creates a container with all fields", () => {
    const c = container({
      image: "node:20",
      credentials: { username: "user", password: "pass" },
      env: { NODE_ENV: "test" },
      ports: ["8080:80", 443],
      volumes: ["/data:/data"],
      options: "--cpus 2",
    });
    expect(toData(c)).toEqual({
      image: "node:20",
      credentials: { username: "user", password: "pass" },
      env: { NODE_ENV: "test" },
      ports: ["8080:80", 443],
      volumes: ["/data:/data"],
      options: "--cpus 2",
    });
  });
});

describe("service", () => {
  it("has kind set to service", () => {
    const s = service({ image: "postgres:15" });
    expect(s.kind).toBe("service");
  });

  it("creates a service with image, env, and ports", () => {
    const s = service({
      image: "redis:7",
      env: { REDIS_PASSWORD: "secret" },
      ports: [6379],
    });
    expect(toData(s)).toEqual({
      image: "redis:7",
      env: { REDIS_PASSWORD: "secret" },
      ports: [6379],
    });
  });
});

describe("container/service key order", () => {
  it("both share the container key order (distinct kinds)", () => {
    // The two specs differ only in `kind`; they share one `fieldMap` *object*,
    // and since a fieldMap's declaration order is the emission order, sharing
    // the object is what makes the two kinds emit the same keys in the same
    // sequence. This used to compare `spec.order`, which stopped being a
    // payload — comparing the two `"explicit"` strings would have passed for
    // every pair of specs in the port.
    const c = container({ image: "node:20" });
    const s = service({ image: "node:20" });
    expect(c.kind).toBe("container");
    expect(s.kind).toBe("service");
    expect(c.spec.fieldMap).toBe(s.spec.fieldMap);
  });
});
