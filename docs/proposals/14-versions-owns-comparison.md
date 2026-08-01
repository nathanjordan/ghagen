# 14 — `versions` owns its comparison

**Status:** proposed | **Ports:** both | **Effort:** L | **Depends on:** lands after **19** (both
`cli.md` pages' consolidated `## Exit codes`); lands before **17** (upgrade-report renderer). **No
order edge with 20** — the regions are disjoint in both ports.

_Effort raised M → L: the measured sweep (below) turns this from a tidy-up into a behaviour change
across 396 real upgrade scenarios in TypeScript, and the deliverable is a 50-row shared table that
both suites are rewritten against, two dependency removals with two lockfile regenerations, two CLI
doc pages, two `CONTEXT.md` files, an ADR amendment and a new ADR._

## Files involved

### Modified

| Path                                              | Lines | Role in this proposal                                                                                                               |
| ------------------------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/src/ghagen/pin/versions.py`      | 140   | Rewritten: keep the padded integer tuple, compare it, drop `packaging`; add `BumpSeverity`, `Bump` and `latest_bump`                |
| `packages/typescript/src/pin/versions.ts`         | 104   | Mirror rewrite; drop `semver`                                                                                                       |
| `packages/python/src/ghagen/pin/engine.py`        | 294   | `upgrade`'s versions stage collapses to one `latest_bump` call; two dead guards deleted; local `Severity` alias moves to `versions` |
| `packages/typescript/src/pin/engine.ts`           | 318   | Mirror                                                                                                                              |
| `packages/python/src/ghagen/pin/__init__.py`      | 58    | **Addition only** — the barrel carries no version symbol today; gains `BumpSeverity`, reaching the parity the TS barrel already has |
| `packages/typescript/src/pin/index.ts`            | 46    | **Deletion only** — `:22` already exports `type BumpSeverity`; the four symbols at `:23-26` go                                      |
| `packages/typescript/src/index.ts`                | 203   | **Deletion only** — same, `:182` already exports it; `:183-186` go                                                                  |
| `packages/python/tests/test_pin/test_versions.py` | 132   | Rewritten as a driver over the shared table; `packaging` import deleted                                                             |
| `packages/typescript/src/pin/versions.test.ts`    | 85    | Mirror; `semver` import deleted                                                                                                     |
| `packages/python/tests/test_pin/test_engine.py`   | 251   | One added `upgrade` case pinning a divergent-shape tag end to end                                                                   |
| `packages/typescript/src/pin/engine.test.ts`      | 242   | Mirror of that one case                                                                                                             |
| `pyproject.toml`                                  | 69    | Drop `packaging>=23` from `dependencies` (`:23`)                                                                                    |
| `uv.lock`                                         | 622   | Regenerate (`packaging` leaves `ghagen`'s `requires-dist` at `:102`; it stays resolved as pytest's transitive, `:389`)              |
| `packages/typescript/package.json`                | 76    | Drop `semver` (`:55`) and `@types/semver` (`:62`)                                                                                   |
| `packages/typescript/package-lock.json`           | 3202  | Regenerate (`semver` has exactly one dependent — the root package — so it leaves `node_modules` entirely)                           |
| `docs/src/content/docs/python/cli.md`             | 210   | Document the tag grammar under `ghagen deps upgrade` (currently undocumented)                                                       |
| `docs/src/content/docs/typescript/cli.md`         | 223   | Mirror                                                                                                                              |
| `packages/python/CONTEXT.md`                      | 114   | Pin glossary gains **Version tag** + **Bump** (after **PinEntry**, `:76`); one **Relationships** line                               |
| `packages/typescript/CONTEXT.md`                  | 119   | Mirror (after **PinEntry**, `:78`)                                                                                                  |
| `docs/adr/0006-pin-collects-parsed-refs.md`       | 20    | One-line amendment recording that the no-reparse rule covers tag parsing as well as ref parsing                                     |

### New

| Path                                           | Lines      | Role in this proposal                                                                                                                       |
| ---------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `schema/tag-grammar.yml`                       | new (~120) | The one shared `(tag → expected)` / `(current, available → latest, severity)` table — 33 parse rows + 17 compare rows — read by both suites |
| `docs/adr/0008-ghagen-owns-its-tag-grammar.md` | new (~30)  | Records that the accept-set and the total order are ghagen's, and that no third-party version library may return to the compare path        |

`0008` is the next free ADR number (`docs/adr/` holds `0001`–`0007`) and no sibling proposal claims it.

Deliberately **not** in the table: `packages/typescript/src/paths.ts` and `scripts/ghagen_schema/paths.py`.
The shared table lives in `schema/`, reached through `SCHEMA_DIR` — which is `REPO_ROOT/"schema"` in
**both** ports (`paths.py:32`, `paths.ts:38`). Neither file needs a line changed.

### Conflicts and ordering

- **`19 → 14` — order edge, on both `cli.md` pages.** 19 consolidates the three per-command
  `### Exit codes` tables; its deletions are `python/cli.md:114-120,136-142,179-185` and
  `typescript/cli.md:127-133,149-155,192-198`, each terminal within its section. My insertion is
  _inside_ `## ghagen deps upgrade`, above `:179` / `:192` — i.e. into the block 19 removes the tail
  of. **19 goes first**, conditional on 19 anchoring its consolidated `## Exit codes` at end-of-file;
  once it has landed my insertion is a clean append to the surviving section body.
- **`14 — 20` — file conflict on `packages/typescript/package.json` and `package-lock.json`, no
  order.** I delete `package.json:55` (`semver`, in `dependencies`) and `:62` (`@types/semver`, in
  `devDependencies`); 20 deletes `:57` (`zod`, same `dependencies` object). Three lines across two
  objects, five apart at the closest — mechanical. **`package-lock.json` is 3202 lines and does not
  merge**: whoever lands second discards its own lockfile diff and re-runs
  `npm install --package-lock-only --prefix packages/typescript` on top of the first one's result,
  rather than resolving a conflict. 20 documents the same interaction at `20` §Scope boundaries vs siblings.
- **No `20 → 14` order edge.** The engine regions are disjoint in both ports: 20's Python deletion
  (the dead `repo_tags_cache`) ends at `engine.py:238`, my first changed line is `:241`; 20's
  TypeScript region ends at `engine.ts:251`, my first changed line is `:254`. In particular
  **`engine.ts:243-249` — including the non-`ResolveError` rethrow at `:248` — is preserved verbatim
  by 20 and is not touched by me.** Either order works. 20 states the same at `20` §Problem.
- **`16 — 14` — file conflict on `pin/__init__.py` and both TypeScript barrels; hand-merge, do not
  serialize.** It is _not_ a shared edit of one import statement: `pin/__init__.py:15-21` is
  `from ghagen.pin.github import (…)` and only 16 edits it, while I add a separate new
  `from ghagen.pin.versions import BumpSeverity` statement inside the isort region `:3-31`. 17 and 18
  each add their own. The real collision is line-shift across that import region plus the genuinely
  shared alphabetical `__all__` at `:33-58`. Same hazard, larger, on the TypeScript barrels:
  `src/index.ts` has **7** claimants (09, 11, 14, 16, 17, 18, 20) and `src/pin/index.ts` has **5**
  (14, 16, 17, 18, 20).
- **`14 → 17` — order edge, alive.** I rewrite `test_versions.py` wholesale, invalidating 17's
  citations to `test_versions.py:45-46` and `:108-110`; 17 then adds `checked_versions` /
  `checked_lockfile` to the same report my added engine case asserts on. `14 — 17` is also a file
  conflict on `test_versions.py`, on `packages/python/tests/test_cli/test_deps.py` (17 rewrites it
  911 → ~250, `17` §Modified), and on `packages/python/tests/test_pin/test_engine.py`, where 17 asserts two
  new report flags and absorbs a case (`17` §Modified) while I add one `upgrade` case — different
  assertions in the same file, hand-merge.

## Problem

`parse_tag` / `parseTag` already does the whole job. It matches the tag with a hand-rolled regex,
splits the numeric part on `.`, rejects prefixed refs with fewer than two segments, and pads to
three. At that point it is holding a list of numeric strings that is a totally ordered value.
**Both ports then throw it away, re-join it into a string, and hand the string to a third-party
version library** — `packaging` (PEP 440) in Python, `semver` (SemVer 2.0.0) in TypeScript.

```python
# packages/python/src/ghagen/pin/versions.py:61,69-78
    segments = version_str.split(".")
    ...
    # Pad to three segments so ``v4`` → ``4.0.0``, ``v4.1`` → ``4.1.0``.
    while len(segments) < 3:
        segments.append("0")

    try:
        version = Version(".".join(segments))   # ← the parse is discarded here
    except InvalidVersion:
        return None

    return ParsedTag(tag=tag, prefix=prefix, version=version)
```

```ts
// packages/typescript/src/pin/versions.ts:35,43-53
  const segments = versionStr.split(".");
  ...
  // Pad to three segments so v4 → 4.0.0, v4.1 → 4.1.0.
  while (segments.length < 3) {
    segments.push("0");
  }

  try {
    const version = new SemVer(segments.join("."));   // ← the parse is discarded here
    return { tag, prefix, version };
  } catch {
    return null;
  }
```

The consequence is that **`ghagen`'s tag grammar is not `ghagen`'s**. The regex
(`versions.py:20-24`, `versions.ts:15`) proposes; two unrelated third-party grammars dispose, and
they dispose differently.

**Correction to the survey.** The brief describes `parse_tag` as extracting "three integers". It
does not: the regex's version group is `\d+(?:\.\d+)*`, and the pad loop only ever _appends_ — it
never truncates (`versions.py:70-71`, `versions.ts:44-46`). A four-segment tag yields a
four-element release. That detail _is_ the bug: PEP 440's release segment is
`[0-9]+(\.[0-9]+)*` — arbitrary arity — while SemVer 2.0.0 is exactly three. Everything below
follows from it.

### The divergence, measured

Both ports were run over the same inputs (throwaway scripts under `$TMPDIR`, not committed;
the TypeScript side imports `src/pin/versions.ts` directly under `tsx`). Of 30 hand-built tag
shapes, **9 diverge** — every one of them a shape the shared regex accepts and only one library
does:

| Input                                     | Python `parse_tag`                       | TS `parseTag`                             | Agree?                                     |
| ----------------------------------------- | ---------------------------------------- | ----------------------------------------- | ------------------------------------------ |
| `v1`                                      | `prefix=None, 1.0.0`                     | `prefix=null, 1.0.0`                      | yes                                        |
| `v1.2`                                    | `1.2.0`                                  | `1.2.0`                                   | yes                                        |
| `v1.2.3`                                  | `1.2.3`                                  | `1.2.3`                                   | yes                                        |
| `1.2.3`                                   | `1.2.3`                                  | `1.2.3`                                   | yes                                        |
| `v10.0.0`                                 | `10.0.0`                                 | `10.0.0`                                  | yes                                        |
| `v999999999999999.0.0`                    | `999999999999999.0.0`                    | `999999999999999.0.0`                     | yes (15 digits: the boundary, both accept) |
| **`v1.2.3.4`**                            | **`1.2.3.4`**                            | **`null`**                                | **no**                                     |
| **`v1.2.3.4.5`**                          | **`1.2.3.4.5`**                          | **`null`**                                | **no**                                     |
| **`v1.2.3.4.5.6`**                        | **`1.2.3.4.5.6`**                        | **`null`**                                | **no**                                     |
| **`v1.2.3.0`**                            | **`1.2.3.0`** (== `1.2.3` under PEP 440) | **`null`**                                | **no**                                     |
| **`v01.02.03`**                           | **`1.2.3`** (PEP 440 normalises)         | **`null`** (SemVer forbids leading zeros) | **no**                                     |
| **`v1.2.03`**                             | **`1.2.3`**                              | **`null`**                                | **no**                                     |
| **`v0000000000000001.0.0`**               | **`1.0.0`**                              | **`null`** (16 characters)                | **no**                                     |
| **`v9999999999999999.0.0`**               | **`9999999999999999.0.0`**               | **`null`** (16 digits)                    | **no**                                     |
| **`prefix-v1.2.3.4`**                     | **`prefix, 1.2.3.4`**                    | **`null`**                                | **no**                                     |
| `V1.2.3`                                  | `None`                                   | `null`                                    | yes                                        |
| `v1.2.3-rc1`                              | `None`                                   | `null`                                    | yes                                        |
| `v1.2.3+build`                            | `None`                                   | `null`                                    | yes                                        |
| `v2beta`                                  | `None`                                   | `null`                                    | yes                                        |
| `v1.0.0a0` / `v3.0.2-node.24` / `v6-beta` | `None`                                   | `null`                                    | yes                                        |
| `latest` / `main` / `master`              | `None`                                   | `null`                                    | yes                                        |
| `release/v1`                              | `None`                                   | `null`                                    | yes                                        |
| `release/v1.0.0`                          | `release, 1.0.0`                         | `release, 1.0.0`                          | yes                                        |
| `prefix-v1.0.0` / `prefix/v1.0.0`         | `prefix, 1.0.0`                          | `prefix, 1.0.0`                           | yes                                        |
| `actions-v2.1`                            | `actions, 2.1.0`                         | `actions, 2.1.0`                          | yes                                        |
| `""`                                      | `None`                                   | `null`                                    | yes                                        |

The nine divergences fall into exactly three classes, and all three are "the library re-litigating
the regex's decision":

1. **arity** — PEP 440 accepts any number of release segments; SemVer accepts three;
2. **leading zeros** — PEP 440 normalises `01` → `1`; SemVer rejects it;
3. **component width** — PEP 440 is unbounded; `semver` accepts a component of ≤ 15 _characters_ and
   rejects ≥ 16, which is why the zero-padded `v0000000000000001.0.0` (value 1) is rejected while
   `v999999999999999.0.0` (value ~10¹⁵) is accepted. The cap is on the literal, not the number.

### What a user sees — **live**, and reproduced end to end

`upgrade`'s versions stage feeds a repo's whole tag list through `find_latest_tag` and writes the
winner into the user's source files (`engine.py:241-259,286-292`; `engine.ts:254-271,303-315`).
So the divergence is not a report cosmetic — it is a **source-file mutation** difference. Same `App`,
same `FakeTransport` tag list `["v4","v4.1.2.3"]`, same ref `actions/checkout@v4`,
`mode="versions", apply=True`:

```
PYTHON version_bumps: [('actions/checkout@v4','v4','v4.1.2.3','minor')]  -> file rewritten
TS     versionBumps:  []                                                  -> file untouched
```

The same inputs, run through both ports' `find_latest_tag` / `classify_bump`:

| current ref | available tags              | Python verdict                    | TS verdict                          | Agree?                                          |
| ----------- | --------------------------- | --------------------------------- | ----------------------------------- | ----------------------------------------------- |
| `v1.2.3`    | `["v1.2.3.4"]`              | bump → `v1.2.3.4` (patch)         | up to date                          | **no**                                          |
| `v1.2.3.4`  | `["v1.2.4"]`                | bump → `v1.2.4` (patch)           | current ref unparseable → no result | **no**                                          |
| `v1`        | `["v1.2.3.4", "v1.1"]`      | bump → **`v1.2.3.4`** (minor)     | bump → **`v1.1`** (minor)           | **no — different tag written to the file**      |
| `v1.2.3`    | `["v1.2.4", "v1.3.0.1"]`    | bump → **`v1.3.0.1`** (**minor**) | bump → **`v1.2.4`** (**patch**)     | **no — different tag _and_ different severity** |
| `v2.1.6`    | `["v2.2", "v2.04"]`         | bump → **`v2.04`** (minor)        | bump → **`v2.2`** (minor)           | **no — this one is real; see below**            |
| `v0.9.0`    | `["v0000000000000001.0.0"]` | bump → that tag (major)           | up to date                          | **no**                                          |
| `v1.2.3`    | `["v1.2.03"]`               | up to date                        | up to date                          | yes (by accident: PEP 440 makes them equal)     |

Rows 3, 4 and 5 are the sharp ones. Both ports report _a_ bump, so neither warns; they simply
rewrite `uses:` to different versions. `severity` also feeds the report grouping the CLI renders and
the `fixtures/expected/upgrade_report.json` contract, so a `minor`/`patch` split propagates outward.

**Live or latent?** _Live_. It needs only an upstream repo whose tag list contains one four-segment
or zero-padded tag, and the tag list comes from GitHub, not from ghagen. Git imposes no version
grammar on tag names.

### How often — measured against the real registry

**Sweep:** every repo returned by GitHub code search for `topic:github-action`,
`topic:github-actions` and `topic:actions`, top-starred, 5 pages each — **1,306 repos, of which
1,116 publish tags**. Up to 300 tags per repo (3 API pages): **39,671 tag observations, 13,165
distinct tag strings.** Every tag was run through both ports' real `parseTag` / `parse_tag`.

- **382 distinct tags parse differently.** All 382 in one direction: **Python accepts, TypeScript
  rejects.** By shape: 265 arity > 3, 113 leading zeros, 4 both. **Zero** hit the digit-width class.
- **29 repos publish at least one such tag**, including `graalvm/setup-graalvm` (an official-vendor
  action), `super-linter/super-linter` (`v3.1.4.1`), `Homebrew/actions` (date tags
  `2026.07.29.1`), `tox-dev/tox` (`4.5.1.1`) and `diggerhq/digger` (`ui/v0.1.32.12`).
- Running **every** real tag of those 29 repos as `current` against its own repo's tag list gives
  **2,153 real upgrade scenarios, 396 of them divergent (18%)**:
  - **333** where Python bumps and TypeScript reports "up to date" — a silent no-op in one port;
  - **63**, across **7** repos, where **both ports bump and each writes a different tag into the
    user's file** — neither warns, and the reports disagree.

The seven silent-disagreement repos, one example scenario each:

| repo@ref                                     | Python writes                    | TypeScript writes     |
| -------------------------------------------- | -------------------------------- | --------------------- |
| `fastai/fastpages@v2.1.6`                    | `v2.04` (minor)                  | `v2.2` (minor)        |
| `Ash258/Scoop-GithubActions@1.0.2`           | `1.5.0.2` (minor)                | `1.0.3` (patch)       |
| `databrickslabs/cicd-templates@v1.0.10`      | `v011` (**major**)               | `v1.0.11` (**patch**) |
| `liudf0716/xfrpc@2.12.656`                   | `5.09.976` (major)               | `3.12.832` (major)    |
| `technote-space/get-diff-action@test/v6.1.2` | `test/v6.1.3.4228877157` (patch) | `test/v6.1.3` (patch) |
| `technote-space/toc-generator@test/v4.3.1`   | `test/v4.3.2.4208394694` (patch) | `test/v4.3.2` (patch) |
| `ones20250/Openwrt-AX6600@…-14.21.56`        | `…-19.05.24` (major)             | `…-18.30.42` (major)  |

And the one-sided cases, from the same sweep with each repo's full tag list:

| repo@ref                                    | Python                         | TypeScript |
| ------------------------------------------- | ------------------------------ | ---------- |
| `graalvm/setup-graalvm@v1.2.4.1`            | bump → `v1.6.3` (minor)        | up to date |
| `diggerhq/digger@v0.6.136.1`                | bump → `v0.6.148` (patch)      | up to date |
| `elgohr/Publish-Docker-Github-Action@3.02`  | bump → `v5` (**major**)        | up to date |
| `DoozyX/clang-format-lint-action@v0.18.1.1` | bump → `v0.20` (minor)         | up to date |
| `Bush2021/chrome_installer@150.0.7871.187`  | bump → `151.0.7922.72` (major) | up to date |

`databrickslabs/cicd-templates@v1.0.10` is the sharpest single row: `v011` normalises to `(11,0,0)`
under PEP 440, so Python calls it a **major** bump while TypeScript calls the same repo a **patch**.

So the architectural argument stands on both feet. The unowned interface is the deeper problem —
**the module's accept-set and its total order are defined by two third-party libraries that no test
observes and that Renovate (`renovate.json`, `config:recommended`) upgrades unattended**; a `semver`
minor that relaxes leading zeros, or a `packaging` release that tightens arity, silently changes
which `uses:` refs ghagen will rewrite, and no gate in this repo would notice. But the _symptom_ is
already out there, on 29 real repos and 396 real scenarios, today.

### Two more defects found while verifying

**A. The docstring at `versions.py:29-33` is half true and misleading where it matters.** Verbatim:

```python
    """A parsed tag — wraps a comparable version plus its optional prefix.

    Mirrors the TypeScript ``ParsedTag`` shape so the tag regex runs once
    (no separate prefix re-extraction).
    """
```

The _field_ shape does mirror: both records are `tag: str`, `prefix: str | None`,
`version: <opaque>` (`versions.py:35-42`; `versions.ts:18-25`). The "regex runs once" clause is
true inside `parse_tag`. But the field that carries all the behaviour — `version` — is a
`packaging.version.Version` on one side (`versions.py:41`) and a `semver.SemVer` on the other
(`versions.ts:24`), with different accept-sets and different orders. A docstring that says
"mirrors the TypeScript shape" is exactly the thing that stops a maintainer from checking whether
the two agree. **Verdict: the claim as written is not true of the member that matters; correct it
or make it true.** This proposal makes it true.

**B. Python's `except InvalidVersion` is unreachable; TypeScript's `catch` is not.**
`versions.py:75-76` guards a `Version()` call whose argument is always `\d+(\.\d+)*` with ≥ 3
components — every such string is a valid PEP 440 release. Verified empirically (8 segments, a
300-digit component, all-zeros: all accepted). So the Python branch is dead code. The
structurally identical `versions.ts:51-53` fires for all nine divergent shapes above, and for 382
of the 13,165 real tags in the sweep. Two ports, byte-parallel code, one dead branch and one hot
path — a direct symptom of "the grammar lives outside the module."

### The engine re-parses what `versions` already parsed — ADR-0006, one level down

`find_latest_tag` parses every candidate, finds the winner, and then returns a **string**
(`versions.py:100,140`; `versions.ts:77,103`). The engine must therefore parse twice more:

```python
# packages/python/src/ghagen/pin/engine.py:241-250
                latest_tag = find_latest_tag(ref.ref, tags)
                if latest_tag is None:
                    continue  # up to date or non-semver

                current_ver = parse_tag(ref.ref)
                latest_ver = parse_tag(latest_tag)
                if current_ver is None or latest_ver is None:
                    continue

                severity = classify_bump(current_ver.version, latest_ver.version)
```

`engine.ts:254-263` is line-for-line the same. Note what the guard at `engine.py:247-248` /
`engine.ts:260-262` is doing: `find_latest_tag` returns non-`None` **only** when
`parse_tag(current_ref)` succeeded (`versions.py:117-119`) and the winning candidate parsed
(`versions.py:125-127` skips anything that did not, and `best_tag` is only ever assigned inside
that loop, `versions.py:136-138`). Both re-parses are therefore guaranteed to succeed, and the
guard is **unreachable**. ADR-0006 states the rule this violates (`docs/adr/0006-…:6-7`):

> downstream pin engine stages consume typed refs and carry no `parse(...) is None` guards — they
> are unreachable.

ADR-0006 fixed exactly this shape at the `UsesRef` layer; `versions` reproduces it one layer down
for tags. This is not a new principle to argue for — it is an accepted one that was applied to the
wrong half of `pin`.

### Smaller parity gaps in the same module

- **The severity type is single-sourced in TS and duplicated in Python.** TS declares
  `BumpSeverity` at `versions.ts:57` and the engine imports it (`engine.ts:21`, used at
  `engine.ts:164`), and re-exports it from both barrels (`pin/index.ts:22`, `index.ts:182`) — the
  TypeScript half of this is already done and correct, and nothing in this proposal changes it.
  Python re-declares the identical union locally as `Severity` at `engine.py:32` (used at
  `engine.py:168`) while `classify_bump` spells it inline in its return annotation
  (`versions.py:83`) — and the name `BumpSeverity` does not exist in the Python port at all.
  Two literal lists that must stay equal, with nothing forcing it, under two different names.
- **`semver` leaks into the published TypeScript type surface — live packaging defect.**
  `semver` ships no `.d.ts` and declares no `types`/`typings` field; its types come from
  `@types/semver`, which sits in **`devDependencies`** (`package.json:62`) while `semver` itself is
  a runtime dependency (`package.json:55`). The built `dist/pin/versions.d.ts:8` reads
  `import { SemVer } from "semver";` and declares `readonly version: SemVer`, and
  `dist/index.d.ts:47` re-exports `ParsedTag` / `parseTag` / `classifyBump` / `findLatestTag` to
  the package root (`dist/` is a gitignored build artifact; line numbers are from a current `tsc`
  run). `package.json:29-34` publishes only `"." → dist/index.js`, so that root re-export _is_ the
  whole published surface. A consumer of `@ghagen/ghagen` who touches `ParsedTag` therefore
  references a type from a package with no type declarations installed. (Masked for consumers who
  set `skipLibCheck: true` — as this repo does, `tsconfig.json:15` — which is why it has gone
  unnoticed.) Python has the opposite problem: `ghagen.pin.__init__` exports **none** of
  `parse_tag` / `ParsedTag` / `classify_bump` / `find_latest_tag` / the severity type
  (`pin/__init__.py:33-58` has no version symbol at all), so the two ports' public pin surfaces do
  not match either way.
- **Neither suite tests a single divergent shape.** `test_versions.py` (132 lines, 27 tests) and
  `versions.test.ts` (85 lines, 17 tests) each cover `v4` / `v4.1` / `v4.1.2` / `4.1.2` / prefixed /
  `main` / `release/v1` — the _agreeing_ set, exclusively. Both also import the third-party version
  type directly into the test (`test_versions.py:5`, `versions.test.ts:2`), so the tests are written
  in the vocabulary of the dependency they are supposed to be insulating the port from. Nothing in
  either suite can fail when the ports disagree.

## Current interface

Python (`versions.py`):

```python
@dataclass(frozen=True)
class ParsedTag:
    tag: str
    prefix: str | None
    version: Version                      # packaging.version.Version — PEP 440 grammar & order

def parse_tag(tag: str) -> ParsedTag | None
def classify_bump(current: Version, latest: Version) -> Literal["major", "minor", "patch"]
def find_latest_tag(current_ref: str, available_tags: list[str]) -> str | None
```

TypeScript (`versions.ts`):

```ts
export interface ParsedTag {
  readonly tag: string;
  readonly prefix: string | null;
  readonly version: SemVer; // semver.SemVer — SemVer 2.0.0 grammar & order
}
export function parseTag(tag: string): ParsedTag | null;
export type BumpSeverity = "major" | "minor" | "patch";
export function classifyBump(current: SemVer, latest: SemVer): BumpSeverity;
export function findLatestTag(currentRef: string, availableTags: readonly string[]): string | null;
```

To use this module a caller must know: which tag shapes are accepted (undocumented — it is the
intersection of a local regex and a third-party grammar, and the answer differs by port); what the
ordering is on the accepted set (delegated, unstated, port-specific); that `find_latest_tag`
returns a string it already parsed, so the caller must re-parse; that the re-parse cannot fail but
the type says it can; and, in TypeScript, that `ParsedTag.version` is a class from a package the
consumer may not have types for. Three functions, five pieces of unwritten knowledge. **Shallow:
the interface is more complicated than the implementation.**

## Proposed interface

`versions` declares the grammar and owns the order. The release becomes the padded integer tuple
`parse_tag` already computed, comparison is tuple comparison, and the module exposes **one**
entry point for the engine.

### The declared grammar

A ref is a version tag iff it matches `^(?:(.+)[/-])?v?(\d+(?:\.\d+)*)$` — unchanged, this regex
stays the authority — **and**:

- when a prefix is present, the numeric part has ≥ 2 segments (unchanged: keeps `release/v1` a
  branch ref, which matters because this repo pins `pypa/gh-action-pypi-publish@release/v1`);
- **every segment, read as an integer, is ≤ 999 999 999 999 999** (10¹⁵ − 1).

The cap is stated on the **integer value**, not on the number of characters. This is deliberate and
it is the one place the wording has to be exact: the leading-zero rule makes padded segments legal,
so `v0000000000000001.0.0` is 16 characters but the value 1, and is **accepted**;
`v9999999999999999.0.0` is 16 digits with value 10¹⁶ − 1, and is **rejected**. A character-count
reading would reject the first, which is a different implementation. Both ports must implement the
value rule.

The **canonical release** is: parse each segment as an integer, pad with zeros to length 3, then
drop trailing zeros beyond index 2. `v4` → `(4,0,0)`; `v4.1` → `(4,1,0)`; `v1.2.3.4` → `(1,2,3,4)`;
`v1.2.3.0` → `(1,2,3)`; `v01.02.03` → `(1,2,3)`; `v2.04` → `(2,4,0)` (the segment is the _number_
4, then padded — not `(2,0,4)`). Ordering is tuple ordering, element-wise then by length. The
trailing-zero strip is what makes `v1.2.3.0 == v1.2.3` rather than greater, matching PEP 440's
zero-padding equality; without it, tuple comparison would invent a new answer.

The value cap is the one place this proposal _adds_ a rule rather than recovering one. It exists so
both ports can hold the release in a plain integer array (JS numbers are exact below 2⁵³;
999 999 999 999 999 < 9 007 199 254 740 991) without a bigint or a string-compare path. It is set
at the value `semver` already enforces incidentally for un-padded literals, so the change is
**declared where it used to be accidental**. **Zero of the 13,165 real tags in the sweep exceed it.**

### What actually changes, per shape

Every row measured against both ports at `e7a972c` and against a reference implementation of the
rule above. "Real tags" counts distinct tags in the 13,165-tag sweep.

| Shape                                     | Example                 | Python today                        | TS today   | After                         | Changes for                                                        | Real tags    |
| ----------------------------------------- | ----------------------- | ----------------------------------- | ---------- | ----------------------------- | ------------------------------------------------------------------ | ------------ |
| ≤ 3 segments, no padding, in range        | `v4`, `v1.2.3`          | `(1,2,3)`                           | `1.2.3`    | same                          | neither                                                            | 9,511        |
| arity > 3                                 | `v3.1.4.1`              | accept `(1,2,3,4)`                  | **reject** | accept                        | **TS**                                                             | 265          |
| leading zeros                             | `v2.04`, `0.06.251`     | accept, normalised                  | **reject** | accept, normalised            | **TS**                                                             | 113          |
| arity > 3 **and** leading zeros           | `2026.07.29.1`          | accept `(2026,7,29,1)`              | **reject** | accept                        | **TS**                                                             | 4            |
| prefixed, arity > 3                       | `ui/v0.1.32.12`         | accept                              | **reject** | accept                        | **TS**                                                             | (in the 265) |
| trailing-zero 4th segment                 | `v1.0.1.0`              | accept `(1,0,1,0)`, **== `v1.0.1`** | **reject** | accept `(1,0,1)`, == `v1.0.1` | **TS** (Python's _order_ is unchanged; only the canonical form is) | (in the 265) |
| zero-padded to ≥ 16 chars, value in range | `v0000000000000001.0.0` | accept `(1,0,0)`                    | **reject** | accept `(1,0,0)`              | **TS**                                                             | **0**        |
| segment value > 10¹⁵ − 1                  | `v9999999999999999.0.0` | **accept**                          | reject     | **reject**                    | **Python**                                                         | **0**        |
| prerelease / build / non-numeric          | `v1.2.3-rc1`, `main`    | reject                              | reject     | reject                        | neither                                                            | 3,272        |

Rolled up over the sweep:

- **Python's accept-set changes on 0 of 13,165 real tags**, and its `latest_bump` result changes on
  **0 of the 2,153** real upgrade scenarios in the 29 affected repos. Its only behaviour change is
  the value cap, whose real-world hit count is zero, plus the canonical-form change on
  trailing-zero tags, which is order-preserving by construction.
- **TypeScript's accept-set changes on 382 of 13,165 real tags** — all reject → accept — and its
  result changes on **396 of the 2,153** scenarios: **333** from "up to date" to a bump, and **63**
  from one bump to a different bump. Those 63 are the ones where the _written tag_ changes; the
  canonical example is `fastai/fastpages@v2.1.6`, where TypeScript moves from `v2.2` to `v2.04`.

This is a real behaviour change in TypeScript, adopting Python's answer in every case. That is the
proposal's position: the regex is the authority, and Python is the port that already honours it.

### Python

```python
BumpSeverity = Literal["major", "minor", "patch"]

@dataclass(frozen=True, order=True)
class ParsedTag:
    """A parsed version tag: its prefix and its canonical release."""
    prefix: str | None = field(compare=False)
    release: tuple[int, ...]        # len >= 3, no trailing zeros past index 2; compares directly
    tag: str = field(compare=False)  # the original string, preserved for rewriting the uses-site

@dataclass(frozen=True)
class Bump:
    """A newer tag for a ref, with everything the caller needs about it."""
    current: ParsedTag
    latest: ParsedTag
    severity: BumpSeverity

def parse_tag(tag: str) -> ParsedTag | None: ...

def latest_bump(current_ref: str, available_tags: Iterable[str]) -> Bump | None:
    """The newest same-prefix tag strictly newer than *current_ref*, classified.

    ``None`` when *current_ref* is not a version tag, or when nothing in
    *available_tags* is newer. Every returned ``Bump`` holds parsed values; no
    caller re-parses (ADR-0006).
    """
```

### TypeScript

```ts
export type BumpSeverity = "major" | "minor" | "patch";

export interface ParsedTag {
  readonly tag: string;
  readonly prefix: string | null;
  readonly release: readonly number[];
}
export interface Bump {
  readonly current: ParsedTag;
  readonly latest: ParsedTag;
  readonly severity: BumpSeverity;
}
export function parseTag(tag: string): ParsedTag | null;
export function latestBump(currentRef: string, availableTags: Iterable<string>): Bump | null;
```

`compareRelease(a, b)` (element-wise, then by length) is module-private in both ports —
`find_latest_tag` and `classify_bump` fold into `latest_bump` and stop being interface. **Note the
consequence for severity:** `latest_bump` filters candidates with `release <= current.release`
_before_ classifying, so `classify_bump(v, v)` becomes unreachable and equal versions produce **no
`Bump` at all** rather than a `"patch"` one. That is a deliberate contract change, and it is why one
existing assertion is deleted rather than migrated (see _Test impact_).

### The engine call site

```python
# engine.py — the four-call dance and both dead guards collapse
            for ref in repo_ref_list:
                bump = latest_bump(ref.ref, tags)
                if bump is None:
                    continue  # not a version tag, or already latest
                report.version_bumps.append(
                    VersionBump(
                        uses=ref.uses,
                        current=ref.ref,
                        latest=bump.latest.tag,
                        severity=bump.severity,
                        source_files=[str(p) for p in ref_locations.get(ref.uses, [])],
                    )
                )
```

`engine.ts:254-271` changes identically. `engine.py:32`'s local `Severity` alias is deleted and
`BumpSeverity` imported from `versions`, matching what TS already does at `engine.ts:21`.

### The shared table

**`schema/tag-grammar.yml`**, beside `schema/conformance-scopes.yml` (44 lines) and
`schema/conformance-gaps.yml` — the two files that already establish this pattern. `schema/` is the
repo's home for shared _tables_, and it is reached symmetrically: `SCHEMA_DIR` is
`REPO_ROOT / "schema"` in Python (`scripts/ghagen_schema/paths.py:32`) and
`resolve(REPO_ROOT, "schema")` in TypeScript (`packages/typescript/src/paths.ts:38`). Neither
`paths` module is touched, and neither port hardcodes a path.

(`fixtures/` is the wrong home: it holds golden _bytes_, and its `FIXTURES_DIR` constants disagree
across the ports — `paths.py:35` is `fixtures/`, `paths.ts:41` is `fixtures/expected/` — under the
identical doc comment. Putting a shared table there would have forced one port to route around the
asymmetry by hand. See _Risks & alternatives_.)

```yaml
# The declared tag grammar for `ghagen deps upgrade`. Read by:
#   - Python (packages/python/tests/test_pin/test_versions.py)
#   - TypeScript (packages/typescript/src/pin/versions.test.ts)
# Both suites assert they consumed every key, so a case added for one port
# cannot silently skip the other.
#
# `release` is the canonical release: each segment as an integer, padded to
# three, trailing zeros beyond index 2 dropped. Ordering is tuple ordering.
# A segment whose integer VALUE exceeds 999999999999999 is rejected; a
# zero-padded literal longer than that is not.

parse:
  # --- shapes both ports already agree on
  "v4": { prefix: null, release: [4, 0, 0] }
  "v4.1": { prefix: null, release: [4, 1, 0] }
  "1.2.3": { prefix: null, release: [1, 2, 3] }
  "prefix-v1.0.0": { prefix: prefix, release: [1, 0, 0] }
  "release/v1.0.0": { prefix: release, release: [1, 0, 0] }
  "actions-v2.1": { prefix: actions, release: [2, 1, 0] }
  "v999999999999999.0.0": { prefix: null, release: [999999999999999, 0, 0] } # at the cap
  "release/v1": null # prefixed + single segment -> branch ref
  "main": null
  "latest": null
  "V1.2.3": null # capital V is not the `v` prefix
  "v1.2.3-rc1": null
  "v1.2.3+build": null
  "v2beta": null
  "v1.0.0a0": null # real: pypa/gh-action-pypi-publish
  "v3.0.2-node.24": null # real: actions/deploy-pages
  "v6-beta": null # real: actions/checkout
  "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": null # a bare commit SHA is not a tag
  "": null

  # --- shapes the ports disagree on today (TS red before)
  "v1.2.3.4": { prefix: null, release: [1, 2, 3, 4] } # arity
  "v1.2.3.4.5": { prefix: null, release: [1, 2, 3, 4, 5] }
  "v1.2.3.4.5.6": { prefix: null, release: [1, 2, 3, 4, 5, 6] }
  "v1.2.3.0": { prefix: null, release: [1, 2, 3] } # trailing zero stripped
  "v01.02.03": { prefix: null, release: [1, 2, 3] } # leading zeros
  "v1.2.03": { prefix: null, release: [1, 2, 3] }
  "prefix-v1.2.3.4": { prefix: prefix, release: [1, 2, 3, 4] } # prefixed + arity
  "v0000000000000001.0.0": { prefix: null, release: [1, 0, 0] } # 16 chars, value 1: ACCEPTED
  "v2.04": { prefix: null, release: [2, 4, 0] } # real: fastai/fastpages
  "2026.07.29.1": { prefix: null, release: [2026, 7, 29, 1] } # real: Homebrew/actions
  "v3.1.4.1": { prefix: null, release: [3, 1, 4, 1] } # real: super-linter/super-linter
  "ui/v0.1.32.12": { prefix: ui, release: [0, 1, 32, 12] } # real: diggerhq/digger

  # --- shapes the ports disagree on today (Python red before)
  "v9999999999999999.0.0": null # value 10^16 - 1: over the cap
  "v99999999999999999999.0.0": null

compare:
  # --- TS red before
  - { current: "v1.2.3", available: ["v1.2.3.4"], latest: "v1.2.3.4", severity: patch }
  - { current: "v1", available: ["v1.2.3.4", "v1.1"], latest: "v1.2.3.4", severity: minor }
  - { current: "v1.2.3", available: ["v1.2.4", "v1.3.0.1"], latest: "v1.3.0.1", severity: minor }
  - { current: "v1.2.3.4", available: ["v1.2.4"], latest: "v1.2.4", severity: patch }
  - { current: "v2.1.6", available: ["v2.2", "v2.04"], latest: "v2.04", severity: minor } # fastai
  - {
      current: "v0.9.0",
      available: ["v0000000000000001.0.0"],
      latest: "v0000000000000001.0.0",
      severity: major,
    }

  # --- severity: all three values, and both precedence rules
  - { current: "v1.2.3", available: ["v2.0.0", "v1.5.0"], latest: "v2.0.0", severity: major } # major beats minor
  - { current: "v1.0.0", available: ["v1.0.1", "v1.1.1"], latest: "v1.1.1", severity: minor } # minor beats patch
  - { current: "v1.0.0", available: ["v1.0.1"], latest: "v1.0.1", severity: patch }

  # --- prefix filter and mixed lists
  - { current: "v4", available: ["release-v5", "v4.1"], latest: "v4.1", severity: minor }
  - {
      current: "release-v1.0.0",
      available: ["release-v1.1.0", "release-v2.0.0"],
      latest: "release-v2.0.0",
      severity: major,
    }
  - {
      current: "v1.0.0",
      available: ["v1.0.0", "v2.0.0", "main", "release/v1", "nightly"],
      latest: "v2.0.0",
      severity: major,
    }

  # --- no bump: equal after normalisation, nothing newer, nothing at all, unparseable current
  - { current: "v1.2.3", available: ["v1.2.03"], latest: null }
  - { current: "v1.2.3", available: ["v1.2.3.0"], latest: null }
  - { current: "v1.0.0", available: [], latest: null }
  - { current: "v3.0.0", available: ["v1.0.0", "v2.0.0"], latest: null }
  - { current: "main", available: ["v1", "v2"], latest: null }
```

**33 parse rows + 17 compare rows = 50 cases.** Measured red-before, by port:

|            | parse rows red                                                                      | compare rows red |
| ---------- | ----------------------------------------------------------------------------------- | ---------------- |
| TypeScript | **12**                                                                              | **6**            |
| Python     | **2** (accept-set: the two over-cap rows) + **1** (canonical form only: `v1.2.3.0`) | **0**            |

The `parse` map pins the accept-set and the canonical release; the `compare` list pins the order,
the prefix filter, and the severity classification in one shot. Each suite asserts it consumed every
key of both sections, mirroring the scope-key parity guard the conformance sweeps already use
(`packages/python/tests/test_schema/test_conformance.py`,
`packages/typescript/src/models/conformance.test.ts`).

## What sits behind the seam

`versions` becomes the module that answers, alone: _is this ref a version tag, which of two tags is
newer, and how big is the jump?_ Behind a two-function interface (`parse_tag`, `latest_bump`) it
holds the regex, the prefix rule, the padding and normalisation rule, the value cap, the total
order, the same-prefix filter, and the severity classification — all of it declared in one file per
port and pinned by one shared table for both.

**Leverage.** The engine's versions stage goes from four calls, two dead guards, and three
throwaway `ParsedTag`s per ref to one call and one `Bump`. No caller needs to know what a version
_is_.

**Locality.** "Does ghagen think `v1.2.3.4` is a version?" has today five answers to check: the
regex, the pad loop, PEP 440, SemVer 2.0.0, and whichever of those two libraries Renovate last
bumped. After: one table, and the two implementations that must satisfy it.

**Deletion test — `Bump`.** Delete it and both engines immediately re-grow `find_latest_tag` +
two `parse_tag` calls + `classify_bump` + the unreachable-`None` branch, at one site per port —
i.e. exactly today's code. It concentrates four calls into one and removes a provably-dead branch:
earned.

**Deletion test — `ParsedTag.release` as a tuple.** Delete it and the module must re-import a
version library to hold a comparable value, and the two ports re-diverge on the nine shapes above.
Earned — and note the _inverse_ deletion test, the one that matters most here: **delete
`packaging` and `semver` from this path and nothing reappears.** Every behaviour they provided that
ghagen actually uses (ordering three-or-more integers) is one tuple comparison; every behaviour
they provide that ghagen does _not_ want (prereleases, build metadata, PEP 440 epochs/dev/post
releases, `~`/`^` ranges, coercion) is unreachable, because the regex already rejects every input
that could exercise it. Both are pass-throughs with side effects. That is the whole proposal in one
sentence.

**Deletion test — `schema/tag-grammar.yml`.** Delete it and each port keeps its own hand-written
cases, which is the status quo: 132 + 85 lines with zero overlap on any divergent shape, and no
artifact anywhere that can fail when the ports disagree on 382 real tags. Earned — it is the only
thing in the repo that would catch a re-divergence.

## Migration plan

Pre-1.0, clean breaks, no shims. Lands **after** 19 (both `cli.md` pages) and **before** 17.

1. **Write `schema/tag-grammar.yml` first.** Every entry in it is a decision; getting them reviewed
   before any code moves is the point. The `parse` map's expected values are the current **Python**
   behaviour with exactly two exceptions, both called out in the file: the two over-cap rows
   (Python-side reject, zero real hits) and `v1.2.3.0`'s canonical form (order-preserving).
2. **Python `versions.py`:** replace `ParsedTag.version` with `release: tuple[int, ...]`, add the
   **value** cap and the trailing-zero strip, add `BumpSeverity` and `Bump`, fold `classify_bump`
   and `find_latest_tag` into `latest_bump`, delete the `packaging` import (`versions.py:14`) and
   the now-doubly-dead `except InvalidVersion` (`:75-76`). Rewrite the `ParsedTag` docstring
   (`versions.py:29-33`) so its "mirrors the TypeScript shape" claim is true of `release`, not just
   of the field names. Rewrite the module docstring (`versions.py:1-6`), which names
   `packaging.version.Version`.
3. **TypeScript `versions.ts`:** the mirror, including deleting the `semver` import (`:9`) and the
   module docstring's `semver.coerce` rationale (`versions.ts:1-7`), which stops being true.
4. **Both engines:** collapse the versions stage to `latest_bump` / `latestBump`; delete the
   unreachable guards (`engine.py:247-248`, `engine.ts:260-262`); delete `engine.py:32`'s
   `Severity` and import `BumpSeverity` from `versions`.
5. **Barrels — the two ports move in opposite directions here, and only one of them adds a line.**
   Python `pin/__init__.py` gains `from ghagen.pin.versions import BumpSeverity` as a new statement
   after `:31` (the isort region `:3-31` currently imports from `collect`, `engine`, `github`,
   `lockfile`, `sites`, `transform` and `uses` — **no `versions` import exists**), plus one `__all__`
   entry, which sorts to the head of the alphabetical list at `:34` ahead of `"GitHubClient"`.
   TypeScript **adds nothing**: `pin/index.ts:22` and `index.ts:182` already export
   `type BumpSeverity`, so both barrels are pure deletions of `ParsedTag` / `parseTag` /
   `classifyBump` / `findLatestTag` (`pin/index.ts:23-26`, `index.ts:183-186`). If 20 has already
   landed those four are gone and this step is a no-op on them; if not, this step does it and 20's
   diff shrinks. Both barrels have several other claimants — see _Conflicts and ordering_;
   hand-merge, do not serialise.
6. **Rewrite both test files** as drivers over the shared table (see _Test impact_).
7. **Drop the dependencies:** `pyproject.toml:23` loses `packaging>=23`; regenerate `uv.lock`
   (`packaging` leaves ghagen's `requires-dist`, `uv.lock:102`, but stays _resolved_ — pytest
   depends on it, `uv.lock:389`). `packages/typescript/package.json:55,62` lose `semver` and
   `@types/semver`; regenerate `package-lock.json` with
   `npm install --package-lock-only --prefix packages/typescript` (`semver` has exactly one
   dependent there, the root package, so it disappears from `node_modules` outright and stops
   appearing in `dist/*.d.ts`). **If 20 has already regenerated `package-lock.json`, discard any
   local lockfile diff and re-run that command on top of 20's result** — a regenerated 3202-line
   lockfile does not merge.
8. **Docs:** add a short "which refs count as version tags" block to the `ghagen deps upgrade`
   section of both CLI pages (`docs/src/content/docs/python/cli.md:157-185`,
   `docs/src/content/docs/typescript/cli.md:170-198`). The grammar is currently documented
   **nowhere** — those sections describe flags and exit codes only — so this is a user-facing gap
   the proposal is obliged to close (`AGENTS.md`: "Update documentation when making any user-facing
   changes"). **After 19 lands**, those sections end at `python:178` / `typescript:191` (19 removes
   the trailing `### Exit codes` tables and consolidates them at end-of-file), and the block is a
   clean append to the surviving body.
9. Gates: `scripts/test.sh all`, `scripts/typecheck.sh all`, `scripts/lint.sh all`,
   `uv run ghagen check-synced`, `uv run ghagen deps check-synced`,
   `PYTHONPATH=scripts uv run python -m ghagen_schema check`. Note `scripts/lint.sh:6` defaults to
   the `all` scope, which runs the `docs/` npm toolchain (`lint.sh:20-26`) — `npm ci --prefix docs`
   must have been run, or use `scripts/lint.sh py`. No emitted-YAML bytes change — `versions` is not
   on the Emitter path — so `fixtures/expected/*.yml` is untouched, and adding a `.yml` to `schema/`
   does not affect `ghagen_schema check`, which diffs only
   `packages/typescript/src/schema/` (`scripts/ghagen_schema/check.py:17,26-30`).

Steps 2-6 land as one commit per port pair; the invariant "both ports satisfy
`schema/tag-grammar.yml`" must never be half-true on `main`.

## Test impact

**Rewritten — `packages/python/tests/test_pin/test_versions.py` (132 lines, 27 tests) and
`packages/typescript/src/pin/versions.test.ts` (85 lines, 17 tests).** Both become thin drivers:

```python
_TABLE = YAML(typ="safe").load(SCHEMA_DIR / "tag-grammar.yml")

@pytest.mark.parametrize("tag,expected", sorted(_TABLE["parse"].items()))
def test_parse_grammar(tag: str, expected: dict | None) -> None:
    parsed = parse_tag(tag)
    if expected is None:
        assert parsed is None
    else:
        assert parsed is not None
        assert parsed.prefix == expected["prefix"]
        assert list(parsed.release) == expected["release"]

@pytest.mark.parametrize("case", _TABLE["compare"])
def test_compare_grammar(case: dict) -> None:
    bump = latest_bump(case["current"], case["available"])
    if case["latest"] is None:
        assert bump is None
    else:
        assert bump is not None
        assert bump.latest.tag == case["latest"]
        assert bump.severity == case["severity"]
```

plus a **consumed-every-key guard** per section in each port
(`set(_TABLE["parse"]) == set(collected ids)`, same for `compare`), mirroring the conformance
sweeps' scope-key parity assertion. `it.each` / `describe.each` is the vitest equivalent, and
`SCHEMA_DIR` comes from `src/paths.ts` there. Net effect: the covered input set goes from two
disjoint hand-picked lists to one shared list of **33 parse cases and 17 compare cases**, including
**all nine** shapes on which the ports currently disagree — none of which either suite tests today.
Both files lose their third-party import (`test_versions.py:5`, `versions.test.ts:2`).

**Added — one engine case per port** (`test_pin/test_engine.py`, `pin/engine.test.ts`): drive
`upgrade(..., mode="versions", apply=False)` with a `FakeTransport` tag list containing
`["v4", "v4.1.2.3"]` for a ref at `v4`, and assert `bump.latest == "v4.1.2.3"` and
`severity == "minor"` in **both** ports. This is the end-to-end regression guard for the
source-file-mutation divergence; on `main` it passes in Python and fails in TypeScript. It uses the
existing `_tags(...)` / `tags(...)` helpers and asserts only on `VersionBump` fields, so 17 (which
reshapes `UpgradeReport` afterwards) needs only to rename fields, not rewrite the case.

**Deleted — and what happens to each assertion.** The `TestClassifyBump` class
(`test_versions.py:71-91`, six tests) and the `classifyBump` describe block
(`versions.test.ts:51-61`, three tests) go, because they construct `Version` / `SemVer` instances
directly and `classify_bump` stops being callable from outside the module. Five of the six Python
assertions have exact replacements in the `compare` table; the sixth does not, and is deleted
outright:

| Deleted test                                      | Replacement                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_major` (`:72-73`)                           | `compare` row `v1.2.3` + `["v2.0.0","v1.5.0"]` → major                                                                                                                                                                                                                                                                                         |
| `test_minor` (`:75-76`)                           | `compare` row `v1.0.0` + `["v1.0.1","v1.1.1"]` → minor                                                                                                                                                                                                                                                                                         |
| `test_patch` (`:78-79`)                           | `compare` row `v1.0.0` + `["v1.0.1"]` → patch                                                                                                                                                                                                                                                                                                  |
| `test_major_with_minor_change` (`:81-83`)         | same major row (minor also differs there)                                                                                                                                                                                                                                                                                                      |
| `test_minor_with_patch_change` (`:85-87`)         | same minor row (patch also differs there)                                                                                                                                                                                                                                                                                                      |
| `test_same_version` (`:89-91`, equal → `"patch"`) | **no replacement — deleted, not moved.** `latest_bump` filters `release <= current.release` before classifying, so equal versions yield **no `Bump`**. The post-change contract is pinned instead by two `compare` rows that assert `latest: null` for equal-after-normalisation inputs (`v1.2.3` + `["v1.2.03"]`, `v1.2.3` + `["v1.2.3.0"]`). |

Four `TestFindLatestTag` cases and one TypeScript `findLatestTag` case whose behaviour is not
severity-related also have explicit table replacements, so nothing is dropped silently:

| Deleted test                                                                         | Replacement                                                                               |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| `test_sha_like` (`:55-56`)                                                           | `parse` row `"aaaa…"` (40 chars) → `null`                                                 |
| `test_empty_available_tags` (`:126-128`)                                             | `compare` row `v1.0.0` + `[]` → `latest: null`                                            |
| `test_no_newer_tags` (`:130-132`)                                                    | `compare` row `v3.0.0` + `["v1.0.0","v2.0.0"]` → `latest: null`                           |
| `test_handles_mixed_semver_and_nonsemver` (`:103-106`)                               | `compare` row `v1.0.0` + `["v1.0.0","v2.0.0","main","release/v1","nightly"]` → `v2.0.0`   |
| TS `"considers prefixed tags that share the same prefix"` (`versions.test.ts:76-80`) | `compare` row `release-v1.0.0` + `["release-v1.1.0","release-v2.0.0"]` → `release-v2.0.0` |

**Unchanged by me, owned by 17:** `fixtures/expected/upgrade_report.json` and the pr-body/issue-body
goldens. This proposal does not alter `VersionBump`'s fields or the renderer, so the golden-file
contract (`packages/python/tests/test_cli/test_deps.py:763,905,910`;
`packages/typescript/src/cli/deps.ts:236,264`) is untouched at land time. 17 then rewrites
`test_deps.py` 911 → ~250 and reshapes the report; that boundary is 17's.

Expected baseline movement, arithmetic shown:

- **pytest 562 → ~588.** `test_versions.py` loses its 27 tests and gains 50 parametrised cases plus
  2 parity guards; `test_engine.py` gains 1. `562 − 27 + 52 = 587`, `+1 = 588`.
- **vitest 515 → ~551.** `versions.test.ts` loses its 17 tests and gains the same 52;
  `engine.test.ts` gains 1. `515 − 17 + 52 = 550`, `+1 = 551`.

Both figures are the parametrised expansion, one runner case per table row.

## Risks & alternatives

**Scope boundaries vs siblings.** See _Conflicts and ordering_ for the full edge list. In summary:

- **20 (delete caller-less pin/spec surface)** shares two files with me and orders with neither. The
  dead per-repo tag cache in both engines (`engine.py:226-238`; `engine.ts:234-251`) is 20's
  deletion, not mine, and sits 3-14 lines above the block I rewrite — disjoint, verified. The four
  caller-less TS exports (`index.ts:183-186`, `pin/index.ts:23-26`) become caller-less by 20's own
  criterion after this proposal; both barrels are in my table, so whichever lands first the other's
  diff on those lines is empty. The one interaction that needs a human is `package-lock.json`.
- **17 (upgrade-report renderer)** is scheduled _after_. I change only how `severity` and `latest`
  are _computed_, not their names, types, or rendering. My one added engine test asserts on the
  pre-17 field names and will move with 17's rename; my rewrite of `test_versions.py` invalidates
  17's two citations into that file, and 17 must rebase that prose (the _coverage_ survives, via the
  table's `"main"` → `null` parse row and the `main` + `["v1","v2"]` compare row).
- **13 (shared byte oracle for headers)** and **11 (shared spec-surface conformance table)** also
  add shared data files. 11 puts its table in `schema/`, as I do; 13 puts golden _bytes_ in
  `fixtures/expected/`. `schema/tag-grammar.yml` is a new path colliding with neither.

**`FIXTURES_DIR` means two different directories in the two ports — real, and no longer this
proposal's problem.** `scripts/ghagen_schema/paths.py:35` sets `FIXTURES_DIR = REPO_ROOT / "fixtures"`;
`packages/typescript/src/paths.ts:41` sets `FIXTURES_DIR = resolve(REPO_ROOT, "fixtures", "expected")`
— under the identical doc comment "Shared golden fixtures consumed by both ports' test suites."
(Python's callers compensate by re-deriving `_FIXTURES_ROOT / "expected"`.) An earlier draft of this
proposal put the shared table in `fixtures/` and routed around the asymmetry by hardcoding a path in
the TypeScript test. Moving it to `schema/` removes the problem entirely: `SCHEMA_DIR` agrees across
ports, so both suites resolve the file the same way and neither `paths` module is touched. The
asymmetry itself remains, unfixed, in files I do not modify.

**Open — Phase 3 decision:** whether the `FIXTURES_DIR` Python/TypeScript asymmetry is fixed this
round (as part of **23**, dev-script hygiene, or as a standalone change) or deferred to
`docs/issues/08`. Nothing in this proposal depends on the answer either way.

**The value cap is new behaviour in Python.** It rejects two synthetic inputs that `packaging`
accepts today (16- and 20-digit components). **Zero of the 13,165 real tags in the sweep come near
it**, and Python's `latest_bump` result is unchanged on all 2,153 real scenarios measured. The
alternative is `bigint` in TypeScript, which gives exact unbounded parity with Python's integers and
needs no cap. Rejected as the default: `bigint` in a `readonly` release array is awkward to compare
against literals in tests, does not JSON-serialise, and buys exactness in a range no git tag will
ever occupy. If a reviewer prefers unbounded exactness, `bigint` is a drop-in for step 2/3 and the
only table changes are deleting the two over-cap rows and rewording the cap sentence.

**Risk: the cap is stated ambiguously and the two ports implement it differently.** This is the
failure mode the wording above exists to prevent, and it is not hypothetical — a "15 significant
digits" phrasing plus a _length_-based justification admits two readings, and
`v0000000000000001.0.0` (16 characters, value 1) falls on opposite sides of them. The rule is on the
**integer value**, the table pins that row explicitly, and both ports must fail the row if they
implement the character reading.

**Alternative: keep the libraries and make the two ports agree by pinning them.** Rejected. There
is no version of `packaging` that implements SemVer 2.0.0 and no version of `semver` that
implements PEP 440; agreeing would mean adding a _third_ layer of pre-validation before the library
call — more code than the tuple comparison it would guard, and the library's grammar would still be
the thing deciding, one Renovate PR away from moving.

**Alternative: adopt SemVer strictly in both ports** (reject 4-segment and zero-padded tags
everywhere). Rejected on evidence: it is a behaviour regression for Python users on shapes **29 real
action repos publish today**, including an official-vendor action (`graalvm/setup-graalvm`) and
`super-linter`, `tox` and `Homebrew/actions`. It would silently stop upgrading 382 real tags, and it
would make `parse_tag`'s own pad-to-three loop the only thing standing between a legal tag and a
silent skip. Accepting what the regex accepts is the lower-surprise rule, and it is already what one
of the two ports does.

**Alternative: adopt PEP 440 strictly in both ports** (a JS PEP 440 implementation). Rejected —
it trades one third-party grammar for another, adds a dependency to the port that is losing one,
and imports epochs, dev/post releases, and local versions that the regex can never produce.

**Risk: someone re-adds a version library later for prereleases.** The regex rejects every
prerelease form today (`v1.2.3-rc1`, `v1.2.3+build`, `v1.0.0a0`, `v6-beta` — all confirmed rejected
by both ports), so "upgrade to a prerelease" is not a feature being removed; it does not exist. If
it is ever wanted, the shared table is where the new accepted shapes and their ordering get
declared first, in one place, for both ports — which is strictly better than today's "add it to one
port's library call and find out."

**Risk: the shared table becomes a place cases go to die.** Mitigated by the consumed-every-key
guard: a row that no port reads fails a test, and a shape one port added cannot skip the other.
This is the same mechanism `schema/conformance-scopes.yml` already relies on.

## ADR / CONTEXT.md impact

- **ADR-0006 (Pin collects parsed refs, not strings) — extended, not contradicted.** Its stated
  invariant at `docs/adr/0006-pin-collects-parsed-refs.md:6-7`, "downstream pin engine stages
  consume typed refs and carry no `parse(...) is None` guards — they are unreachable," is violated
  one level down by `find_latest_tag` returning a string and the engine re-parsing it behind an
  unreachable guard (`engine.py:245-248`, `engine.ts:258-262`). `latest_bump` returning a `Bump` of
  parsed values applies ADR-0006's own rule to tags. **Recommended one-line amendment to ADR-0006**
  recording that the rule covers tag parsing as well as ref parsing, so the shape does not grow back
  a third time.
- **New ADR: `docs/adr/0008-ghagen-owns-its-tag-grammar.md`.** Records that the accept-set and the
  total order on version tags are declared in `schema/tag-grammar.yml` and implemented in
  `pin/versions.*` in both ports, and that **no third-party version library may be reintroduced on
  the compare path**. Without this, the next person who needs prerelease ordering reaches for
  `semver` again and re-forks the grammar. It must also record the value cap and its reason (exact
  integers in both runtimes, JS numbers below 2⁵³), since that is the one rule with no external
  justification, and the fact that the TypeScript port's accept-set widened by 382 real tags when it
  landed.
- **No other ADR is contradicted.** ADR-0001 (serialization seam) and ADR-0002 (no
  construction-time config globals) are untouched — nothing here is on the Emitter or config path.
  ADR-0003's "the two ports enforce different things by nature — do not fix this into false parity"
  is about _schema conformance_ (compile-time TS vs runtime Pydantic) and is not in tension: the
  tag grammar is one behaviour with one correct answer, not a language-idiom difference.
- **`CONTEXT.md` (both ports), pin glossary — two new entries after **PinEntry**
  (`packages/python/CONTEXT.md:76`, `packages/typescript/CONTEXT.md:78`):**
  - **Version tag** — a `uses:` ref that matches ghagen's declared tag grammar (optional
    `prefix-`/`prefix/`, optional `v`, dot-separated integers, each ≤ 10¹⁵ − 1); its **canonical
    release** is the integer tuple padded to three and stripped of trailing zeros beyond the third.
    Refs that are not version tags (`main`, `release/v1`) are never upgrade candidates. The grammar
    is declared once, in `schema/tag-grammar.yml`, and pinned by both suites.
  - **Bump** — a version tag strictly newer than the current one, with the same prefix, plus its
    severity (major/minor/patch). `pin/versions` is the sole authority on both; the engine consumes
    `Bump`s and never compares versions itself. Equal versions produce no Bump.
- **`CONTEXT.md` (both ports), Relationships — one appended line**
  (`packages/python/CONTEXT.md:86-92`, `packages/typescript/CONTEXT.md:88-94`): _`upgrade` compares
  only **version tags** with the same prefix; the comparison lives in `pin/versions`, never in a
  third-party library._
- **Nothing else in either `CONTEXT.md`.** In particular this proposal appends **no** Surface-notes
  bullet — the fact it would have recorded (that `pin`'s public surface exposes `BumpSeverity` only,
  `ParsedTag` / `parse_tag` being pin-internal in both ports, which ends the current asymmetry where
  TypeScript exports four version symbols and Python exports none) is carried by the **Bump** and
  **Version tag** glossary entries instead. The Surface-notes lists in both files have other
  claimants this round.
