/** CLI-local error type. A non-zero exit is a CLI concern, so this lives here. */

/**
 * Error thrown by CLI commands to signal a non-zero exit code.
 *
 * When caught by the top-level CLI runner, `exitCode` is what `main()` returns
 * and `message` (if non-empty) is written to stderr. `main()` owns the exit
 * code end to end; the bin shim only assigns it to `process.exitCode`.
 */
export class CliError extends Error {
  /** Process exit code returned when this error propagates to the CLI entry point. */
  readonly exitCode: number;
  /**
   * @param message - Human-readable error text written to stderr (pass `""` for silent exits).
   * @param exitCode - Process exit code (default `1`).
   */
  constructor(message: string, exitCode = 1) {
    super(message);
    this.name = "CliError";
    this.exitCode = exitCode;
  }
}
