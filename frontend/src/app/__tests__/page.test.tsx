import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  vi,
} from "vitest";
import type { CampaignSummary } from "@/lib/schemas";
import { campaignSummary } from "@/mocks/fixtures";
import { handlers } from "@/mocks/handlers";
import { resetMockStore } from "@/mocks/store";
import LoadingCampaignsPage from "../loading";
import HomePage from "../page";

const { refresh } = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());
beforeEach(() => {
  resetMockStore();
  refresh.mockClear();
});
afterEach(() => server.resetHandlers());

function overrideCampaigns(campaigns: CampaignSummary[]) {
  server.use(
    http.get("*/api/v1/campaigns", () => HttpResponse.json(campaigns)),
  );
}

function campaign(
  id: string,
  idea: string,
  createdAt: string,
): CampaignSummary {
  return {
    ...campaignSummary,
    id,
    idea,
    created_at: createdAt,
    updated_at: createdAt,
  };
}

describe("HomePage", () => {
  it("shows a campaign card with idea, status, score, date and overview link", async () => {
    render(await HomePage());

    const list = screen.getByRole("list", { name: "Campaigns" });
    const card = within(list).getByRole("listitem");
    const idea = within(card).getByText(campaignSummary.idea);

    expect(idea).toHaveClass("line-clamp-2");
    expect(within(card).getByText("Awaiting approval")).toBeInTheDocument();
    expect(within(card).getByText("86 / 100")).toBeInTheDocument();
    expect(within(card).getByText("2026-11-05")).toBeInTheDocument();
    expect(within(card).getByRole("link")).toHaveAttribute(
      "href",
      `/campaigns/${campaignSummary.id}`,
    );
  });

  it("orders campaigns newest first by creation time", async () => {
    const newest = campaign(
      "11111111-1111-4111-8111-111111111111",
      "Newest campaign",
      "2026-11-05T09:00:00.000Z",
    );
    const middle = campaign(
      "22222222-2222-4222-8222-222222222222",
      "Middle campaign",
      "2026-11-04T09:00:00.000Z",
    );
    const oldest = campaign(
      "33333333-3333-4333-8333-333333333333",
      "Oldest campaign",
      "2026-11-03T09:00:00.000Z",
    );
    overrideCampaigns([middle, oldest, newest]);

    render(await HomePage());

    const links = within(
      screen.getByRole("list", { name: "Campaigns" }),
    ).getAllByRole("link");

    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      `/campaigns/${newest.id}`,
      `/campaigns/${middle.id}`,
      `/campaigns/${oldest.id}`,
    ]);
  });

  it("shows an empty state linking to the new campaign page", async () => {
    overrideCampaigns([]);

    render(await HomePage());

    expect(
      screen.getByRole("heading", { name: "No campaigns yet" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "New campaign" }),
    ).toHaveAttribute("href", "/campaigns/new");
  });

  it("shows the API error and retries with a refresh", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/campaigns", () =>
        HttpResponse.json(
          {
            error: {
              code: "service_unavailable",
              message: "The campaign service is unavailable.",
            },
          },
          { status: 503 },
        ),
      ),
    );

    render(await HomePage());

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Could not load campaigns");
    expect(alert).toHaveTextContent("The campaign service is unavailable.");

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("renders a loading skeleton", () => {
    render(<LoadingCampaignsPage />);

    expect(
      screen.getByRole("status", { name: "Loading campaigns" }),
    ).toBeInTheDocument();
  });
});
