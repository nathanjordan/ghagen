# TypeScript pagination breaks on a non-array body; Python has no peer guard

**Status:** open — from round 2

`packages/typescript/src/pin/github.ts:189-191`:

```ts
if (!Array.isArray(body)) break;
```

Python's paging loop has no equivalent. Under a malformed page the two ports diverge: TypeScript
stops and returns what it has, Python raises.

Left out of round 2 deliberately — hotfix H5 (`JSONDecodeError` → `ResolveError`) covers the
_malformed JSON_ case in Python, and proposal 16 lifts transport policy into the `HttpClient`
interface. Whether "a 200 whose body is the wrong shape" is a transport error or a resolve error is
a decision that belongs with 16's landed interface, not ahead of it.
