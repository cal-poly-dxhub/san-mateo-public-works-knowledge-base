import { fetchAuthSession } from 'aws-amplify/auth';

const getApiUrl = () => {
  const url = typeof window !== 'undefined'
    ? (window as any).__RUNTIME_CONFIG__?.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_URL
    : process.env.NEXT_PUBLIC_API_URL;
  
  if (!url) {
    throw new Error("NEXT_PUBLIC_API_URL environment variable is required");
  }
  
  return url.replace(/\/$/, "");
};

export async function apiRequest(
  endpoint: string,
  options: RequestInit = {}
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (options.headers) {
    Object.assign(headers, options.headers);
  }

  // Get Cognito JWT token
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    
    if (token) {
      headers["Authorization"] = token;
    }
  } catch (error) {
    console.error("Failed to get auth session:", error);
    throw new Error("Not authenticated");
  }

  const url = `${getApiUrl()}${endpoint.startsWith("/") ? endpoint : "/" + endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
    mode: "cors",
    credentials: "include",
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw new Error("Session expired");
    }
    const errorData = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(errorData.error || `API request failed: ${response.statusText}`);
  }

  const text = await response.text();
  if (!text) {
    return {};
  }
  return JSON.parse(text);
}
