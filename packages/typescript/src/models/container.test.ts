import { describe, it, expect } from "vitest";
import { container, service } from "./container.js";
import { CONTAINER_KEY_ORDER } from "../emitter/key-order.js";

describe("container", () => {
  it("creates a container with image only", () => {
    const c = container({ image: "node:20" });
    expect(c._data).toEqual({ image: "node:20" });
    expect(c._kind).toBe("container");
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
    expect(c._data.image).toBe("node:20");
    expect(c._data.credentials).toEqual({ username: "user", password: "pass" });
    expect(c._data.env).toEqual({ NODE_ENV: "test" });
    expect(c._data.ports).toEqual(["8080:80", 443]);
    expect(c._data.volumes).toEqual(["/data:/data"]);
    expect(c._data.options).toBe("--cpus 2");
  });
});

describe("service", () => {
  it("has _kind set to service", () => {
    const s = service({ image: "postgres:15" });
    expect(s._kind).toBe("service");
  });

  it("creates a service with image, env, and ports", () => {
    const s = service({
      image: "redis:7",
      env: { REDIS_PASSWORD: "secret" },
      ports: [6379],
    });
    expect(s._data.image).toBe("redis:7");
    expect(s._data.env).toEqual({ REDIS_PASSWORD: "secret" });
    expect(s._data.ports).toEqual([6379]);
  });
});

describe("container/service key order", () => {
  it("both use CONTAINER_KEY_ORDER", () => {
    const c = container({ image: "node:20" });
    const s = service({ image: "node:20" });
    expect(c._keyOrder).toEqual(CONTAINER_KEY_ORDER);
    expect(s._keyOrder).toEqual(CONTAINER_KEY_ORDER);
  });
});
