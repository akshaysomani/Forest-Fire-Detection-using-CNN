import React from "react";
import { render, screen } from "@testing-library/react";
import PredictionsPage from "@/app/predictions/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock next/navigation router hooks
jest.mock("next/navigation", () => ({
  useRouter() {
    return {
      push: jest.fn(),
    };
  },
}));

describe("CNN Prediction Interface Tests", () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  test("Renders prediction upload form container successfully", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <PredictionsPage />
      </QueryClientProvider>
    );

    expect(screen.getByText(/CNN INFERENCE STUDIO/i)).toBeInTheDocument();
    expect(screen.getByText(/Drag & Drop Image Here/i)).toBeInTheDocument();
  });
});
