const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

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

  // Add API key from environment or localStorage
  const apiKey = process.env.NEXT_PUBLIC_API_KEY || localStorage?.getItem('apiKey');
  if (apiKey) {
    headers["x-api-key"] = apiKey;
  }

  const url = `${API_URL}${endpoint.startsWith("/") ? endpoint : "/" + endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
    mode: "cors",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(errorData.error || `API request failed: ${response.statusText}`);
  }

  return response.json();
}
