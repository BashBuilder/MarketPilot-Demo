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
import type { VersionSummary } from "@/lib/schemas";
import { campaignId } from "@/mocks/fixtures";
import { handlers } from "@/mocks/handlers";
import { resetMockStore } from "@/mocks/store";
import LoadingVersionsPage from "../loading";
import VersionsPage from "../page";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());
beforeEach(() => resetMockStore());
afterEach(() => server.resetHandlers());

function overrideVersions(versions: VersionSummary[]) {
  server.use(
    http.get("*/api/v1/campaigns/:id/versions", () =>
      HttpResponse.json(versions),
    ),
  );
}

async function renderVersionsPage() {
  const page = await VersionsPage({
    params: Promise.resolve({ id: campaignId }),
  });
  return render(page);
}

describe("VersionsPage", () => {
  it("lists versions newest first with date, score, status and detail links", async () => {
    overrideVersions([
      {
        version: 1,
        parent_version: null,
        created_at: "2026-11-03T09:00:00.000Z",
        total_score: 86,
        run_status: "approved",
      },
      {
        version: 3,
        parent_version: 2,
        created_at: "2026-11-05T09:00:00.000Z",
        total_score: 91,
        run_status: "awaiting_approval",
      },
      {
        version: 2,
        parent_version: 1,
        created_at: "2026-11-04T09:00:00.000Z",
        total_score: null,
        run_status: "revision_requested",
      },
    ]);

    await renderVersionsPage();

    const list = screen.getByRole("list", { name: "Version history" });
    const links = within(list).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      `/campaigns/${campaignId}/versions/3`,
      `/campaigns/${campaignId}/versions/2`,
      `/campaigns/${campaignId}/versions/1`,
    ]);

    const items = within(list).getAllByRole("listitem");
    const [newest, middle, oldest] = items;
    if (!newest || !middle || !oldest) {
      throw new Error("Expected three version rows");
    }

    expect(within(newest).getByText("Version 3")).toBeInTheDocument();
    expect(within(newest).getByText("2026-11-05")).toBeInTheDocument();
    expect(within(newest).getByText("91 / 100")).toBeInTheDocument();
    expect(within(newest).getByText("Awaiting approval")).toBeInTheDocument();
    expect(within(middle).getByText("No score")).toBeInTheDocument();
    expect(
      within(middle).getByText("Revision requested"),
    ).toBeInTheDocument();
    expect(within(oldest).getByText("Approved")).toBeInTheDocument();
  });

  it("shows an empty state when the campaign has no versions", async () => {
    overrideVersions([]);

    await renderVersionsPage();

    expect(
      screen.getByRole("heading", { name: "No versions yet" }),
    ).toBeInTheDocument();
  });

  it("shows an error state with the API message", async () => {
    server.use(
      http.get("*/api/v1/campaigns/:id/versions", () =>
        HttpResponse.json(
          {
            error: {
              code: "service_unavailable",
              message: "The version service is unavailable.",
            },
          },
          { status: 503 },
        ),
      ),
    );

    await renderVersionsPage();

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Could not load version history");
    expect(alert).toHaveTextContent("The version service is unavailable.");
  });

  it("renders a loading skeleton", () => {
    render(<LoadingVersionsPage />);

    expect(
      screen.getByRole("status", { name: "Loading version history" }),
    ).toBeInTheDocument();
  });
});
