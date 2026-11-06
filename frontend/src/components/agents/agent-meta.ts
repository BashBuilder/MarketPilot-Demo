import type { AgentName, EventActor } from "@/lib/schemas";

export interface AgentMeta {
  name: string;
  description: string;
}

export const AGENT_META: Record<AgentName, AgentMeta> = {
  brief: {
    name: "Brief",
    description: "Turns the campaign idea into a structured brief.",
  },
  research: {
    name: "Research",
    description: "Maps audience segments, pain points and messaging angles.",
  },
  copywriter: {
    name: "Copywriter",
    description: "Writes headlines, descriptions and CTAs per channel.",
  },
  creative_director: {
    name: "Creative Director",
    description: "Sets the visual direction and generation prompts.",
  },
  designer: {
    name: "Designer",
    description: "Generates and records the campaign assets.",
  },
  compliance: {
    name: "Compliance",
    description: "Checks claims and policy restrictions.",
  },
  reviewer: {
    name: "Reviewer",
    description: "Scores the package against the rubric.",
  },
  supervisor: {
    name: "Supervisor",
    description: "Routes the run and escalates when needed.",
  },
};

const HUMAN_META: AgentMeta = {
  name: "Human review",
  description: "The approval gate where a person reviews the package.",
};

export function agentLabel(agent: EventActor): string {
  return agent === "human" ? HUMAN_META.name : AGENT_META[agent].name;
}
