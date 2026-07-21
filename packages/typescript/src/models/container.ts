import type { Container as SchemaContainer } from "../schema/workflow-types.generated.js";
import { buildModel, extractMeta } from "./_base.js";
import type { WithMeta, ModelSpec, ContainerModel, ServiceModel } from "./_base.js";

/**
 * Input properties for defining a container used in a GitHub Actions job.
 *
 * Containers run the job or provide services alongside it. See
 * {@link container} and {@link service} for the corresponding factories.
 */
export interface ContainerInput {
  /** Docker image to use, e.g. `"node:20"` or `"ghcr.io/org/image:tag"`. */
  image: string;
  /** Credentials for authenticating to a private container registry. */
  credentials?: { username?: string; password?: string };
  /** Environment variables to set inside the container. */
  env?: Record<string, string>;
  /** Ports to expose from the container to the host (e.g. `[8080, "5432:5432"]`). */
  ports?: Array<string | number>;
  /** Volumes to mount into the container (Docker `-v` syntax). */
  volumes?: string[];
  /** Additional `docker create` options passed as a single string. */
  options?: string;
}

const CONTAINER_FIELD_MAP = {
  image: "image",
  credentials: "credentials",
  env: "env",
  ports: "ports",
  volumes: "volumes",
  options: "options",
} satisfies Record<keyof ContainerInput, keyof SchemaContainer>;

const CONTAINER_ORDER = ["image", "credentials", "env", "ports", "volumes", "options"];

/** Serialization spec for {@link ContainerModel}. */
export const CONTAINER_SPEC: ModelSpec = {
  kind: "container",
  fieldMap: CONTAINER_FIELD_MAP,
  order: CONTAINER_ORDER,
};

/** Serialization spec for {@link ServiceModel} (identical shape, distinct kind). */
export const SERVICE_SPEC: ModelSpec = {
  kind: "service",
  fieldMap: CONTAINER_FIELD_MAP,
  order: CONTAINER_ORDER,
};

/**
 * Create a container model for use as a job-level container.
 *
 * The returned model maps to the `jobs.<job_id>.container` key in a
 * GitHub Actions workflow YAML.
 *
 * @param input - Container configuration and optional metadata.
 * @returns A branded {@link ContainerModel}.
 *
 * @example
 * ```ts
 * const pg = container({
 *   image: "postgres:16",
 *   env: { POSTGRES_PASSWORD: "postgres" },
 *   ports: ["5432:5432"],
 * });
 * ```
 */
export function container(input: WithMeta<ContainerInput>): ContainerModel {
  const [data, meta] = extractMeta(input);
  return buildModel<ContainerModel>(CONTAINER_SPEC, data as Record<string, unknown>, meta);
}

/**
 * Create a service container model.
 *
 * Service containers run alongside the job and are accessible via their
 * key in `jobs.<job_id>.services`. The input shape is identical to
 * {@link container}, but the returned model is branded as a
 * {@link ServiceModel} so it can only be placed in the `services` map.
 *
 * @param input - Container configuration and optional metadata.
 * @returns A branded {@link ServiceModel}.
 *
 * @example
 * ```ts
 * const redis = service({
 *   image: "redis:7",
 *   ports: ["6379:6379"],
 * });
 * ```
 */
export function service(input: WithMeta<ContainerInput>): ServiceModel {
  const [data, meta] = extractMeta(input);
  return buildModel<ServiceModel>(SERVICE_SPEC, data as Record<string, unknown>, meta);
}
