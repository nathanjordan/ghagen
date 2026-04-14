import type { WithMeta } from "../models/_base.js";
import type { StepInput } from "../models/step.js";
import { step } from "../models/step.js";
import type { StepModel } from "../models/_base.js";

/** Options for the checkout helper. */
export interface CheckoutOptions {
  /** Git ref to checkout. */
  ref?: string;
  /** Number of commits to fetch. Defaults to 1. */
  fetchDepth?: number;
  /** Action version. Defaults to "actions/checkout@v4". */
  version?: string;
}

/** Create an actions/checkout step. */
export function checkout(
  options?: WithMeta<CheckoutOptions>,
): StepModel {
  const { ref, fetchDepth = 1, version = "actions/checkout@v4", ...meta } =
    (options ?? {}) as CheckoutOptions & Record<string, unknown>;
  const with_: Record<string, string | number | boolean> = {};
  if (fetchDepth !== undefined) with_["fetch-depth"] = fetchDepth;
  if (ref !== undefined) with_["ref"] = ref;
  return step({
    name: "Checkout",
    uses: version,
    with_: Object.keys(with_).length > 0 ? with_ : undefined,
    ...meta,
  });
}

/** Options for the setup-node helper. */
export interface SetupNodeOptions {
  /** Node.js version string. */
  version: string;
  /** Registry URL for package publishing. */
  registryUrl?: string;
  /** Action version. Defaults to "actions/setup-node@v4". */
  actionVersion?: string;
}

/** Create an actions/setup-node step. */
export function setupNode(
  options: WithMeta<SetupNodeOptions>,
): StepModel {
  const {
    version,
    registryUrl,
    actionVersion = "actions/setup-node@v4",
    ...meta
  } = options as SetupNodeOptions & Record<string, unknown>;
  const with_: Record<string, string | number | boolean> = {
    "node-version": version,
  };
  if (registryUrl !== undefined) with_["registry-url"] = registryUrl;
  return step({
    name: "Set up Node.js",
    uses: actionVersion,
    with_,
    ...meta,
  });
}

/** Options for the setup-python helper. */
export interface SetupPythonOptions {
  /** Python version string. */
  version: string;
  /** Action version. Defaults to "actions/setup-python@v5". */
  actionVersion?: string;
}

/** Create an actions/setup-python step. */
export function setupPython(
  options: WithMeta<SetupPythonOptions>,
): StepModel {
  const {
    version,
    actionVersion = "actions/setup-python@v5",
    ...meta
  } = options as SetupPythonOptions & Record<string, unknown>;
  return step({
    name: "Set up Python",
    uses: actionVersion,
    with_: { "python-version": version },
    ...meta,
  });
}
