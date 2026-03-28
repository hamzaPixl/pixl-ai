import type { ArtifactMetadata } from "@/types/api";
import { get, projectPath } from "./core";

export const artifacts = {
  list: (params?: {
    limit?: number;
    offset?: number;
    session_id?: string;
    artifact_type?: string;
  }): Promise<ArtifactMetadata[]> => {
    if (params?.session_id) {
      const { session_id, ...rest } = params;
      return get(projectPath(`/sessions/${session_id}/artifacts`), rest);
    }
    return get(projectPath("/artifacts"), params);
  },

  search: (
    query: string,
    params?: { limit?: number; artifact_type?: string },
  ): Promise<ArtifactMetadata[]> =>
    get(projectPath("/artifacts/search"), { q: query, ...params }),

  get: (id: string): Promise<ArtifactMetadata> =>
    get(projectPath(`/artifacts/${id}`)),

  getContent: (
    id: string,
  ): Promise<{
    id: string;
    content: string | null;
    content_hash: string | null;
    storage_mode?: string | null;
    chunk_count?: number | null;
    size_bytes?: number | null;
    uncompressed_size_bytes?: number | null;
    compressed_size_bytes?: number | null;
  }> => get(projectPath(`/artifacts/${id}/content`)),

  getVersions: (
    path: string,
    sessionId?: string,
  ): Promise<ArtifactMetadata[]> =>
    get(projectPath("/artifacts/by-path/versions"), {
      path,
      session_id: sessionId,
    }),
};
