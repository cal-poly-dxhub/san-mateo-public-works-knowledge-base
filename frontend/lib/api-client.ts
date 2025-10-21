const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

export async function apiRequest(
  endpoint: string,
  options: RequestInit = {},
  apiKey?: string,
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (options.headers) {
    Object.assign(headers, options.headers);
  }

  if (apiKey) {
    headers["x-api-key"] = apiKey;
  }

  const url = `${API_URL}${endpoint.startsWith("/") ? endpoint : "/" + endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
    mode: "cors",
  });

  return response;
}
