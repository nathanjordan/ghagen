# `to_data` and `to_yaml` disagree about `auto_dedent` by default — in both ports

**Status:** open — from round 2; **reframed after direct verification**

A `to_data` / `to_yaml` pair called with no options disagrees about the content of a Step's `run`:

| Port       | `to_yaml` default                                | `to_data` default                 |
| ---------- | ------------------------------------------------ | --------------------------------- |
| TypeScript | `?? true` (`yaml-writer.ts:425`)                 | `?? false` (`yaml-writer.ts:302`) |
| Python     | `= True` (`models/_base.py`, `Document.to_yaml`) | `= False` (`emitter/data.py:52`)  |

This was originally logged as a TypeScript-only asymmetry. It is not — **the two ports agree with
each other exactly**, so it is not a parity divergence and no byte oracle will ever catch it.

What is left is a genuine interface question: `to_data` is documented as the observation surface for
what `to_yaml` will emit, and by default it observes something `to_yaml` does not emit. Either the
defaults converge, or the docstrings state the asymmetry and say why. No proposal in round 2 owned
it.
