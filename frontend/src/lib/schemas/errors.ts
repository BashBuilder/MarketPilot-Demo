import { z } from "zod";
import { text } from "./common";

export const apiErrorBody = z.object({
  error: z.object({
    code: text,
    message: text,
    details: z.unknown().optional(),
  }),
});

export type ApiErrorBody = z.infer<typeof apiErrorBody>;
