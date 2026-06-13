import React from "react";
import { render, screen } from "@testing-library/react";
import DashboardPage from "@/app/dashboard/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock next/navigation router hooks
jest.mock("next/navigation", () => ({
  useRouter() {
    return {
      push: jest.fn(),
    };
  },
}));

// Mock Recharts elements since they don't render inside JSdom SVG layout containers correctly
jest.mock("recharts", () => {
  const OriginalModule = jest.requireActual("recharts");
  return {
    ...OriginalModule,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 800, height: 400 }}>{children}</div>,
  };
});

describe("Inference Suite Dashboard Widget Tests", () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  test("Renders loading indicator before data retrieval completes", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <DashboardPage />
      </QueryClientProvider>
    );

    expect(screen.getByText(/Loading Dashboard Analytics/i)).toBeInTheDocument();
  });
});
