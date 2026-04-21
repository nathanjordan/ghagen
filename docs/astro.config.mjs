import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightThemeRapide from "starlight-theme-rapide";
import starlightTypeDoc from "starlight-typedoc";

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
              autogenerate: { directory: "typescript/api" },
            },
          ],
        },
      ],
      plugins: [
        starlightThemeRapide(),
        starlightTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api",
          sidebar: {
            label: "API Reference",
            collapsed: false,
          },
          typeDoc: {
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
            tableColumnSettings: {
              hideSources: true,
            },
          },
        }),
      ],
    }),
  ],
});
