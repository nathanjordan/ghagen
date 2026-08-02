# ghagen owns its tag grammar

**Status:** accepted (2026-07-31); regex text amended 2026-08-02 — the original spelling was
dialect-ambiguous and Python's port had taken the wider reading in all three places. The decision is
unchanged; what changed is that the accept-set is now stated in a way only one dialect can read.

The accept-set and the total order on version tags are ghagen's own. They are declared in
`schema/tag-grammar.yml` and implemented in `pin/versions.py` / `pin/versions.ts`, which hold the
tag regex, the prefix rule, the canonical-release rule, the segment cap, the order, the same-prefix
filter and the severity classification. **No third-party version library may be reintroduced on
the compare path in either port.**

A ref is a version tag iff it matches `\A(?:([^\n\r\u2028\u2029]+)[/-])?v?([0-9]+(?:\.[0-9]+)*)\z`,
has at least two numeric segments when a prefix is present, and has every segment's **integer
value** at most `999999999999999`. Its canonical release is the segments as integers, padded to
three, with trailing zeros beyond index 2 dropped; ordering is element-wise then by length.

**The regex is written in one dialect on purpose, and it is not the obvious one.** This ADR
originally stated it as `^(?:(.+)[/-])?v?(\d+(?:\.\d+)*)$` — which does not denote a single
accept-set, because three of those metacharacters mean something wider in Python than in
JavaScript, and Python's port took every wider reading:

| Written | Python read it as                                  | JavaScript read it as         |
| ------- | -------------------------------------------------- | ----------------------------- |
| `\d`    | any Unicode decimal digit — `v١.٢.٤`, `v१.२.३`     | `[0-9]` only                  |
| `.`     | any character but `\n` — a prefix may contain `\r` | any but `\n \r \u2028 \u2029` |
| `$`     | end, **or** before a trailing `\n`                 | end                           |

Every divergence ran in the damaging direction: Python accepted a ref TypeScript rejected, which is
a bump, which is a rewrite of the user's workflow files. So the **narrower JavaScript reading is
the declared one** in all three cases, and the ADR now spells the classes out rather than relying on
a dialect the reader has to guess. The distinguishing rows are pinned in `schema/tag-grammar.yml`.

Consequently the two ports do **not** carry the same regex source text, and that is correct: the
JavaScript reading is the declared one, so `versions.ts` keeps `/^(?:(.+)[/-])?v?(\d+(?:\.\d+)*)$/`
unchanged — in its own dialect that literal already denotes the narrow accept-set — while
`versions.py` spells every class out (`[0-9]`, `[^\n\r\u2028\u2029]`, `fullmatch` in place of `$`)
to reach the same set. Same accept-set, different source text. `\A`/`\z` above say "end of string,
no trailing-newline exemption" in a way neither dialect can read two ways.

## Why

`parse_tag` / `parseTag` already matched the tag, split the numeric part and padded it — then both
ports threw that parse away, re-joined it into a string and handed the string to a third-party
library: `packaging` (PEP 440) in Python, `semver` (SemVer 2.0.0) in TypeScript. The regex
proposed; two unrelated grammars disposed, and they disposed differently. Measured over 13,165
distinct tags published by real action repos, **382 parsed differently** — every one accepted by
Python and rejected by TypeScript (arity above three, leading zeros). Across the affected repos
that is **396 divergent upgrade scenarios**: 333 where Python rewrites a `uses:` ref and TypeScript
reports "up to date", and 63 where both bump and each port writes a _different_ tag into the user's
file, neither warning.

Neither suite could observe any of it, and Renovate upgrades both libraries unattended — a `semver`
minor relaxing leading zeros, or a `packaging` release tightening arity, would silently change
which refs ghagen rewrites with no gate noticing.

Every behaviour the libraries provided that ghagen uses is one tuple comparison. Everything else
they provide — prereleases, build metadata, PEP 440 epochs/dev/post releases, ranges, coercion — is
unreachable, because the regex already rejects every input that could reach it.

## Consequences

**The value cap is ghagen's own rule, not a recovered one.** It exists so both ports can hold a
release in a plain integer array: JS numbers are exact below 2^53 and `999999999999999` is well
under it, so neither port needs a bigint or a string-compare path. It is stated on the integer
**value**, not the literal's length — `v0000000000000001.0.0` is 16 characters but the value 1 and
is accepted, while `v9999999999999999.0.0` is rejected. A character-count reading is a different
implementation and the shared table pins the distinguishing row. Zero of the 13,165 real tags
measured come near the cap.

**The TypeScript port's accept-set widened by 382 real tags when this landed.** TypeScript adopted
Python's answer in every divergent case: the regex is the authority and Python was already
honouring it. Adopting SemVer strictly in both ports instead would have stopped upgrading tags that
29 real action repos publish today, including `graalvm/setup-graalvm`, `super-linter/super-linter`,
`Homebrew/actions` and `tox-dev/tox`.

**Equal versions produce no bump.** `latest_bump` / `latestBump` filters candidates that are not
strictly newer before classifying, so there is no "patch bump to the same version" result.

**New accepted shapes get declared in the table first.** If prerelease ordering is ever wanted, the
new shapes and their order go into `schema/tag-grammar.yml`, in one place, for both ports — not
into one port's library call.
