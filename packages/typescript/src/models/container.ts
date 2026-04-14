import type { Container as SchemaContainer } from "../generated/workflow-types.js";
import type { ContainerModel, ServiceModel, WithMeta } from "./_base.js";
import { createModel, extractMeta, mapFields } from "./_base.js";
import { CONTAINER_KEY_ORDER } from "../emitter/key-order.js";

export interface ContainerInput {
  image: string;
  credentials?: { username?: string; password?: string };
  env?: Record<string, string>;
  ports?: Array<string | number>;
  volumes?: string[];
  options?: string;
}

const CONTAINER_FIELD_MAP = {
  image: "image",
  credentials: "credentials",
  env: "env",
  ports: "ports",
  volumes: "volumes",
  options: "options",
} as const satisfies Record<keyof ContainerInput, keyof SchemaContainer>;

export function container(input: WithMeta<ContainerInput>): ContainerModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, CONTAINER_FIELD_MAP);
  return createModel("container", yamlData, meta, CONTAINER_KEY_ORDER) as ContainerModel;
}

export function service(input: WithMeta<ContainerInput>): ServiceModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, CONTAINER_FIELD_MAP);
  return createModel("service", yamlData, meta, CONTAINER_KEY_ORDER) as ServiceModel;
}
