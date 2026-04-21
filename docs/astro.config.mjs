import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightThemeRapide from "starlight-theme-rapide";
import starlightLlmsTxt from "starlight-llms-txt";
import { createStarlightTypeDocPlugin } from "starlight-typedoc";

const [appTypeDoc, appSidebar] = createStarlightTypeDocPlugin();
const [workflowTypeDoc, workflowSidebar] = createStarlightTypeDocPlugin();
const [jobTypeDoc, jobSidebar] = createStarlightTypeDocPlugin();
const [stepTypeDoc, stepSidebar] = createStarlightTypeDocPlugin();
const [triggersTypeDoc, triggersSidebar] = createStarlightTypeDocPlugin();
const [permissionsTypeDoc, permissionsSidebar] = createStarlightTypeDocPlugin();
const [actionTypeDoc, actionSidebar] = createStarlightTypeDocPlugin();
const [expressionsTypeDoc, expressionsSidebar] = createStarlightTypeDocPlugin();
const [outputTypeDoc, outputSidebar] = createStarlightTypeDocPlugin();

const sharedTypeDocConfig = {
  skipErrorChecking: true,
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
  flattenOutputFiles: true,
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
            { label: "Linting", slug: "python/linting" },
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
            { label: "Linting", slug: "typescript/linting" },
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
              description: "Python CLI, linting, and API reference",
              paths: ["python/**"],
            },
            {
              label: "TypeScript",
              description: "TypeScript CLI, linting, and API reference",
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
