import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { api } from "./api";

describe("college website", () => {
  it("renders the public home page and navigation", () => {
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: /big ideas/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /main navigation/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /apply now/i })).toHaveAttribute("href", "/admissions");
  });

  it("provides an accessible responsive menu button", () => {
    render(<MemoryRouter><App /></MemoryRouter>);
    const menu = screen.getByRole("button", { name: /open navigation/i });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
  });

  it("shows a real error instead of a success state when the inquiry API fails", async () => {
    vi.spyOn(api, "contact").mockRejectedValueOnce(new Error("Service unavailable"));
    render(<MemoryRouter initialEntries={["/admissions"]}><App /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: "Sample Visitor" } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: "visitor@example.edu" } });
    const form = screen.getByRole("button", { name: /send an inquiry/i }).closest("form");
    fireEvent.submit(form!);
    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    expect(screen.queryByText(/inquiry was received/i)).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it("shows available updates when one updates API fails", async () => {
    vi.spyOn(api, "programs").mockResolvedValue([]);
    vi.spyOn(api, "news").mockResolvedValue([{
      id: 1,
      title: "Campus library hours",
      body: "The library is open weekdays.",
      category: "Campus",
      created_at: "2026-10-28T09:00:00Z",
    }]);
    vi.spyOn(api, "notices").mockRejectedValue(new Error("Notices unavailable"));
    vi.spyOn(api, "events").mockResolvedValue([]);
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Campus library hours" })).toBeInTheDocument();
    expect(await screen.findByRole("status")).toHaveTextContent(/Some live news and notices are unavailable.*Notices unavailable/i);
    vi.restoreAllMocks();
  });

  it("reports password-reset API failures without implying a reset was sent", async () => {
    vi.spyOn(api, "requestPasswordReset").mockRejectedValueOnce(new Error("Service unavailable"));
    render(<MemoryRouter initialEntries={["/forgot-password"]}><App /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: "visitor@example.edu" } });
    const form = screen.getByRole("button", { name: /send password reset link/i }).closest("form");
    fireEvent.submit(form!);
    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    expect(screen.queryByText(/account email will be sent/i)).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it("does not submit a password reset when the confirmation differs", async () => {
    const resetPassword = vi.spyOn(api, "resetPassword");
    render(<MemoryRouter initialEntries={["/reset-password?token=sample-token"]}><App /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText(/^New password/), { target: { value: "new-secure-password-2026" } });
    fireEvent.change(screen.getByLabelText(/^Confirm new password/), { target: { value: "different-secure-password-2026" } });
    const form = screen.getByRole("button", { name: /reset password/i }).closest("form");
    fireEvent.submit(form!);
    expect(await screen.findByRole("alert")).toHaveTextContent("Passwords do not match.");
    expect(resetPassword).not.toHaveBeenCalled();
    vi.restoreAllMocks();
  });
});
