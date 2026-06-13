import { apiRequest } from "@/lib/api-client";
import { User } from "@/store/auth-store";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
}

export interface Session {
  id: string;
  user_id: string;
  refresh_token_id: string;
  ip_address: string | null;
  user_agent: string | null;
  is_active: boolean;
  last_activity_at: string;
  created_at: string;
}

export const authService = {
  async register(data: any): Promise<User> {
    return apiRequest<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async login(formData: URLSearchParams): Promise<LoginResponse> {
    return apiRequest<LoginResponse>("/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
    });
  },

  async logout(refreshToken: string): Promise<void> {
    return apiRequest<void>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  async getProfile(): Promise<User> {
    return apiRequest<User>("/auth/profile");
  },

  async updateProfile(data: any): Promise<User> {
    return apiRequest<User>("/auth/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async changePassword(data: any): Promise<void> {
    return apiRequest<void>("/auth/change-password", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async getSessions(): Promise<Session[]> {
    return apiRequest<Session[]>("/auth/sessions");
  },

  async revokeSession(sessionId: string): Promise<void> {
    return apiRequest<void>(`/auth/sessions/${sessionId}`, {
      method: "DELETE",
    });
  },

  async forgotPassword(email: string): Promise<{ message: string }> {
    return apiRequest<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },

  async resetPassword(data: any): Promise<void> {
    return apiRequest<void>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async verifyEmail(token: string): Promise<void> {
    return apiRequest<void>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  },
};
