# Shared-walk emitter: to_data as a projection of one recursion

**Status:** open — follow-up to proposal 02 / round 1 review

`to_data`/`toData` shipped as the proposal's sanctioned two-walk alternative: a second recursion
beside the YAML walk. The round-1 review found the model suite now rides the copy, not the walk
that writes files; the full-tree cross-check test (added post-review) is the mitigation. Real fix:
one shared emission walk with a swappable backend (YAML nodes vs plain data), per proposal 02's
recommended design. Both ports.
