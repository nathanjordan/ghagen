/**
 * Auto-dedent utilities for multiline script strings.
 *
 * The heavy lifting is delegated to the `dedent` npm package. This
 * module re-exports it and manages the module-level auto-dedent flag
 * that controls whether `step({ run: ... })` values are automatically
 * dedented at construction time.
 *
 * NOTE: `autoDedent` is module-level mutable state. It is not safe for
 * concurrent App instances with different configs. Fine for ghagen's
 * single-threaded CLI usage.
 */

export { default as dedent } from "dedent";

/**
 * Module-level flag controlling whether `step({ run: ... })` values are
 * auto-dedented at construction time. Defaults to true. Set via
 * `setAutoDedent(false)` or `[options] auto_dedent = false` in
 * `.ghagen.yml`.
 */
let autoDedentFlag = true;

/** Read the current auto-dedent flag. */
export function getAutoDedent(): boolean {
  return autoDedentFlag;
}

/** Set the module-level auto-dedent flag. */
export function setAutoDedent(value: boolean): void {
  autoDedentFlag = value;
}
