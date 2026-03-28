/**
 * Hook for fetching and using version information.
 */

import { useQuery } from "@tanstack/react-query";

export interface VersionInfo {
  version: string;
  build_hash: string;
  python_version: string;
  build_date?: string;
  api_version?: string;
}

/**
 * Fetch version information from the API.
 */
async function fetchVersion(): Promise<VersionInfo> {
  const response = await fetch("/api/version");
  if (!response.ok) {
    throw new Error(`Failed to fetch version: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Hook to get version information.
 */
export function useVersion() {
  return useQuery({
    queryKey: ["version"],
    queryFn: fetchVersion,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false, // Don't retry on failure - version is not critical
  });
}