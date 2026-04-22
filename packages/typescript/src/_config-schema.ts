/**
 * Zod schema for `.ghagen.yml` configuration.
 *
 * Single source of truth for config shape, types, and defaults.
 */

import { z } from "zod/v4";

export const optionsSchema = z.object({
  auto_dedent: z.boolean().default(true),
});

export const ghagenYmlSchema = z.object({
  options: optionsSchema.optional(),
  entrypoint: z.string().optional(),
});

export type GhagenYmlConfig = z.infer<typeof ghagenYmlSchema>;
export type GhagenOptions = z.infer<typeof optionsSchema>;
