import { render, screen, waitFor } from "@testing-library/react";
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
import NewCampaignPage from "../page";
import { handlers } from "@/mocks/handlers";
import { resetMockStore } from "@/mocks/store";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());
beforeEach(() => {
  resetMockStore();
  push.mockClear();
});
afterEach(() => server.resetHandlers());

async function submitIdea(idea: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Campaign idea"), idea);
  await user.click(screen.getByRole("button", { name: "Start campaign" }));
}

describe("NewCampaignPage", () => {
  it("creates a campaign and redirects to its live run", async () => {
    render(<NewCampaignPage />);

    await submitIdea("Launch a travel mug");

    await waitFor(() => expect(push).toHaveBeenCalledTimes(1));
    expect(push.mock.calls[0][0]).toMatch(
      /^\/campaigns\/[0-9a-f-]{36}\/run\/[0-9a-f-]{36}$/,
    );
  });

  it("shows an ApiError message in the ErrorState and stays put", async () => {
    server.use(
      http.post("*/api/v1/campaigns", () =>
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

    render(<NewCampaignPage />);

    await submitIdea("Launch a travel mug");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Could not start the campaign");
    expect(alert).toHaveTextContent("The campaign service is unavailable.");
    expect(push).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Start campaign" }),
    ).toBeEnabled();
  });
});
