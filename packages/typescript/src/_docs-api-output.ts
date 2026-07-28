// Hand-synced with the index.ts barrel — index.ts is the source of truth.
/**
 * YAML serialization and raw value escape hatch.
 * @packageDocumentation
 */
export { toYaml, toYamlFile, toData } from "./emitter/yaml-writer.js";
export type { ToDataOptions, CommentNode } from "./emitter/yaml-writer.js";
export { raw } from "./models/_base.js";
