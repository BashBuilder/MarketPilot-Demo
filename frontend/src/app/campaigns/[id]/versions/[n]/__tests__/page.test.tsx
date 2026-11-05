import { fireEvent, render, screen, within } from "@testing-library/react";
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
import {
  campaignId,
  haircarePackage,
  versionOne,
} from "@/mocks/fixtures";
import { haircareDirection } from "@/mocks/fixtures/package-visuals";
import { handlers } from "@/mocks/handlers";
import { resetMockStore } from "@/mocks/store";
import LoadingVersionPage from "../loading";
import VersionPage from "../page";

const server = setupServer(...handlers);

const { push, refresh } = vi.hoisted(() => ({
  push: vi.fn(),
  refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());
beforeEach(() => resetMockStore());
afterEach(() => server.resetHandlers());

async function renderVersionPage(n = "1") {
  const page = await VersionPage({
    params: Promise.resolve({ id: campaignId, n }),
  });
  return render(page);
}

function overrideVersion(packageData: typeof haircarePackage) {
  server.use(
    http.get("*/api/v1/campaigns/:id/versions/:version", () =>
      HttpResponse.json({ ...versionOne, package: packageData }),
    ),
  );
}

describe("VersionPage", () => {
  it("renders every review section from the mock package", async () => {
    await renderVersionPage();

    expect(
      screen.getByRole("heading", { level: 1, name: "Version 1" }),
    ).toBeInTheDocument();
    expect(screen.getByText(haircarePackage.brief.product)).toBeInTheDocument();
    expect(
      screen.getByText(haircarePackage.research.segments[0].name),
    ).toBeInTheDocument();
    expect(
      screen.getByText(haircarePackage.copy[0].headline),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: haircareDirection.image_prompts[0] }),
    ).toBeInTheDocument();
    expect(
      within(
        screen.getByRole("region", { name: "Compliance report" }),
      ).getByText(haircarePackage.compliance.items[0].check),
    ).toBeInTheDocument();
    expect(screen.getByText(String(haircarePackage.score.total))).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Version 1 is ready for review" }),
    ).toBeInTheDocument();
  });

  it("surfaces a failed compliance item", async () => {
    const failedItem = {
      check: "Guaranteed repair",
      passed: false,
      reason: "Implies a treatment outcome the product cannot guarantee.",
    };

    overrideVersion({
      ...haircarePackage,
      compliance: {
        items: [...haircarePackage.compliance.items, failedItem],
      },
    });

    await renderVersionPage();

    const row = screen.getByText(failedItem.check).closest("li");
    if (!row) throw new Error("Failed compliance item was not rendered");

    expect(row).toHaveAttribute("data-status", "failed");
    expect(within(row).getByText("Failed")).toBeInTheDocument();
    expect(within(row).getByText(failedItem.reason)).toBeInTheDocument();
  });

  it("falls back when an asset image fails to load", async () => {
    overrideVersion({
      ...haircarePackage,
      assets: [{ ...haircarePackage.assets[0], uri: "/missing-asset.webp" }],
    });

    await renderVersionPage();

    fireEvent.error(
      screen.getByRole("img", { name: haircareDirection.image_prompts[0] }),
    );

    expect(screen.getByText("Preview unavailable")).toBeInTheDocument();
  });

  it("shows an empty state for a missing version", async () => {
    server.use(
      http.get("*/api/v1/campaigns/:id/versions/:version", () =>
        HttpResponse.json(
          { error: { code: "version_not_found", message: "Version not found" } },
          { status: 404 },
        ),
      ),
    );

    await renderVersionPage("99");

    expect(
      screen.getByRole("heading", { name: "Version not found" }),
    ).toBeInTheDocument();
  });

  it("shows an empty state for an invalid version parameter", async () => {
    await renderVersionPage("not-a-number");

    expect(
      screen.getByRole("heading", { name: "Version not found" }),
    ).toBeInTheDocument();
  });

  it("shows an error state when the version cannot be loaded", async () => {
    server.use(
      http.get("*/api/v1/campaigns/:id/versions/:version", () =>
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

    await renderVersionPage();

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Could not load this version");
    expect(alert).toHaveTextContent("The version service is unavailable.");
  });

  it("renders a loading skeleton", () => {
    render(<LoadingVersionPage />);

    expect(
      screen.getByRole("status", { name: "Loading version" }),
    ).toBeInTheDocument();
  });
});
