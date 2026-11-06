import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { haircarePackage } from "@/mocks/fixtures";
import { ComplianceReport } from "../ComplianceReport";

const { compliance } = haircarePackage;

describe("ComplianceReport", () => {
  it("renders every fixture check with its reason and pass status", () => {
    render(<ComplianceReport compliance={compliance} />);

    expect(
      screen.getByRole("heading", { level: 2, name: "Compliance report" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        `${compliance.items.length} of ${compliance.items.length} checks passed`,
      ),
    ).toBeInTheDocument();

    for (const item of compliance.items) {
      expect(screen.getByText(item.check)).toBeInTheDocument();
      expect(screen.getByText(item.reason)).toBeInTheDocument();
    }
    expect(screen.getAllByText("Passed")).toHaveLength(
      compliance.items.length,
    );
  });

  it("distinguishes a failed item without relying on colour alone", () => {
    const failedItem = {
      check: "Guaranteed repair",
      passed: false,
      reason: "Implies a treatment outcome the product cannot guarantee.",
    };

    render(
      <ComplianceReport
        compliance={{ items: [compliance.items[0], failedItem] }}
      />,
    );

    const failedRow = screen.getByText(failedItem.check).closest("li");
    if (!failedRow) throw new Error("Failed compliance item was not rendered");

    expect(failedRow).toHaveAttribute("data-status", "failed");
    expect(within(failedRow).getByText("Failed")).toBeInTheDocument();
    expect(within(failedRow).getByText(failedItem.reason)).toBeInTheDocument();
    expect(failedRow.querySelector("svg")).not.toBeNull();
    expect(screen.getByText(/1 need attention/)).toBeInTheDocument();
  });

  it("shows an empty state when the report is missing or empty", () => {
    const { rerender } = render(<ComplianceReport compliance={undefined} />);

    expect(
      screen.getByRole("heading", { name: "No compliance report yet" }),
    ).toBeInTheDocument();

    rerender(<ComplianceReport compliance={{ items: [] }} />);

    expect(
      screen.getByRole("heading", { name: "No compliance report yet" }),
    ).toBeInTheDocument();
  });

  it("renders backend text as plain text, never as HTML", () => {
    const reason = "<strong>Do not ship this claim</strong>";

    render(
      <ComplianceReport
        compliance={{
          items: [{ ...compliance.items[0], reason }],
        }}
      />,
    );

    expect(screen.getByText(reason)).toBeInTheDocument();
    expect(document.querySelector("strong")).toBeNull();
  });
});
