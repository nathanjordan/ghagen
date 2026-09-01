import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightThemeRapide from "starlight-theme-rapide";
import starlightLlmsTxt from "starlight-llms-txt";
import { createStarlightTypeDocPlugin } from "starlight-typedoc";
import { Converter } from "typedoc";

const [appTypeDoc, appSidebar] = createStarlightTypeDocPlugin();
const [workflowTypeDoc, workflowSidebar] = createStarlightTypeDocPlugin();
const [jobTypeDoc, jobSidebar] = createStarlightTypeDocPlugin();
const [stepTypeDoc, stepSidebar] = createStarlightTypeDocPlugin();
const [triggersTypeDoc, triggersSidebar] = createStarlightTypeDocPlugin();
const [permissionsTypeDoc, permissionsSidebar] = createStarlightTypeDocPlugin();
const [actionTypeDoc, actionSidebar] = createStarlightTypeDocPlugin();
const [expressionsTypeDoc, expressionsSidebar] = createStarlightTypeDocPlugin();
const [outputTypeDoc, outputSidebar] = createStarlightTypeDocPlugin();

/**
 * TypeDoc plugin that runs TypeDoc's own validation pass and fails the build on it.
 *
 * Two things have to be true for the `validation` options below to be a gate, and
 * neither is true by default here:
 *
 *  1. Something has to *call* the validation pass. `notExported`, `notDocumented`,
 *     `invalidLink` and `unusedMergeModuleWith` only run inside `Application.validate()`,
 *     and `validate()` is called by TypeDoc's own CLI -- not by `convert()`, not by
 *     `generateOutputs()`. starlight-typedoc drives the two latter directly, so
 *     setting `validation` alone would be inert config. This hook runs `validate()`
 *     at the same point the CLI does: immediately after conversion resolves.
 *  2. Something has to *fail* on the result. `treatValidationWarningsAsErrors` is
 *     likewise only read by the CLI, where it picks an exit code. Nothing here has an
 *     exit code to pick, so the equivalent is to throw -- which fails `astro build`,
 *     and so fails `scripts/typecheck.sh docs`.
 *
 * The pass/fail rule below is copied from TypeDoc's `cli.js`: validation failed if the
 * validators raised an error, or if they raised any warning (`validationWarningCount`
 * also counts the `invalidPath` warnings raised during conversion rather than in
 * `validate()`).
 */
function typeDocValidationGate(app) {
  app.converter.on(Converter.EVENT_END, (context) => {
    const errorsBefore = app.logger.errorCount;
    const warningsBefore = app.logger.warningCount;

    app.validate(context.project);

    const hadValidationWarnings =
      app.logger.warningCount !== warningsBefore || app.logger.validationWarningCount !== 0;

    if (app.logger.errorCount !== errorsBefore) {
      throw new Error("TypeDoc validation reported errors -- see the log above.");
    }
    if (hadValidationWarnings && app.options.getValue("treatValidationWarningsAsErrors")) {
      throw new Error(
        "TypeDoc validation failed -- see the warnings above. " +
          "Fix the API reference, or adjust `validation` in docs/astro.config.mjs.",
      );
    }
  });
}

const sharedTypeDocConfig = {
  // Left on deliberately: `tsc --noEmit` (scripts/typecheck.sh ts) already compiles
  // src/, _docs-api-*.ts included, so letting TypeDoc re-run the TypeScript program
  // diagnostics would report the same errors from a second, slower gate. What is
  // wanted from TypeDoc is its *own* diagnostics, which is what `validation` below
  // and typeDocValidationGate turn on.
  skipErrorChecking: true,
  plugin: [typeDocValidationGate],
  // Every flag is listed, on or off, so that a change of mind is a diff rather than
  // a silent inheritance of a TypeDoc default. Measured counts are in the Resolution
  // section of docs/issues/34.
  validation: {
    // ON. The check issue 34 was opened for: a `{@link Foo}` whose target is not in
    // this entry point's project renders as bare text, so a broken cross-reference
    // is invisible in the published page. 15 real findings on first run, all fixed.
    invalidLink: true,
    // ON. The same failure in relative-path syntax -- a doc comment pointing at a
    // file that will not be copied to the output. 0 findings.
    invalidPath: true,
    // ON. Guards against a typo'd `@mergeModuleWith`, which is otherwise dropped
    // without a word. Nothing here uses the tag today. 0 findings.
    unusedMergeModuleWith: true,
    // ON. Fires when a link resolves to something other than its literal target.
    // 0 findings; note that TypeDoc raises this from its HTML renderer, so the
    // markdown theme used here may never exercise it.
    rewrittenLink: true,
    // OFF, deliberately, with a measured reason. 65 findings, and they are all one
    // fact: the nine `_docs-api-*.ts` entry points publish the builder functions but
    // not the `*Model` / `*Input` types those builders' signatures name. Satisfying
    // this check means either publishing ~30 model types (a redesign of what the API
    // reference is) or maintaining nine separate `intentionallyNotExported` lists --
    // a shared list cannot work, because TypeDoc warns about entries unused in a
    // given run. Tracked as follow-up work, not suppressed silently.
    notExported: false,
    // OFF, deliberately, with a measured reason. 18 findings, concentrated in
    // `App`'s properties, `CommentNode`, and the members of the `ModelInputProblem`
    // union. These are real documentation gaps rather than an architectural
    // mismatch, so they are worth writing -- as prose work, not as part of this
    // gate change. Tracked as follow-up work.
    notDocumented: false,
  },
  treatValidationWarningsAsErrors: true,
  disableSources: true,
  categorizeByGroup: false,
  navigation: {
    includeGroups: false,
    includeCategories: false,
  },
  hideGroupHeadings: true,
  hidePageHeader: true,
  hidePageTitle: true,
  hideBreadcrumbs: true,
  hideGenerator: true,
  cleanOutputDir: true,
  indexFormat: "htmlTable",
  interfacePropertiesFormat: "htmlTable",
  classPropertiesFormat: "htmlTable",
  parametersFormat: "htmlTable",
  enumMembersFormat: "htmlTable",
  typeDeclarationFormat: "htmlTable",
  propertyMembersFormat: "htmlTable",
  typeDeclarationVisibility: "compact",
  expandParameters: true,
  tableColumnSettings: {
    hideSources: true,
  },
};

export default defineConfig({
  site: "https://nathanjordan.github.io",
  base: "/ghagen/",
  integrations: [
    starlight({
      title: "ghagen",
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/nathanjordan/ghagen",
        },
      ],
      sidebar: [
        { label: "Home", link: "/" },
        {
          label: "Guides",
          items: [
            { label: "Cookbook", slug: "guides/cookbook" },
            { label: "DRY Patterns", slug: "guides/dry-patterns" },
            { label: "Escape Hatches", slug: "guides/escape-hatches" },
            { label: "Comments", slug: "guides/comments" },
          ],
        },
        {
          label: "Python",
          items: [
            { label: "CLI Reference", slug: "python/cli" },
            {
              label: "API Reference",
              autogenerate: { directory: "python/api" },
            },
          ],
        },
        {
          label: "TypeScript",
          items: [
            { label: "CLI Reference", slug: "typescript/cli" },
            {
              label: "API Reference",
              items: [
                appSidebar,
                workflowSidebar,
                jobSidebar,
                stepSidebar,
                triggersSidebar,
                permissionsSidebar,
                actionSidebar,
                expressionsSidebar,
                outputSidebar,
              ],
            },
          ],
        },
      ],
      plugins: [
        starlightThemeRapide(),
        starlightLlmsTxt({
          projectName: "ghagen",
          description:
            "Generate GitHub Actions workflows programmatically in Python or TypeScript instead of writing YAML",
          promote: ["index*", "guides/*"],
          customSets: [
            {
              label: "Guides",
              description: "Usage patterns and best practices",
              paths: ["guides/**"],
            },
            {
              label: "Python",
              description: "Python CLI and API reference",
              paths: ["python/**"],
            },
            {
              label: "TypeScript",
              description: "TypeScript CLI and API reference",
              paths: ["typescript/**"],
            },
          ],
        }),
        appTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api-app.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api/app",
          sidebar: { label: "App", collapsed: true },
          typeDoc: sharedTypeDocConfig,
        }),
        workflowTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api-workflow.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api/workflow",
          sidebar: { label: "Workflow", collapsed: true },
          typeDoc: sharedTypeDocConfig,
        }),
        jobTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api-job.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api/job",
          sidebar: { label: "Job", collapsed: true },
          typeDoc: sharedTypeDocConfig,
        }),
        stepTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api-step.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api/step",
          sidebar: { label: "Step", collapsed: true },
          typeDoc: sharedTypeDocConfig,
        }),
        triggersTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api-triggers.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api/triggers",
          sidebar: { label: "Triggers", collapsed: true },
          typeDoc: sharedTypeDocConfig,
        }),
        permissionsTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api-permissions.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api/permissions",
          sidebar: { label: "Permissions", collapsed: true },
          typeDoc: sharedTypeDocConfig,
        }),
        actionTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api-action.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api/action",
          sidebar: { label: "Action", collapsed: true },
          typeDoc: sharedTypeDocConfig,
        }),
        expressionsTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api-expressions.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api/expressions",
          sidebar: { label: "Expressions", collapsed: true },
          typeDoc: sharedTypeDocConfig,
        }),
        outputTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api-output.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api/output",
          sidebar: { label: "Output", collapsed: true },
          typeDoc: sharedTypeDocConfig,
        }),
      ],
    }),
  ],
});
