import { render, screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
} from "vitest";
import type { CampaignSummary } from "@/lib/schemas";
import { campaignId, campaignSummary, runId } from "@/mocks/fixtures";
import { handlers } from "@/mocks/handlers";
import { resetMockStore } from "@/mocks/store";
import CampaignPage from "../page";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());
beforeEach(() => resetMockStore());
afterEach(() => server.resetHandlers());

function overrideCampaign(campaign: CampaignSummary) {
  server.use(
    http.get("*/api/v1/campaigns/:id", () => HttpResponse.json(campaign)),
  );
}

async function renderCampaignPage() {
  render(await CampaignPage({ params: Promise.resolve({ id: campaignId }) }));
}

describe("CampaignPage", () => {
  it("links to the live run when a run is in progress", async () => {
    overrideCampaign({ ...campaignSummary, status: "running" });

    await renderCampaignPage();

    expect(
      screen.getByRole("heading", { level: 1, name: campaignSummary.idea }),
    ).toBeInTheDocument();

    const summary = screen.getByRole("region", { name: "Version 1" });
    expect(within(summary).getByText("Running")).toBeInTheDocument();
    expect(within(summary).getByText("86 / 100")).toBeInTheDocument();
    expect(
      within(summary).getByRole("link", { name: "Review latest version" }),
    ).toHaveAttribute("href", `/campaigns/${campaignId}/versions/1`);
    expect(
      within(summary).getByRole("link", { name: "Version history" }),
    ).toHaveAttribute("href", `/campaigns/${campaignId}/versions`);

    const notice = screen.getByRole("region", { name: "Run in progress" });
    expect(
      within(notice).getByRole("link", { name: "Open live run" }),
    ).toHaveAttribute("href", `/campaigns/${campaignId}/run/${runId}`);
  });

  it("hides the live-run notice when no run is active", async () => {
    await renderCampaignPage();

    const summary = screen.getByRole("region", { name: "Version 1" });
    expect(within(summary).getByText("Awaiting approval")).toBeInTheDocument();
    expect(
      within(summary).getByRole("link", { name: "Review latest version" }),
    ).toHaveAttribute("href", `/campaigns/${campaignId}/versions/1`);

    expect(
      screen.queryByRole("region", { name: "Run in progress" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Open live run" }),
    ).not.toBeInTheDocument();
  });

  it("shows a not-found state when the campaign does not exist", async () => {
    server.use(
      http.get("*/api/v1/campaigns/:id", () =>
        HttpResponse.json(
          {
            error: {
              code: "campaign_not_found",
              message: "Campaign not found",
            },
          },
          { status: 404 },
        ),
      ),
    );

    await renderCampaignPage();

    expect(
      screen.getByRole("heading", { name: "Campaign not found" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Back to campaigns" }),
    ).toHaveAttribute("href", "/");
  });

});
