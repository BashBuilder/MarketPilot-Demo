import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
import { VersionApproval } from "../VersionApproval";
import type { CampaignStatus } from "@/lib/schemas";
import { handlers } from "@/mocks/handlers";
import { campaignId, runId } from "@/mocks/fixtures";
import { mockStore, resetMockStore } from "@/mocks/store";

const { push, refresh } = vi.hoisted(() => ({
  push: vi.fn(),
  refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());
beforeEach(() => {
  resetMockStore();
  push.mockClear();
  refresh.mockClear();
});
afterEach(() => server.resetHandlers());

function renderApproval(
  campaignStatus: CampaignStatus = "awaiting_approval",
  isLatest = true,
) {
  return render(
    <VersionApproval
      campaignId={campaignId}
      version={1}
      runId={runId}
      campaignStatus={campaignStatus}
      isLatest={isLatest}
    />,
  );
}

describe("VersionApproval", () => {
  it("approves the run and shows the approved state", async () => {
    const user = userEvent.setup();
    renderApproval();

    await user.click(screen.getByRole("button", { name: "Approve" }));
    await user.click(screen.getByRole("button", { name: "Approve version 1" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Version 1 approved",
    );
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
    expect(mockStore.campaigns.get(campaignId)?.status).toBe("completed");
    expect(
      screen.queryByRole("button", { name: "Request revision" }),
    ).not.toBeInTheDocument();
  });

  it("submits a revision and redirects to the new run", async () => {
    const user = userEvent.setup();
    renderApproval();

    await user.click(screen.getByRole("button", { name: "Request revision" }));
    const dialog = screen.getByRole("dialog");
    await user.type(
      within(dialog).getByLabelText("What should change?"),
      "Sharper headline",
    );
    await user.click(
      within(dialog).getByRole("button", { name: "Request revision" }),
    );

    await waitFor(() => expect(push).toHaveBeenCalledTimes(1));
    const target = String(push.mock.calls[0]?.[0]);
    expect(target).toMatch(
      new RegExp(`^/campaigns/${campaignId}/run/[0-9a-f-]{36}$`),
    );
    expect(mockStore.runs.has(target.split("/").at(-1) ?? "")).toBe(true);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("shows an HTTP error and re-enables the controls", async () => {
    server.use(
      http.post("*/api/v1/runs/:runId/approve", () =>
        HttpResponse.json(
          {
            error: {
              code: "conflict",
              message: "The run is no longer awaiting approval.",
            },
          },
          { status: 409 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApproval();

    await user.click(screen.getByRole("button", { name: "Approve" }));
    await user.click(screen.getByRole("button", { name: "Approve version 1" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The run is no longer awaiting approval.");
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("sends only one request for a double click", async () => {
    let requests = 0;
    server.use(
      http.post("*/api/v1/runs/:runId/approve", () => {
        requests += 1;
        return HttpResponse.json({
          status: "completed",
          version: 1,
        });
      }),
    );
    const user = userEvent.setup();
    renderApproval();

    await user.click(screen.getByRole("button", { name: "Approve" }));
    const confirm = screen.getByRole("button", { name: "Approve version 1" });
    fireEvent.click(confirm);
    fireEvent.click(confirm);

    await waitFor(() => expect(requests).toBe(1));
  });

  it("only shows the panel while the campaign is awaiting approval", () => {
    const { unmount } = renderApproval("running");
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
    unmount();

    renderApproval("completed");
    expect(screen.getByRole("status")).toHaveTextContent("Version 1 approved");
  });

  it("does not offer approval for an older version", () => {
    renderApproval("awaiting_approval", false);
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
  });
});
