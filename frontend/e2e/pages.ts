// These IDs match src/mocks/fixtures/campaign.ts. The mock API seeds one
// campaign and one run so each page can be reached without setup.
export const mockCampaignId = "7c9e6679-7425-40de-944b-e07fc1f90ae7";
export const mockRunId = "0f8fad5b-d9cb-469f-a165-70867728950e";

export interface AppPage {
  name: string;
  path: string;
  heading: string;
}

export const appPages: readonly AppPage[] = [
  {
    name: "landing",
    path: "/",
    heading: "Campaigns, composed by a team of agents.",
  },
  {
    name: "campaign list",
    path: "/campaigns",
    heading: "Campaigns",
  },
  {
    name: "new campaign",
    path: "/campaigns/new",
    heading: "What should the agents create?",
  },
  {
    name: "live run",
    path: `/campaigns/${mockCampaignId}/run/${mockRunId}`,
    heading: "Ready for your review",
  },
  {
    name: "version review",
    path: `/campaigns/${mockCampaignId}/versions/1`,
    heading: "Version 1",
  },
  {
    name: "version history",
    path: `/campaigns/${mockCampaignId}/versions`,
    heading: "Version history",
  },
  {
    name: "campaign overview",
    path: `/campaigns/${mockCampaignId}`,
    heading:
      "Create an advertising campaign for a fictional hair-care product targeting adults aged 25 to 40",
  },
];
