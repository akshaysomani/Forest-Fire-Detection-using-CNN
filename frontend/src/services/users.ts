export interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  created_at: string;
}

export interface UsersResponse {
  success: boolean;
  count: number;
  data: User[];
}

export interface UserResponse {
  success: boolean;
  data: User;
}

const USERS_API_BASE = "/api/users";

/**
 * Service for interacting with the /api/users endpoint
 * backed by the Node.js/Express + PostgreSQL server.
 *
 * NOTE: This calls /api/users directly (proxied to port 5000)
 * rather than /api/v1/users (which goes to the Python backend).
 */
export const usersService = {
  /** Fetch all users from the PostgreSQL database */
  async getAll(): Promise<UsersResponse> {
    const res = await fetch(USERS_API_BASE);
    if (!res.ok) throw new Error("Failed to fetch users");
    return res.json();
  },

  /** Fetch a single user by ID */
  async getById(id: number): Promise<UserResponse> {
    const res = await fetch(`${USERS_API_BASE}/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch user ${id}`);
    return res.json();
  },
};

