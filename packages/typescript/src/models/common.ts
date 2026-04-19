/**
 * Supported shell types for `run` steps.
 *
 * Use `Raw<string>` to specify a shell type not covered by this union
 * (e.g., `raw("powershell")`).
 *
 * | Value      | Description            |
 * | ---------- | ---------------------- |
 * | `"bash"`   | Bash shell             |
 * | `"pwsh"`   | PowerShell Core        |
 * | `"python"` | Python interpreter     |
 * | `"sh"`     | POSIX shell            |
 * | `"cmd"`    | Windows Command Prompt |
 */
export type ShellType = "bash" | "pwsh" | "python" | "sh" | "cmd";

/**
 * Valid permission access levels for `GITHUB_TOKEN` scopes.
 *
 * | Value     | Description                        |
 * | --------- | ---------------------------------- |
 * | `"read"`  | Read-only access to the scope      |
 * | `"write"` | Read and write access to the scope |
 * | `"none"`  | No access to the scope             |
 */
export type PermissionLevel = "read" | "write" | "none";
