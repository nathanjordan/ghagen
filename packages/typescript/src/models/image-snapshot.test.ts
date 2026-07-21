import { describe, it, expect } from "vitest";
import { imageSnapshot, IMAGE_SNAPSHOT_SPEC } from "./image-snapshot.js";
import { job } from "./job.js";
import { isModel } from "./_base.js";
import { modelToYamlMap, toYaml } from "../emitter/yaml-writer.js";
import { workflow } from "./workflow.js";

describe("imageSnapshot", () => {
  it("creates a mapping-syntax model with image name and version", () => {
    const s = imageSnapshot({ imageName: "custom-ubuntu", version: "1.2" });
    expect(s.data).toEqual({ "image-name": "custom-ubuntu", version: "1.2" });
    expect(s.kind).toBe("imageSnapshot");
    expect(s.spec).toBe(IMAGE_SNAPSHOT_SPEC);
  });

  it("maps imageName to image-name", () => {
    const s = imageSnapshot({ imageName: "img" });
    expect(s.data).toHaveProperty("image-name", "img");
    expect(s.data).not.toHaveProperty("imageName");
  });

  it("omits version when not provided", () => {
    const s = imageSnapshot({ imageName: "img" });
    expect(s.data).not.toHaveProperty("version");
  });
});

describe("job snapshot field", () => {
  it("passes a string snapshot through untouched (string syntax)", () => {
    const j = job({ runsOn: "ubuntu-latest", snapshot: "custom-ubuntu" });
    expect(j.data.snapshot).toBe("custom-ubuntu");
  });

  it("promotes an inline object to an ImageSnapshot model (mapping syntax)", () => {
    const j = job({
      runsOn: "ubuntu-latest",
      snapshot: { imageName: "custom-ubuntu", version: "1.0" },
    });
    expect(isModel(j.data.snapshot)).toBe(true);
    expect((j.data.snapshot as { kind: string }).kind).toBe("imageSnapshot");
  });

  it("leaves a pre-built ImageSnapshot model untouched", () => {
    const s = imageSnapshot({ imageName: "img" });
    const j = job({ runsOn: "ubuntu-latest", snapshot: s });
    expect(j.data.snapshot).toBe(s);
  });

  it("orders snapshot immediately after container", () => {
    const j = job({
      runsOn: "ubuntu-latest",
      container: "python:3.13",
      snapshot: "custom-ubuntu",
    });
    const keys = modelToYamlMap(j).items.map((p) => (p.key as { value: string }).value);
    expect(keys.indexOf("snapshot")).toBe(keys.indexOf("container") + 1);
  });
});

describe("imageSnapshot emission", () => {
  function emit(snapshot: unknown): string {
    const w = workflow({
      name: "S",
      on: { push: { branches: ["main"] } },
      jobs: {
        build: job({ runsOn: "ubuntu-latest", snapshot: snapshot as never, steps: [] }),
      },
    });
    return toYaml(w, { header: null });
  }

  it("emits the mapping syntax", () => {
    const yaml = emit({ imageName: "custom-ubuntu", version: "1.0" });
    expect(yaml).toContain("snapshot:");
    expect(yaml).toContain("image-name: custom-ubuntu");
    expect(yaml).toContain("version: '1.0'");
  });

  it("emits the string syntax", () => {
    const yaml = emit("custom-ubuntu");
    expect(yaml).toContain("snapshot: custom-ubuntu");
  });
});
