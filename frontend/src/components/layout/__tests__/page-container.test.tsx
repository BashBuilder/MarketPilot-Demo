import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PageContainer } from "../page-container";

describe("PageContainer", () => {
  it("centres content in the shared responsive width", () => {
    render(
      <PageContainer data-testid="container" className="custom-class">
        Content
      </PageContainer>,
    );

    const container = screen.getByTestId("container");
    expect(container).toHaveTextContent("Content");
    expect(container).toHaveClass(
      "mx-auto",
      "w-full",
      "max-w-7xl",
      "px-md",
      "sm:px-lg",
      "lg:px-xl",
      "custom-class",
    );
  });
});
