/**
 * Media upload foundation package.
 *
 * Provides presigned URL generation, file metadata tracking, and upload validation.
 * Works with any S3-compatible storage (AWS S3, MinIO, Cloudflare R2, Supabase Storage).
 */

export interface MediaConfig {
  bucket: string;
  region: string;
  maxFileSizeBytes: number;
  allowedMimeTypes: string[];
  urlExpirationSeconds: number;
  cdnBaseUrl?: string;
}

export const DEFAULT_MEDIA_CONFIG: Partial<MediaConfig> = {
  maxFileSizeBytes: 10 * 1024 * 1024, // 10MB
  allowedMimeTypes: [
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
  ],
  urlExpirationSeconds: 3600,
};

export interface PresignedUploadRequest {
  filename: string;
  mimeType: string;
  fileSizeBytes: number;
  tenantId: string;
  uploadedBy: string;
}

export interface PresignedUploadResponse {
  uploadUrl: string;
  fileKey: string;
  expiresAt: string;
  publicUrl: string;
}

export interface FileMetadata {
  id: string;
  tenantId: string;
  fileKey: string;
  filename: string;
  mimeType: string;
  fileSizeBytes: number;
  publicUrl: string;
  uploadedBy: string;
  uploadedAt: Date;
}

/**
 * Validate upload request against config constraints.
 */
export function validateUpload(
  request: PresignedUploadRequest,
  config: MediaConfig,
): { valid: boolean; error?: string } {
  if (request.fileSizeBytes > config.maxFileSizeBytes) {
    return {
      valid: false,
      error: `File size ${request.fileSizeBytes} exceeds maximum ${config.maxFileSizeBytes} bytes`,
    };
  }

  if (!config.allowedMimeTypes.includes(request.mimeType)) {
    return {
      valid: false,
      error: `MIME type ${request.mimeType} not allowed. Allowed: ${config.allowedMimeTypes.join(", ")}`,
    };
  }

  return { valid: true };
}

/**
 * Generate a unique file key for storage.
 *
 * Format: `{tenantId}/{year}/{month}/{uuid}-{sanitized-filename}`
 */
export function generateFileKey(tenantId: string, filename: string): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const uuid = crypto.randomUUID();
  const sanitized = filename
    .toLowerCase()
    .replace(/[^a-z0-9.\-_]/g, "-")
    .replace(/-+/g, "-");

  return `${tenantId}/${year}/${month}/${uuid}-${sanitized}`;
}

/**
 * Build the public URL for a file.
 */
export function buildPublicUrl(fileKey: string, config: MediaConfig): string {
  if (config.cdnBaseUrl) {
    return `${config.cdnBaseUrl}/${fileKey}`;
  }
  return `https://${config.bucket}.s3.${config.region}.amazonaws.com/${fileKey}`;
}

/**
 * S3 client adapter interface — implement for your storage provider.
 */
export interface StorageAdapter {
  generatePresignedUploadUrl(
    bucket: string,
    key: string,
    mimeType: string,
    expirationSeconds: number,
  ): Promise<string>;

  deleteObject(bucket: string, key: string): Promise<void>;
}

/**
 * Create a presigned upload URL using the storage adapter.
 */
export async function createPresignedUpload(
  request: PresignedUploadRequest,
  config: MediaConfig,
  storage: StorageAdapter,
): Promise<PresignedUploadResponse> {
  const validation = validateUpload(request, config);
  if (!validation.valid) {
    throw new Error(validation.error);
  }

  const fileKey = generateFileKey(request.tenantId, request.filename);
  const uploadUrl = await storage.generatePresignedUploadUrl(
    config.bucket,
    fileKey,
    request.mimeType,
    config.urlExpirationSeconds,
  );

  const expiresAt = new Date(
    Date.now() + config.urlExpirationSeconds * 1000,
  ).toISOString();

  return {
    uploadUrl,
    fileKey,
    expiresAt,
    publicUrl: buildPublicUrl(fileKey, config),
  };
}
