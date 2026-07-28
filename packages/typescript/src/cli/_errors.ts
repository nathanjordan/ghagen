/** CLI-local error type. A non-zero exit is a CLI concern, so this lives here. */

/**
 * Error thrown by CLI commands to signal a non-zero exit code.
 *
 * When caught by the top-level CLI runner, `exitCode` is forwarded to
 * `process.exit()` and `message` (if non-empty) is written to stderr.
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
