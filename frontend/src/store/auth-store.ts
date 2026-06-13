import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface Role {
  id: string;
  name: string;
  description: string | null;
}

export interface User {
  id: string;
  email: string;
  username: string;
  profile_image_url: string | null;
  is_active: boolean;
  is_verified: boolean;
  roles: Role[];
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: User) => void;
  clearAuth: () => void;
  hasRole: (roleName: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setUser: (user) => set({ user }),
      clearAuth: () => set({ accessToken: null, refreshToken: null, user: null }),
      hasRole: (roleName) => {
        const user = get().user;
        if (!user) return false;
        return user.roles.some((r) => r.name.toLowerCase() === roleName.toLowerCase());
      },
    }),
    {
      name: "wildfire-auth-storage",
    }
  )
);
