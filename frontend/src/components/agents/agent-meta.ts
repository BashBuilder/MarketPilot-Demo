import type { AgentName } from "@/lib/schemas";

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

export function agentLabel(agent: AgentName): string {
  return AGENT_META[agent].name;
}
