"use client";

import {
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import { ExamplePrompts } from "./ExamplePrompts";

export const IDEA_MAX_LENGTH = 2000;

export interface IdeaFormProps {
  onSubmit: (idea: string) => Promise<void>;
}

function validateIdea(value: string): string | null {
  if (value.trim().length === 0) {
    return "Describe your campaign idea before starting.";
  }
  if (value.length > IDEA_MAX_LENGTH) {
    return `Keep your idea to ${IDEA_MAX_LENGTH} characters or fewer.`;
  }
  return null;
}

export function IdeaForm({ onSubmit }: IdeaFormProps) {
  const [idea, setIdea] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const validationError = validateIdea(idea);
    if (validationError) {
      setError(validationError);
      textareaRef.current?.focus();
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(idea.trim());
    } catch (cause) {
      setError(
        cause instanceof Error && cause.message
          ? cause.message
          : "Could not start the campaign. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function chooseExample(prompt: string) {
    setIdea(prompt);
    setError(null);
    textareaRef.current?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      noValidate
      aria-busy={submitting}
      className="flex w-full flex-col gap-6"
    >
      <Field data-invalid={error !== null}>
        <FieldLabel htmlFor="campaign-idea">Campaign idea</FieldLabel>
        <Textarea
          id="campaign-idea"
          ref={textareaRef}
          value={idea}
          onChange={(event) => {
            setIdea(event.target.value);
            if (error) setError(null);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Describe the product, the audience and the feeling the campaign should create."
          rows={6}
          maxLength={IDEA_MAX_LENGTH}
          required
          disabled={submitting}
          aria-invalid={error !== null}
          aria-describedby={
            error
              ? "campaign-idea-hint campaign-idea-count campaign-idea-error"
              : "campaign-idea-hint campaign-idea-count"
          }
          className="min-h-36"
        />
        <div className="flex flex-wrap items-start justify-between gap-3">
          <FieldDescription id="campaign-idea-hint">
            Be specific about the product, audience and goal. The agents handle
            the research and production.
          </FieldDescription>
          <span
            id="campaign-idea-count"
            className="shrink-0 text-sm tabular-nums text-muted-foreground"
          >
            {idea.length} / {IDEA_MAX_LENGTH}
          </span>
        </div>
        {error ? <FieldError id="campaign-idea-error">{error}</FieldError> : null}
      </Field>

      <ExamplePrompts disabled={submitting} onSelect={chooseExample} />

      <div className="flex flex-col gap-3 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          A full run takes a few minutes. You review the package before
          anything is approved.
        </p>
        <Button
          type="submit"
          size="lg"
          disabled={submitting}
          className="sm:shrink-0"
        >
          {submitting ? "Starting campaign…" : "Start campaign"}
        </Button>
      </div>
    </form>
  );
}
