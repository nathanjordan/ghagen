/**
 * Tagged template literal for GitHub Actions expressions.
 *
 * @example
 * ```typescript
 * step({ if_: expr`github.ref == 'refs/heads/main'` })
 * // produces: if: "${{ github.ref == 'refs/heads/main' }}"
 * ```
 */
export function expr(strings: TemplateStringsArray, ...values: unknown[]): string {
  const inner = String.raw(strings, ...values);
  return `\${{ ${inner} }}`;
}

/**
 * Proxy for accessing secrets as expressions.
 *
 * @example
 * ```typescript
 * step({ env: { TOKEN: secrets.GITHUB_TOKEN } })
 * // produces: TOKEN: "${{ secrets.GITHUB_TOKEN }}"
 * ```
 */
export const secrets: Record<string, string> = new Proxy({} as Record<string, string>, {
  get(_, key: string) {
    return `\${{ secrets.${key} }}`;
  },
});

/**
 * Proxy for accessing GitHub context values as expressions.
 *
 * @example
 * ```typescript
 * step({ env: { REF: github.ref } })
 * // produces: REF: "${{ github.ref }}"
 * ```
 */
export const github: Record<string, string> = new Proxy({} as Record<string, string>, {
  get(_, key: string) {
    return `\${{ github.${key} }}`;
  },
});

/**
 * Proxy for accessing environment variable expressions.
 *
 * @example
 * ```typescript
 * step({ run: `echo ${vars.MY_VAR}` })
 * // produces: run: "echo ${{ vars.MY_VAR }}"
 * ```
 */
export const vars: Record<string, string> = new Proxy({} as Record<string, string>, {
  get(_, key: string) {
    return `\${{ vars.${key} }}`;
  },
});
