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
} from "vitest";
import type { VersionDiff, VersionSummary } from "@/lib/schemas";
import { campaignId, versionOneId } from "@/mocks/fixtures";
import { handlers } from "@/mocks/handlers";
import { resetMockStore } from "@/mocks/store";
import { VersionCompare } from "../VersionCompare";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());
beforeEach(() => resetMockStore());
afterEach(() => server.resetHandlers());

function summary(version: number): VersionSummary {
  return {
    version,
    parent_version_id: version > 1 ? versionOneId : null,
    created_at: `2026-11-0${version}T09:00:00.000Z`,
    score: 80 + version,
  };
}

function mockDiff(changes: VersionDiff["changes"]) {
  server.use(
    http.get("*/api/v1/campaigns/:id/versions/:from/diff/:to", () =>
      HttpResponse.json({ from: 1, to: 2, changes }),
    ),
  );
}

async function compare() {
  const user = userEvent.setup();
  render(<VersionCompare campaignId={campaignId} versions={[summary(1), summary(2)]} />);
  await user.selectOptions(screen.getByLabelText("From version"), "1");
  await user.selectOptions(screen.getByLabelText("To version"), "2");
  await user.click(screen.getByRole("button", { name: "Compare versions" }));
  return user;
}

describe("VersionCompare", () => {
  it("shows a copy change side by side with a text marker", async () => {
    mockDiff([
      {
        path: "copy.variants.0.headline",
        before: "Shine for a day",
        after: "Shine past the commute",
      },
    ]);
    await compare();

    expect(
      await screen.findByRole("heading", { name: "Copy" }),
    ).toBeInTheDocument();
    expect(screen.getByText("copy.variants.0.headline")).toBeInTheDocument();
    expect(screen.getByText("Shine for a day")).toBeInTheDocument();
    expect(screen.getByText("Shine past the commute")).toBeInTheDocument();
    expect(screen.getByText("Changed")).toBeInTheDocument();
    expect(screen.getByText("Before")).toBeInTheDocument();
    expect(screen.getByText("After")).toBeInTheDocument();
  });

  it("groups asset changes under Assets", async () => {
    mockDiff([
      {
        path: "assets.assets.0.uri",
        before: "/assets/old.webp",
        after: "/assets/new.webp",
      },
    ]);
    await compare();

    const group = await screen.findByRole("region", {
      name: "Changes in Assets",
    });
    expect(
      screen.getByRole("heading", { name: "Assets" }),
    ).toBeInTheDocument();
    expect(group).toHaveTextContent("/assets/old.webp");
    expect(group).toHaveTextContent("/assets/new.webp");
  });

  it("says when there are no changes", async () => {
    mockDiff([]);
    await compare();

    expect(
      await screen.findByText("No changes between these versions."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Changed")).toBeNull();
  });

  it("shows the API error when the comparison fails", async () => {
    server.use(
      http.get("*/api/v1/campaigns/:id/versions/:from/diff/:to", () =>
        HttpResponse.json(
          {
            error: {
              code: "diff_unavailable",
              message: "The comparison service is unavailable.",
            },
          },
          { status: 503 },
        ),
      ),
    );
    await compare();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Could not compare versions");
    expect(alert).toHaveTextContent("The comparison service is unavailable.");
  });
});
