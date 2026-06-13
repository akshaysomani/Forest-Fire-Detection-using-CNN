import { useAuthStore } from "@/store/auth-store";

const BASE_URL = "/api/v1";

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
}

class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

export async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers, ...rest } = options;
  const store = useAuthStore.getState();

  let url = `${BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val));
      }
    });
    url += `?${searchParams.toString()}`;
  }

  const defaultHeaders: Record<string, string> = {};
  if (!(options.body instanceof FormData)) {
    defaultHeaders["Content-Type"] = "application/json";
  }

  if (store.accessToken) {
    defaultHeaders["Authorization"] = `Bearer ${store.accessToken}`;
  }

  const config: RequestInit = {
    ...rest,
    headers: {
      ...defaultHeaders,
      ...headers,
    },
  };

  try {
    const response = await fetch(url, config);

    if (response.status === 401 && store.refreshToken && !isRefreshing && endpoint !== "/auth/refresh") {
      isRefreshing = true;
      try {
        const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: store.refreshToken }),
        });

        if (refreshRes.ok) {
          const newTokens = await refreshRes.json();
          store.setTokens(newTokens.access_token, newTokens.refresh_token);
          isRefreshing = false;
          onRefreshed(newTokens.access_token);
          
          // Retry original request with new token
          if (config.headers) {
            (config.headers as Record<string, string>)["Authorization"] = `Bearer ${newTokens.access_token}`;
          }
          const retryRes = await fetch(url, config);
          if (!retryRes.ok) {
            const errData = await retryRes.json().catch(() => ({}));
            throw new ApiError(errData.detail || "Request failed after refresh", retryRes.status, errData);
          }
          return (await retryRes.json()) as T;
        } else {
          isRefreshing = false;
          store.clearAuth();
          throw new ApiError("Session expired", 401);
        }
      } catch (err) {
        isRefreshing = false;
        store.clearAuth();
        throw err;
      }
    }

    if (response.status === 401 && isRefreshing && endpoint !== "/auth/refresh") {
      return new Promise((resolve, reject) => {
        subscribeTokenRefresh(async (token) => {
          if (config.headers) {
            (config.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
          }
          try {
            const retryRes = await fetch(url, config);
            if (!retryRes.ok) {
              const errData = await retryRes.json().catch(() => ({}));
              reject(new ApiError(errData.detail || "Retry failed", retryRes.status, errData));
            } else {
              resolve((await retryRes.json()) as T);
            }
          } catch (e) {
            reject(e);
          }
        });
      });
    }

    if (response.status === 204) {
      return {} as T;
    }

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new ApiError(errData.detail || "API request failed", response.status, errData);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError((error as Error).message || "Network error", 500);
  }
}
