/**
 * Minimal ghagen example — one workflow with a single job.
 *
 * Run: npx ghagen synth -c examples/minimal.workflows.ts
 */

import {
  App,
  job,
  permissions,
  pushTrigger,
  prTrigger,
  step,
  workflow,
} from "../src/index.js";

export const app = new App({ root: "." });

const ci = workflow({
  name: "CI",
  on: {
    push: pushTrigger({ branches: ["main"] }),
    pullRequest: prTrigger({ branches: ["main"] }),
  },
  permissions: permissions({ contents: "read" }),
  jobs: {
    test: job({
      runsOn: "ubuntu-latest",
      timeoutMinutes: 10,
      steps: [
        step({ uses: "actions/checkout@v4" }),
        step({ name: "Run tests", run: "npm test" }),
      ],
    }),
  },
});

app.addWorkflow(ci, "ci.yml");
