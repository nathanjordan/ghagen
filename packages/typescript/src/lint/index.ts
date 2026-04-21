/** ghagen lint — rule-based validation of Workflow models. */

export { type LintConfig, type LoadLintConfigResult, loadLintConfig } from "./config.js";
export { runLint } from "./engine.js";
export { formatGithub, formatHuman, formatJson } from "./output.js";
export {
  type Severity,
  type SourceLocation,
  type Violation,
  SEVERITY_VALUES,
} from "./violation.js";
export {
  ALL_RULES,
  type Rule,
  type RuleContext,
  type RuleMeta,
  rule,
  makeRuleContext,
  checkDuplicateStepIds,
  checkMissingPermissions,
  checkMissingTimeout,
  checkUnpinnedActions,
} from "./rules/index.js";
