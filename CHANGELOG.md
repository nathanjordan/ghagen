# Changelog

## [0.6.0](https://github.com/nathanjordan/ghagen/compare/v0.5.0...v0.6.0) (2026-09-01)


### ⚠ BREAKING CHANGES

* **deps:** drop packaging and semver
* **pin:** `classify_bump`/`classifyBump` and `find_latest_tag`/ `findLatestTag` are gone, replaced by `latest_bump`/`latestBump`. The `Severity` alias in `pin/engine` is now `BumpSeverity`, exported from `pin/versions`.
* **pin:** `ParsedTag`, `parseTag`, `classifyBump` and `findLatestTag` are no longer exported from `@ghagen/ghagen` or its `pin` barrel.
* **actions:** drop the dead `group` input from check-deps
* **pin:** drop appLoader injection from trackUserFiles
* **pin:** drop app_loader injection from track_user_files
* **app:** App.synth returns string[] and App.check returns Array<[string, string]> (no longer Promises), and transform ordering flips from pin-first to pin-LAST. User transforms now run before the auto-registered pin transform, so they see authored uses: refs and refs they inject get pinned; an injected ref absent from the lockfile raises PinError at synth. render/applyTransforms/Rendered are exported from both port barrels.
* **app:** transform ordering flips from pin-first to pin-LAST. User transforms now run before the auto-registered pin transform, so they see authored uses: refs (not 40-char SHAs), and refs a user transform injects get pinned. A user-injected ref absent from the lockfile now raises PinError at synth.
* **config:** Python config module owns .ghagen.yml end to end
* **config:** TS config module owns .ghagen.yml end to end
* **models:** ModelSpec is the sole emitted-key authority
* **deps:** deps upgrade --json is replaced by --format json.
* to_commented_map() (Python) and Model.toYamlMap() (TypeScript) are removed; serialize through Document.to_yaml()/toYaml() or the emitter surface.
* the 24 per-model classes are no longer exported as values from the TS package; use the factories and kind discriminants. Spec self-consistency tests added in both ports.
* SynthContext removed from public exports; Transform implementations take only the document.
* replace header template with closure variant
* Model field names drop underscore prefixes (_kind -> kind, _data -> data, _meta -> meta, _keyOrder -> keyOrder, _sourceLocation -> sourceLocation). createModel() and modelToYamlMap() are removed. Model classes are now exported as values for instanceof.
* GhagenOptions.autoDedent renamed to auto_dedent to match the YAML key name.
* remove ghagen lint feature
* Configuration files must be migrated from .github/ghagen.toml to .ghagen.yml at the repo root. Lockfiles must be migrated from .github/ghagen.lock.toml to .ghagen.lock.yml. Entrypoint paths are now relative to the repo root instead of .github/.

### feat\

* migrate configuration from TOML to .ghagen.yml ([cd2629c](https://github.com/nathanjordan/ghagen/commit/cd2629c2e34d21349ad6d570bc41bd088d3d13e3))
* remove ghagen lint feature ([0e05e34](https://github.com/nathanjordan/ghagen/commit/0e05e34757753a45a54c14a71cc90fa520057bee))
* replace header template with closure variant ([2fccb42](https://github.com/nathanjordan/ghagen/commit/2fccb428d20cb7dfddae7600d3011194f0c094b7))


### refactor\

* replace Symbol-branded model objects with class hierarchy ([2550b87](https://github.com/nathanjordan/ghagen/commit/2550b879b95b308787e7f2e68c98c36213de438c))


### Features

* add ModelKind union type for model kind discriminants ([35a56b4](https://github.com/nathanjordan/ghagen/commit/35a56b43a4ceda924dc81f9c7eca5d34ed2d074a))
* **app:** extract filesystem-free synth pipeline, pin runs last (python) ([92ec67b](https://github.com/nathanjordan/ghagen/commit/92ec67b6461c0cef0dcb439ddb5b1218bee7d71a))
* **app:** sync synth pipeline, pin runs last (typescript) ([a8afe67](https://github.com/nathanjordan/ghagen/commit/a8afe67cddf4836e5b5fca03502d200907320e87))
* **ci:** scoped scripts as the single command seam; gate vitest in CI ([609088d](https://github.com/nathanjordan/ghagen/commit/609088d087d63dd98e3e691263a5ed452ab895f5))
* **cli:** add `ghagen deps update` (Python) ([40c196f](https://github.com/nathanjordan/ghagen/commit/40c196f108e2564752ce15b49c80c00d6c0522d4))
* **cli:** add `ghagen deps update` (TypeScript) ([dd924b4](https://github.com/nathanjordan/ghagen/commit/dd924b419b063cbc74f195dcb2ec12f162b94929))
* **cli:** add Python main() and take the exit code back from click ([09deafa](https://github.com/nathanjordan/ghagen/commit/09deafa6f316a180b27a5e59eb66a66e3ae90ff2))
* **cli:** main() owns the exit code in the TypeScript port ([1831948](https://github.com/nathanjordan/ghagen/commit/18319486780e9eb0e16f3ea240d5ab3179204cd4))
* **config:** Python config module owns .ghagen.yml end to end ([8d4e1db](https://github.com/nathanjordan/ghagen/commit/8d4e1db6cbad325b1c609f65bfb65fe2cb972b0c))
* **config:** TS config module owns .ghagen.yml end to end ([b3e72a6](https://github.com/nathanjordan/ghagen/commit/b3e72a647c6457ce32691497f0326567d8f585aa))
* **deps:** --format {json,pr-body,issue-body}; check-deps heredocs die ([658a6e1](https://github.com/nathanjordan/ghagen/commit/658a6e1858ba2b8debe660dd0e879f638f28dceb))
* **docs:** add build step to dev script and update AGENTS.md ([a6f33ee](https://github.com/nathanjordan/ghagen/commit/a6f33ee30891e967f11846d7a67fb5ed2e4830ed))
* **docs:** generate LLM-friendly documentation with starlight-llms-txt ([f4c5376](https://github.com/nathanjordan/ghagen/commit/f4c5376d1638109ac5d8253c3eb7af7b05a28919))
* **docs:** group TypeScript API docs into 9 module sidebar sections ([e4143fe](https://github.com/nathanjordan/ghagen/commit/e4143febc2aefe74eb9fd2bac18a7a9d51d2cdcf))
* **emitter:** public to_data/toData observation surface (both ports) ([133934a](https://github.com/nathanjordan/ghagen/commit/133934a1875b79d3a8505a7acb372b0be68b2c91))
* **models:** add generic walk()/children() traversal (Python) ([261a9bd](https://github.com/nathanjordan/ghagen/commit/261a9bdfce8918d3f19554a57a1b7ec6375e89e9))
* **models:** close the Raw escape hatch's divergence across the ports ([17280a9](https://github.com/nathanjordan/ghagen/commit/17280a95b7bf5e41d526b0771e496bcaba65ab25))
* **models:** close the schema surface gap in both ports ([3ac78c6](https://github.com/nathanjordan/ghagen/commit/3ac78c667668013d3a178af9b1118a8de36c466c))
* **models:** declarative OrderMode/dynamicKeys/present-null close TS escape hatches ([b180f50](https://github.com/nathanjordan/ghagen/commit/b180f507432cb9d2c184be8fc38f1e444df72b54))
* **models:** ImageSnapshot — model jobs.&lt;job_id&gt;.snapshot in both ports ([705bc15](https://github.com/nathanjordan/ghagen/commit/705bc15feccebf17bfcc4e8f2f8a9c49b0542c9c))
* **models:** mirror OrderMode + present-null in Python; delete On Raw(None) smuggle ([c3fc25a](https://github.com/nathanjordan/ghagen/commit/c3fc25a532c8d89637ea80c923b00be7c5a703e5))
* **models:** reject unknown input keys and enforce declared value grammars ([3ac764a](https://github.com/nathanjordan/ghagen/commit/3ac764a7a1ee288e6bf233ab2b12463250e7d6fa))
* **pin:** add pin/plan — UpdatePlan and plan_update, both ports ([39e7752](https://github.com/nathanjordan/ghagen/commit/39e775244fa8268378f9193b7e9fd4c7f047c283))
* **pin:** add pin/render, one function over four formats ([c072d44](https://github.com/nathanjordan/ghagen/commit/c072d44a2ff7032087457e5fb5664583ca2c5e9f))
* **pin:** collect parsed UsesRefs, engine drops re-parse (python) ([1af0ecd](https://github.com/nathanjordan/ghagen/commit/1af0ecdf1035cf869ff62119edcfb6d7d600659d))
* **pin:** collect parsed UsesRefs, engine drops re-parse (typescript) ([a5fa9f1](https://github.com/nathanjordan/ghagen/commit/a5fa9f1ca3b71b93d0abc07b0c394b78b84964c2))
* **pin:** ghagen owns its version-tag comparison ([411ee92](https://github.com/nathanjordan/ghagen/commit/411ee92888ed646eb53b68a93bed5157d64522a1))
* **pin:** lift transport policy into the Python HttpClient contract ([3d6dc4f](https://github.com/nathanjordan/ghagen/commit/3d6dc4f723e0252c778671d143c9a4daf48e768b))
* **pin:** lift transport policy into the TypeScript HttpClient contract ([8ee145a](https://github.com/nathanjordan/ghagen/commit/8ee145a9e46fbf94993f3c6481351388f593d28d))
* **pin:** single-home the lockfile's on-disk encoding and error mode ([ade4b7d](https://github.com/nathanjordan/ghagen/commit/ade4b7de632da6aad0d918ec2a728ff83f0dd3b0))
* **pin:** track native-ESM helpers via module.register augmentation ([82ee55d](https://github.com/nathanjordan/ghagen/commit/82ee55d5cd6e1d8f79b3db5147eabb124000f58d))
* **pin:** UpgradeReport reports what the run was asked to check ([07a8ed9](https://github.com/nathanjordan/ghagen/commit/07a8ed9af0a84f78a0bacd7ff55ca8600c1c18f5))
* **release:** switch npm publish to OIDC trusted publishing ([9871653](https://github.com/nathanjordan/ghagen/commit/9871653409995a56ed637a04c7c52174fae35e6c))
* **schema:** add dev-only ghagen_schema pipeline orchestrator ([7a5bfbd](https://github.com/nathanjordan/ghagen/commit/7a5bfbd52ee003c9174775b86b7993aa40e29ac6))
* **scripts:** add docs dev server script ([ff5fc09](https://github.com/nathanjordan/ghagen/commit/ff5fc09e0aec0ae9da7229e44498813702f8c5f9))


### Bug Fixes

* **action:** rewrite check-deps around ghagen deps update ([b40f7f5](https://github.com/nathanjordan/ghagen/commit/b40f7f5b1a5e30a96e16304f879d097353a2044f))
* **actions:** drop the dead `group` input from check-deps ([558fca4](https://github.com/nathanjordan/ghagen/commit/558fca481e450b2be09328d54dd777ad3512986f))
* **check-deps:** recover from a pushed branch with no PR, guard LABEL_ARGS ([9e083ab](https://github.com/nathanjordan/ghagen/commit/9e083abde7b3b3bb43321ad44bc8281fa457add7))
* **ci:** drift job no longer self-defeats on real drift ([21cd6d1](https://github.com/nathanjordan/ghagen/commit/21cd6d128f9960a84caabb3957cf8a45ac745d55))
* **ci:** env-independent generated headers; oxfmt-stable generated types ([fb688cc](https://github.com/nathanjordan/ghagen/commit/fb688cc836b7a3d7008ea5ffa3a11a62a64a49e5))
* **cli:** `ghagen help` is a usage error in both ports, not 0 in one and 2 in the other ([2e6b334](https://github.com/nathanjordan/ghagen/commit/2e6b334aa4892fc2ab4dd3b1e6aa9a8c385de157))
* **cli:** converge the two init templates on a byte oracle ([406665c](https://github.com/nathanjordan/ghagen/commit/406665c192c2fcba1b8e0b97ad6f41905597ad65))
* **cli:** import click exceptions from the pinned top-level distribution ([adb2e8a](https://github.com/nathanjordan/ghagen/commit/adb2e8a4303062f7014933df064f20f82b78b56b))
* **cli:** Python main() returns 1 instead of propagating unexpected exceptions ([fee62fd](https://github.com/nathanjordan/ghagen/commit/fee62fdc5af8a55e1f34d7cf73c512672f6e3801))
* **cli:** route the apply progress note to stderr under --format ([0cae9b1](https://github.com/nathanjordan/ghagen/commit/0cae9b103f0a0149b13ced2e4abcfce14df47e38))
* **config:** --config short-circuits before .ghagen.yml read ([d71a627](https://github.com/nathanjordan/ghagen/commit/d71a627d4ab03d5a0d908161bca95ae835c93d0d))
* **deps:** declare click and cap typer below its click vendoring ([1e9e95f](https://github.com/nathanjordan/ghagen/commit/1e9e95fb2480a01d534aa49de450d4babd7cb58a))
* **deps:** declare packaging as a runtime dependency ([1010fed](https://github.com/nathanjordan/ghagen/commit/1010fede16179f9327ebaf16883f46a023014a7d))
* **deps:** synthesize after update, and refresh the lockfile a bump invalidated ([e6c342f](https://github.com/nathanjordan/ghagen/commit/e6c342f52821e79fa378397afcd56bebaf9a55e5))
* **deps:** the config module does not own stdout ([41bdb9b](https://github.com/nathanjordan/ghagen/commit/41bdb9b7e28fee1e9488ae503807ee5c496b620b))
* **deps:** treat upgrade report JSON as typed contract; dogfood check-deps ([ba404c9](https://github.com/nathanjordan/ghagen/commit/ba404c92050c6400baba42b4d81835ac9e9b26e0))
* **emitter:** a model's own comment precedes a field comment on the same key ([3786a94](https://github.com/nathanjordan/ghagen/commit/3786a94e8986d80775d8735eeafb3e25a41f23fd))
* **emitter:** present-null fires and keeps its comment when the model is commented ([fbc5544](https://github.com/nathanjordan/ghagen/commit/fbc55442409d2a9fa5d17aca9d1e0c56cb7f26c2))
* **emitter:** render comment geometry at attach time, never over emitted text ([f1c6797](https://github.com/nathanjordan/ghagen/commit/f1c67978b40ff4bef0607041ab3c8d0aa1e45952))
* **emitter:** toData present-null comment + Step-run dedent parity ([7abe0f6](https://github.com/nathanjordan/ghagen/commit/7abe0f6ad126341f31dbcc65b4fe4cf8f71db812))
* **emitter:** TypeScript keeps a discarded present-null sub-model's comment ([4ae0f8a](https://github.com/nathanjordan/ghagen/commit/4ae0f8ac6ea0c4ba9ea9b7c4d6b4fc4444524ce2))
* **models:** Raw[T] no longer auto-wraps, restoring union constraints ([3741a1d](https://github.com/nathanjordan/ghagen/commit/3741a1def090c1e940e3834a548d3826955c8b99))
* **models:** reject unknown keyword arguments (python) ([944bd90](https://github.com/nathanjordan/ghagen/commit/944bd904362d3e50945d44f9e6799ef885635fe7))
* **models:** traverse extras in walk(), and traverse them last ([d9dc4fb](https://github.com/nathanjordan/ghagen/commit/d9dc4fbb3efc4fcb7cd1e94c7a2902ad5a1ebe0b))
* **pin:** a shape-malformed 200 raises ResolveError in both ports ([fa9d015](https://github.com/nathanjordan/ghagen/commit/fa9d0152030d7c6ed0cafc4fccecdbdc424bb586))
* **pin:** bound GitHub API requests with a 30s timeout (python) ([b150bc7](https://github.com/nathanjordan/ghagen/commit/b150bc7856f0efca3edfea9203d9b5cc4ef05f80))
* **pin:** export the transport deadline; ADR-0008 states one dialect ([f7ee668](https://github.com/nathanjordan/ghagen/commit/f7ee668dd1431e5057d92334e6278f0f18d3b738))
* **pin:** give the config loaders' sys.path insertion a lifetime (item D) ([43a931e](https://github.com/nathanjordan/ghagen/commit/43a931e6b9fd8e4f948d891a2c64539cac0a8c0b))
* **pin:** map malformed JSON bodies onto ResolveError (python) ([7c3964f](https://github.com/nathanjordan/ghagen/commit/7c3964fb0c3a57fa90d71e73e03a9d2b8b92d2d2))
* **pin:** Python's HTTP deadline is wall-clock, not per socket operation ([36df592](https://github.com/nathanjordan/ghagen/commit/36df5928cef341ab89f40867e72b922b46a79dff))
* **pin:** Python's PinError names a command that exists ([24338f9](https://github.com/nathanjordan/ghagen/commit/24338f9b16fa2814ce917412c304d171bb2edd4e))
* **pin:** Python's tag grammar is the same accept-set as TypeScript's ([3d3e056](https://github.com/nathanjordan/ghagen/commit/3d3e0564fe2a3335c34c664d285331972660ac62))
* **pin:** track helpers imported lazily inside create_app() ([c634a9d](https://github.com/nathanjordan/ghagen/commit/c634a9db43910596517e8d4728d0a38dbd21bb7d))
* remove unused imports and useless string concatenation ([a02bbc2](https://github.com/nathanjordan/ghagen/commit/a02bbc2f81e8509a4541db73caabb9081b5f433f))
* **scripts:** ghagen_schema check no longer writes the files it checks ([c894255](https://github.com/nathanjordan/ghagen/commit/c894255a7be6eeca7df05e7ef730734c972513d5))
* **test:** commit the sources-canary fixture's fake installed package ([e05bae6](https://github.com/nathanjordan/ghagen/commit/e05bae6578937e5fb403e48761afb08ca309860f))
* **tests:** stop pinning click's usage-error prose ([d9e0bd8](https://github.com/nathanjordan/ghagen/commit/d9e0bd8c98307f78284352056e3e9474fd8d59cf))
* **test:** thread required auto_dedent into to_data cross-check emit call ([2fc1751](https://github.com/nathanjordan/ghagen/commit/2fc17519c57cede40e473ac8d5218963cb1f3fe2))
* **ts:** port dedent_script for Python parity; drop npm dedent ([c12ac56](https://github.com/nathanjordan/ghagen/commit/c12ac5687836be857b2392cd5f7fedb59fbbd957))


### Documentation

* ADR-0012 for the check-deps outputs reversal, plus two round-2 issues ([7a91491](https://github.com/nathanjordan/ghagen/commit/7a91491e529b2642ab0fbd177e3a8b6d96b14b86))
* **adr,context:** round-1 ADR amendments, ADR-0005..0007, glossary updates, deferred issues ([abdacee](https://github.com/nathanjordan/ghagen/commit/abdaceedada6f5f5013f2ed57c6ad67e85070167))
* **adr:** record the extrasPlacement deletion as a reversal of 06's accepted risk ([02effcc](https://github.com/nathanjordan/ghagen/commit/02effcc06486bc13ec801435ef759e76101989c2))
* **api:** add new public surface to TypeDoc entry points ([8248474](https://github.com/nathanjordan/ghagen/commit/8248474ee1d47aa901723069ca056084df774870))
* architecture deepening plan round 2; amend ADR-0001; add ADR-0004 ([034f1e3](https://github.com/nathanjordan/ghagen/commit/034f1e375cd2ca5d5dd03cd0846e999892f19cad))
* architecture deepening plan, domain glossary, and ADRs ([caaedb1](https://github.com/nathanjordan/ghagen/commit/caaedb1f24abfc5b0ef00f1a9297a9bb2abd2d78))
* **cli:** document the --format json key-set rule in both ports ([9d81e03](https://github.com/nathanjordan/ghagen/commit/9d81e03eef3be8d601c38ff4142fa844ca4054b2))
* **cli:** one exit-code table per port, replacing three partial ones ([657ba12](https://github.com/nathanjordan/ghagen/commit/657ba122f69a4bac6e5b226be77758eedd651565))
* **cli:** the update plan states decisions, not outcomes ([2190898](https://github.com/nathanjordan/ghagen/commit/2190898f55cd50988671df55bf57be2a9c4d4077))
* **context:** record the transport contract in both glossaries ([3e3501f](https://github.com/nathanjordan/ghagen/commit/3e3501f7c043946c30697fef257e6d2219d3c901))
* **context:** state the factory-is-a-spec-binding rule and the [@function](https://github.com/function) requirement ([c6f85bb](https://github.com/nathanjordan/ghagen/commit/c6f85bb61bb763adf29190b76e6962a00f2150ad))
* **context:** state the narrowed traversal contract in both ports ([5151d32](https://github.com/nathanjordan/ghagen/commit/5151d328c91ad44aeebdc6d01be84e829ce72850))
* document `deps update`, reverse spec 0005's no-outputs rule ([4c71a74](https://github.com/nathanjordan/ghagen/commit/4c71a74f380adfad424241565f2436b0c971d3a5))
* document the gate setup and the per-gate scope vocabulary ([7181d60](https://github.com/nathanjordan/ghagen/commit/7181d60cbfbff84f370d07791deab156838c9731))
* **emitter:** correct the documented comment geometry ([5b9a0d2](https://github.com/nathanjordan/ghagen/commit/5b9a0d2e3bb4329c4c18b074a0610ae5fcf708cd))
* **issues:** land round-2 deferred work as issues 09-19 ([10486b1](https://github.com/nathanjordan/ghagen/commit/10486b12d48446b5ae4080e2d30a7c5a30864f82))
* **issues:** record the click 8.4 wording drift as issue 19's second data point ([00b401a](https://github.com/nathanjordan/ghagen/commit/00b401a83b9dee35b77efd2a3ed6287efca144ce))
* **models:** re-attach six orphaned factory doc blocks ([b4ebf46](https://github.com/nathanjordan/ghagen/commit/b4ebf46d4cc63a9d274a5d7e97d3722b6136c4ff))
* **pin:** record the tag grammar as ghagen's own ([06f1cb9](https://github.com/nathanjordan/ghagen/commit/06f1cb94d082517f16b3238b8697c4dc99f4d438))
* **proposals:** architecture deepening round 1 — proposals 01-08 ([8972de6](https://github.com/nathanjordan/ghagen/commit/8972de64559faa4dd08ad25bdbd818822fb3b870))
* **proposals:** round-1 index ([2199861](https://github.com/nathanjordan/ghagen/commit/2199861ac7532c8bcd7ae97b02cdf18394c4f926))
* **proposals:** round-2 proposals 09-24 ([9f2612d](https://github.com/nathanjordan/ghagen/commit/9f2612dae6ab9eb8cfb4c48342a49919aee80a1d))
* record proposal 10's out-of-allowlist findings ([8c01e38](https://github.com/nathanjordan/ghagen/commit/8c01e388d609135caab57ea99a81e821added457))
* record the construction-time input contract in ADR-0003 and CONTEXT ([24bdfbd](https://github.com/nathanjordan/ghagen/commit/24bdfbdb23c612a413715c774b8421da4dc9bede))
* record the round-2 review fix pass, file issue 30 ([a8ba47a](https://github.com/nathanjordan/ghagen/commit/a8ba47a927f6f8ba4553c99f82da4d2cca4c9f00))
* round-2 index section, review-derived issues 23-29, CONTEXT.md glossary ([2e62c9b](https://github.com/nathanjordan/ghagen/commit/2e62c9bae6a9f91d3792ac71407038905a43141e))
* unstale proposals README; ADR-0010 declines the matrix_ rename ([3f5519c](https://github.com/nathanjordan/ghagen/commit/3f5519cd1687078f0cafe19c1adf97f98addc875))
* update CONTEXT surface notes for the amended Emitter seam ([0a75172](https://github.com/nathanjordan/ghagen/commit/0a75172ad8ddb594a7232264951556339c6515f1))


### Code Refactoring

* Emitter owns all serialization recursion (ADR-0001 amendment) ([6fec49e](https://github.com/nathanjordan/ghagen/commit/6fec49e9604d0b019c4b212a0187b6443648495b))
* **models:** ModelSpec is the sole emitted-key authority ([d20519f](https://github.com/nathanjordan/ghagen/commit/d20519fe9bbf5eac20895c84fdeac407c9fab91a))
* ModelSpec — per-model serialization spec in both ports ([919266d](https://github.com/nathanjordan/ghagen/commit/919266ddf9ad9a88ad5a2cca28d40a8caa3d62c3))
* narrow Transform to (document) -&gt; document; drop SynthContext ([49a55b3](https://github.com/nathanjordan/ghagen/commit/49a55b3bb3a977065d66d8aa841ec3732ca7d362))
* **pin:** drop app_loader injection from track_user_files ([75ca071](https://github.com/nathanjordan/ghagen/commit/75ca0713ddf76b2216b5d9970a197545fc3edb2e))
* **pin:** drop appLoader injection from trackUserFiles ([c1bb483](https://github.com/nathanjordan/ghagen/commit/c1bb4832cd9f07bbb84fb2e0a0d299768dec18a0))
* **pin:** stop re-exporting four caller-less versions symbols (item H) ([d2542ea](https://github.com/nathanjordan/ghagen/commit/d2542ea6f448b91630c3ff22db1b2b620cde8e55))
* replace manual config validation with Zod 4 schema ([d881e01](https://github.com/nathanjordan/ghagen/commit/d881e01aa1ae8a341e5bfedc6b941a995fefb4f4))


### Build System

* **deps:** drop packaging and semver ([059e689](https://github.com/nathanjordan/ghagen/commit/059e6893caa4f6427900d53e36555dc5c5ea92f3))

## [0.5.0](https://github.com/nathanjordan/ghagen/compare/v0.4.0...v0.5.0) (2026-04-21)

### Features

- add CI/local parity for lint, format, and type checks ([eb40f1b](https://github.com/nathanjordan/ghagen/commit/eb40f1b4e35491e8805c75948bd30eceb570b179))
- add top-level lint/fmt/test scripts and simplify pre-commit hooks ([f07bc1a](https://github.com/nathanjordan/ghagen/commit/f07bc1a91529451dc8d4d2dbf5d6794219da9b80))
- **docs:** render TypeScript API members as HTML tables ([b986b5a](https://github.com/nathanjordan/ghagen/commit/b986b5a8818f8e1f25caf8e6b7f1e97fbdc7ae67))
- replace field_comments/field_eol_comments with withComment/withEolComment wrappers ([6eb57bb](https://github.com/nathanjordan/ghagen/commit/6eb57bbb067fe1e816e92695a8cb470b32cdfdfe))
- **typescript:** add App, CLI, pin, lint, and config subsystems ([9553551](https://github.com/nathanjordan/ghagen/commit/95535511ecc3a0b2f5c9f2a5e65ed90f75bb54e9))

### Bug Fixes

- **ci:** resolve pyright, ruff, and oxfmt failures ([66d8a8e](https://github.com/nathanjordan/ghagen/commit/66d8a8e22232c3de760d265225051ccb59b69171))
- **deps:** prune stale lockfile entries by default and fix oxlint errors ([752cd22](https://github.com/nathanjordan/ghagen/commit/752cd224140c9fc94e1c69fabb68f86006807f25))
- **docs:** apply oxfmt formatting to docs content files ([8b133ae](https://github.com/nathanjordan/ghagen/commit/8b133ae4eb8da0c22e1effeed696842dc2367906))
- **docs:** install TypeScript package deps before docs build ([35c429b](https://github.com/nathanjordan/ghagen/commit/35c429bb3e8959eb7d2cf3dcec5076d9d04db99f))
- **docs:** skip TypeDoc error checking during build ([a8207e4](https://github.com/nathanjordan/ghagen/commit/a8207e41e9e50401797f3e5373d9d17183f19036))
- **release:** single approval gate, clean up tags and changelogs ([1bb0b4e](https://github.com/nathanjordan/ghagen/commit/1bb0b4e461c6e75e75f7b43fcda4d563a51b8ed6))

### Documentation

- add local docs server instructions to AGENTS.md ([7487e50](https://github.com/nathanjordan/ghagen/commit/7487e5075ca49fed49926c8b7e2bc258875f46ff))
- add Why section and expand Features list in README ([8d84fc9](https://github.com/nathanjordan/ghagen/commit/8d84fc9f5eeae6d84760a195d5b0e8af467f9ab2))
- bring TypeScript documentation to parity with Python ([bda81e4](https://github.com/nathanjordan/ghagen/commit/bda81e458ba3a4ee0a334f97334c3b69e63b43ab))
- clean up documentation for developer audience ([e32768c](https://github.com/nathanjordan/ghagen/commit/e32768c9d82f730bdc1d2ed3d7b5f68d0c3fc4cf))
- clean up TypeScript API pages with concise formatting ([09fa292](https://github.com/nathanjordan/ghagen/commit/09fa2926b934e313ba175628c29a292a64e7aa81))
- fix typos and improve README clarity ([2b92acb](https://github.com/nathanjordan/ghagen/commit/2b92acbe4addb0ce3f77b3cbb330e453149cd2b6))
- flatten TypeScript API sidebar into a single list ([e12c722](https://github.com/nathanjordan/ghagen/commit/e12c722fa5f8a3fb0ab0be97a4c7208b843d0ec3))
- improve examples, navigation, and add raw YAML passthrough ([224fa75](https://github.com/nathanjordan/ghagen/commit/224fa7508c5f480c233e2604bce3b11d70f6b16e))
- move "Why" section from README to docs home page ([893b5a8](https://github.com/nathanjordan/ghagen/commit/893b5a83106346992dae919844d4c22bfde2ca70))
- move "you probably don't need this" note below features ([39461f5](https://github.com/nathanjordan/ghagen/commit/39461f5da7e1b8c212f873310e08c2b6a8615b59))
- remove dependency update action design spec ([6e4f632](https://github.com/nathanjordan/ghagen/commit/6e4f632b5fabd9dacbfbcc610b63fa4d7959ff1e))
- remove getting-started, FAQ, and unpinned-actions references ([2b062f4](https://github.com/nathanjordan/ghagen/commit/2b062f4e804ece7d56f687563bd8ad04c652e637))
- restructure README with per-tool quickstarts and inline FAQ ([1dba769](https://github.com/nathanjordan/ghagen/commit/1dba769875aea916141774018a0ba56c0640936f))
- switch Starlight theme to rapide ([0e8a58b](https://github.com/nathanjordan/ghagen/commit/0e8a58b092bd8261ed98e08c9126d7473495ca72))
- trim completed items from ROADMAP and reformat ([a42bf61](https://github.com/nathanjordan/ghagen/commit/a42bf61b9c80d73a4115b6135492041947c3b304))
- update README to reflect TypeScript App/synth parity ([5f89560](https://github.com/nathanjordan/ghagen/commit/5f895606d7eb1e237944bda4755517ae7481f567))

## [0.4.0](https://github.com/nathanjordan/ghagen/compare/v0.3.2...v0.4.0) (2026-04-15)

### ⚠ BREAKING CHANGES

- checkout(), setup_python(), setup_uv(), setup_node(), cache(), upload_artifact(), download_artifact() helpers removed. Use Step(uses=...) directly.

### Features

- add oxlint and oxfmt for TypeScript and docs packages ([688c77e](https://github.com/nathanjordan/ghagen/commit/688c77eb0e01e831b66b5f788fd262e285ba444d))
- remove predefined step helpers in favor of direct Step() usage ([869ff2f](https://github.com/nathanjordan/ghagen/commit/869ff2f6235e027cbf6776df114ae4159ee807a4))

### Bug Fixes

- **release:** switch to v0.X.Y tags and add rolling major version tag ([696c723](https://github.com/nathanjordan/ghagen/commit/696c7236f6ab2bb9fb01bb42d697a94c55f35ddb))

## [0.3.2](https://github.com/nathanjordan/ghagen/compare/v0.3.1...v0.3.2) (2026-04-15)

### Bug Fixes

- **release:** rename npm package to @ghagen/ghagen for scoped publishing ([a60cc87](https://github.com/nathanjordan/ghagen/commit/a60cc87fcf36230c2f5a12a72a284b67ffa5912f))

### Documentation

- migrate from MkDocs to Astro Starlight with TypeScript support ([580dda1](https://github.com/nathanjordan/ghagen/commit/580dda175c5e7d4791d6ef1cc8e5ffd6e54b686e))

## [0.3.1](https://github.com/nathanjordan/ghagen/compare/v0.3.0...v0.3.1) (2026-04-14)

### Bug Fixes

- **release:** correct release-please output key for TypeScript package ([2967da0](https://github.com/nathanjordan/ghagen/commit/2967da0489daed0f95e266321df074ce02cff9f4))
- **release:** reset TypeScript manifest to 0.1.0 for re-release ([ab1f20a](https://github.com/nathanjordan/ghagen/commit/ab1f20aff62cc54fb1ec026a1b8986923c6ffce4))

## [0.3.0](https://github.com/nathanjordan/ghagen/compare/v0.2.1...v0.3.0) (2026-04-14)

### ⚠ BREAKING CHANGES

- **emitter:** configurable header with source-file templating
- add action.yml generation and redesign App API ([#4](https://github.com/nathanjordan/ghagen/issues/4))

### Features

- add action.yml generation and redesign App API ([#4](https://github.com/nathanjordan/ghagen/issues/4)) ([10914bb](https://github.com/nathanjordan/ghagen/commit/10914bb8768d2a4fc390a3c86dca6f80c80c5805))
- add `ghagen pin` command with SHA lockfile ([#7](https://github.com/nathanjordan/ghagen/issues/7)) ([a138ee0](https://github.com/nathanjordan/ghagen/commit/a138ee06b858e376ed4948bf893dc5b2937510b9))
- add CI job to test composite action via uses: ./ ([f02a3ed](https://github.com/nathanjordan/ghagen/commit/f02a3ed27b9d930fab150fac3ba19daef6df82bb))
- add ghagen lint command with rule engine ([#5](https://github.com/nathanjordan/ghagen/issues/5)) ([3e7d3da](https://github.com/nathanjordan/ghagen/commit/3e7d3da76db019d83da87a7c56be976fa625b557))
- add ghagen update action for automated dependency updates ([78d19b4](https://github.com/nathanjordan/ghagen/commit/78d19b476fa945c2d26042865cb2852f8177cc35))
- add Homebrew tap automation and install docs ([60dd99c](https://github.com/nathanjordan/ghagen/commit/60dd99cc828d594db0784f37ac435e8694530c40))
- **cli:** add `entrypoint` key to .github/ghagen.toml ([16f5156](https://github.com/nathanjordan/ghagen/commit/16f5156ff68ff0e3aa9788b2af504b1104e0be2f))
- **cli:** add `ghagen outdated` command for update detection ([f1a1dff](https://github.com/nathanjordan/ghagen/commit/f1a1dff8166a3d85029e501e178fcf97e74452ba))
- **emitter:** configurable header with source-file templating ([64bb6d9](https://github.com/nathanjordan/ghagen/commit/64bb6d9141c05f52c0510f3260c1966bdd81f06b))
- **emitter:** fix seq-item comments and auto-wrap multiline strings ([#9](https://github.com/nathanjordan/ghagen/issues/9)) ([5fd0bda](https://github.com/nathanjordan/ghagen/commit/5fd0bdaf380cdcd16800fddec5688f0aecbef378))
- **lint:** add duplicate-step-ids rule and drop mutable-defaults ([#6](https://github.com/nathanjordan/ghagen/issues/6)) ([1d5874d](https://github.com/nathanjordan/ghagen/commit/1d5874d952b377536c23e5ff49e5db75ce5497cd))
- **pin:** add list_tags() for paginated tag listing via GitHub API ([483589b](https://github.com/nathanjordan/ghagen/commit/483589bc7b32fb0fa1188659b3bd9bd64f034fa4))
- **pin:** add source tracking module for uses ref location ([189e3db](https://github.com/nathanjordan/ghagen/commit/189e3dbcae78dc8b2ab17e3e4c8e14b0e7268be7))
- **pin:** add source update module for applying version bumps ([1838832](https://github.com/nathanjordan/ghagen/commit/18388323463539b94cdc8c872d39417038a72943))
- **pin:** add version comparison module for action tags ([a416844](https://github.com/nathanjordan/ghagen/commit/a416844054cc878e8386b21b24179d9c27385a53))
- **pin:** pin composite action steps alongside workflows ([dbd9aa4](https://github.com/nathanjordan/ghagen/commit/dbd9aa400357a75702eec03aa73b1382701108d1))
- **release:** add npm publishing for TypeScript package ([1a50b45](https://github.com/nathanjordan/ghagen/commit/1a50b454f31de02dd106604133c27a359f6d38ac))
- restructure into monorepo with TypeScript package skeleton ([#20](https://github.com/nathanjordan/ghagen/issues/20)) ([e997f15](https://github.com/nathanjordan/ghagen/commit/e997f15acec46136d57386498e60ce644d89967e))
- **step:** auto-dedent triple-quoted strings in Step.run ([0dac976](https://github.com/nathanjordan/ghagen/commit/0dac97625f778fcbd34129c391942c1653773efd))
- **typescript:** implement model layer with factory functions and YAML serializer ([0ca3e2d](https://github.com/nathanjordan/ghagen/commit/0ca3e2d389cf4639d175053f419a5a6fe5fd9925))

### Bug Fixes

- add release environment to homebrew-bump job ([5f80ca1](https://github.com/nathanjordan/ghagen/commit/5f80ca10606ed0d8b7da61b079f5ad0500f985a3))
- address code review findings for outdated command ([b808e64](https://github.com/nathanjordan/ghagen/commit/b808e64f684b8a13ff3fab47c885014a79dda079))
- **pin:** skip token warning in --check mode ([4c09391](https://github.com/nathanjordan/ghagen/commit/4c09391cb34ab771d6bf2634eb04d584c4e98d1e))
- **release:** bump minor (not major) for breaking changes pre-1.0 ([#11](https://github.com/nathanjordan/ghagen/issues/11)) ([687fd3e](https://github.com/nathanjordan/ghagen/commit/687fd3ecea704007b665d2d1e2c58843f08cd395))

### Documentation

- add AGENTS.md with project overview and agent instructions ([1e862a8](https://github.com/nathanjordan/ghagen/commit/1e862a866952acfe1f60b0f4466410a5f75b4e8d))
- **mkdocs:** switch theme to amber accent with factory logo ([7d2ab9a](https://github.com/nathanjordan/ghagen/commit/7d2ab9a5f852e8a2fe698f83aabcd62705f003e8))
- note that ghagen supports actions defined in this repo ([f41e240](https://github.com/nathanjordan/ghagen/commit/f41e2409d1a4f1b8dd24ec90f26e821be710af18))
- require documentation updates for user-facing changes ([e7b96e1](https://github.com/nathanjordan/ghagen/commit/e7b96e145a7a27f6a6d458e13efea456510717ea))
- **roadmap:** mark action pinning as done ([#8](https://github.com/nathanjordan/ghagen/issues/8)) ([1149723](https://github.com/nathanjordan/ghagen/commit/114972386a2d0931b5c7a580d33f1b5e1394e49d))
- update AGENTS.md to reflect TypeScript/JavaScript support ([78de75b](https://github.com/nathanjordan/ghagen/commit/78de75b764330faad363c7c2b5d6bc71f3ecfd17))

## [0.2.1](https://github.com/nathanjordan/ghagen/compare/v0.2.0...v0.2.1) (2026-04-07)

### Bug Fixes

- add contents:read permission to publish job ([a7cb3fb](https://github.com/nathanjordan/ghagen/commit/a7cb3fb283239dc2b40735d2cde063648b85fd83))

## [0.2.0](https://github.com/nathanjordan/ghagen/compare/v0.1.0...v0.2.0) (2026-04-07)

### Features

- add actionlint to pre-commit and CI lint job ([59198c2](https://github.com/nathanjordan/ghagen/commit/59198c20824e3bc4a5fc693d3d5bf82dc72c2ff7))
- add composite GitHub Action for workflow freshness checking ([178728b](https://github.com/nathanjordan/ghagen/commit/178728b9981cf237cd2db75309dd32d1748d0c03))
- add DRY helpers — step factories and expression builder ([3b1fabf](https://github.com/nathanjordan/ghagen/commit/3b1fabf651308ca019cb0b977e360fada9d35545))
- add Release Please automation for PyPI publishing (Milestone 5) ([6f48ab3](https://github.com/nathanjordan/ghagen/commit/6f48ab39f465ed423bd1b508490a74dd7fbcd7a0))
- add schema pipeline for drift detection ([637fafc](https://github.com/nathanjordan/ghagen/commit/637fafc13027ee5f57cb1f4037ac1d309fa21d11))
- dogfood ghagen for own CI/CD workflows ([949acf9](https://github.com/nathanjordan/ghagen/commit/949acf9858bdff5414e7d2e6c482abf85b1fe3be))
- initial implementation of ghagen core library ([8651ab0](https://github.com/nathanjordan/ghagen/commit/8651ab03893ff80b83a8fb03890a82d23180efa0))

### Bug Fixes

- resolve ruff lint errors in new test files ([9b409a1](https://github.com/nathanjordan/ghagen/commit/9b409a1a61dde62ee81df40537bd2829a0927b3d))

### Documentation

- add detailed ROADMAP.md for remaining work ([17e249c](https://github.com/nathanjordan/ghagen/commit/17e249c07dcf469b295a2f886f629c90f87f1196))
- add MkDocs-Material documentation site and README (Milestone 4) ([1885543](https://github.com/nathanjordan/ghagen/commit/1885543804ca0b70f0fe500042a8b86ecfd37186))
- update ROADMAP.md — mark Milestone 3 complete ([203c9b5](https://github.com/nathanjordan/ghagen/commit/203c9b55a8f212c02a6378c0cd2c05f1444af0c3))

## [0.1.0](https://github.com/nathanjordan/ghagen/releases/tag/v0.1.0) (2026-04-07)

Initial release — generate GitHub Actions workflow YAML from Python code.
