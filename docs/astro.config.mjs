import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightTypeDoc, { typeDocSidebarGroup } from "starlight-typedoc";

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
        { label: "Cookbook", slug: "cookbook" },
        {
          label: "Guides",
          items: [
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
            typeDocSidebarGroup,
          ],
        },
      ],
      plugins: [
        starlightTypeDoc({
          entryPoints: ["../packages/typescript/src/_docs-api.ts"],
          tsconfig: "../packages/typescript/tsconfig.json",
          output: "typescript/api",
          sidebar: {
            label: "API Reference",
            collapsed: true,
          },
        }),
      ],
    }),
  ],
});
