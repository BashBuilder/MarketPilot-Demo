export interface ExamplePrompt {
  label: string;
  idea: string;
}

export const EXAMPLE_PROMPTS: readonly ExamplePrompt[] = [
  {
    label: "Hair-care launch",
    idea: "Create an advertising campaign for a fictional hair-care product targeting adults aged 25 to 40.",
  },
  {
    label: "Travel mug",
    idea: "Launch a reusable travel mug for commuters who care about good design and cutting single-use plastic.",
  },
  {
    label: "Plant-based skincare",
    idea: "Introduce a plant-based skincare line for first-time buyers who want a simple, fragrance-free routine.",
  },
];
