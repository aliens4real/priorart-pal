import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../src/App";

describe("App", () => {
  it("renders the app title", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /priorart pal/i })).toBeInTheDocument();
  });

  it("lists the upcoming phases", () => {
    render(<App />);
    expect(screen.getByText(/patent corpus ingest/i)).toBeInTheDocument();
    expect(screen.getByText(/cohere reranking/i)).toBeInTheDocument();
    expect(screen.getByText(/cognito auth/i)).toBeInTheDocument();
  });
});
