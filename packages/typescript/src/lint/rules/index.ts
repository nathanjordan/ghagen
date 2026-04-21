/** Built-in lint rules for ghagen workflows. */

import type { Rule } from "./_base.js";
import { checkDuplicateStepIds } from "./duplicate-step-ids.js";
import { checkMissingPermissions } from "./missing-permissions.js";
import { checkMissingTimeout } from "./missing-timeout.js";
import { checkUnpinnedActions } from "./unpinned-actions.js";

export { type Rule, type RuleContext, type RuleMeta, rule, makeRuleContext } from "./_base.js";
export {
  checkDuplicateStepIds,
  checkMissingPermissions,
  checkMissingTimeout,
  checkUnpinnedActions,
};

/** All built-in rules, in the order they should run. */
export const ALL_RULES: readonly Rule[] = [
  checkMissingPermissions,
  checkUnpinnedActions,
  checkMissingTimeout,
  checkDuplicateStepIds,
];
