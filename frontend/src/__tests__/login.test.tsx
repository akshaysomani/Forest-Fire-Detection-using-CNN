import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "@/app/auth/login/page";
import { useAuthStore } from "@/store/auth-store";

// Mock next/navigation router hooks
jest.mock("next/navigation", () => ({
  useRouter() {
    return {
      prefetch: () => null,
      push: jest.fn(),
    };
  },
}));

describe("Inference Suite Authentication Form Tests", () => {
  beforeEach(() => {
    // Reset Zustand stores
    useAuthStore.getState().clearAuth();
  });

  test("Renders login inputs and labels successfully", () => {
    render(<LoginPage />);

    expect(screen.getByLabelText(/Username or Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Authenticate Access/i })).toBeInTheDocument();
  });

  test("Renders validation warning messages on empty form submissions", async () => {
    render(<LoginPage />);

    const submitBtn = screen.getByRole("button", { name: /Authenticate Access/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Username or Email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Password is required/i)).toBeInTheDocument();
    });
  });
});
