import { Button } from "@/components/ui/button";
import { EXAMPLE_PROMPTS } from "./example-prompts";

interface ExamplePromptsProps {
  disabled: boolean;
  onSelect: (idea: string) => void;
}

export function ExamplePrompts({ disabled, onSelect }: ExamplePromptsProps) {
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="text-sm font-medium">Try an example</legend>
      <div className="flex flex-wrap gap-2">
        {EXAMPLE_PROMPTS.map((prompt) => (
          <Button
            key={prompt.label}
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            onClick={() => onSelect(prompt.idea)}
          >
            {prompt.label}
          </Button>
        ))}
      </div>
    </fieldset>
  );
}
