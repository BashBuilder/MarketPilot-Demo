import { render, screen } from "@testing-library/react";
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
import { campaignId } from "@/mocks/fixtures";
import { handlers } from "@/mocks/handlers";
import { resetMockStore } from "@/mocks/store";
import LoadingCampaignPage from "../loading";
import CampaignPage from "../page";

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

describe("CampaignPage states", () => {
  it("shows the API error and retries with a refresh", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/campaigns/:id", () =>
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

    render(await CampaignPage({ params: Promise.resolve({ id: campaignId }) }));

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Could not load this campaign");
    expect(alert).toHaveTextContent("The campaign service is unavailable.");

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("renders a loading skeleton", () => {
    render(<LoadingCampaignPage />);

    expect(
      screen.getByRole("status", { name: "Loading campaign" }),
    ).toBeInTheDocument();
  });
});
