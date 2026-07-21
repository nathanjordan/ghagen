import { App } from "../../src/app.js";
import { tsRef } from "./ts-helper.js";
import { esmRef } from "./esm-helper.mjs";
import { cjsRef } from "./cjs-helper.js";
import { internalRef } from "ghagen-internal";

const app = new App();
export const _refs = [tsRef, esmRef, cjsRef, internalRef];
export { app };
