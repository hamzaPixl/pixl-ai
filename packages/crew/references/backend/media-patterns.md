# Media Upload Patterns

## Presigned URL Flow

```
Client → API (request upload) → S3 (generate presigned URL) → Client (direct upload to S3)
                                                              → API (confirm upload, save metadata)
```

1. Client requests upload with filename, MIME type, and size
2. API validates constraints (size limit, allowed types)
3. API generates presigned URL via S3 SDK (valid for N seconds)
4. Client uploads directly to S3 using the presigned URL
5. Client confirms upload → API saves file metadata to DB

## File Key Strategy

Format: `{tenantId}/{year}/{month}/{uuid}-{sanitized-filename}`

- Tenant isolation at the storage level
- Date-based partitioning for lifecycle management
- UUID prefix prevents collisions
- Sanitized filename preserves human readability

## Image Processing

For image-heavy apps, add a processing pipeline:

1. Original uploaded to `/originals/{key}`
2. Lambda/worker generates variants: thumbnail, medium, large
3. Variants stored at `/variants/{key}/{size}`
4. CDN serves variants with cache headers

## CDN Integration

- Set `cdnBaseUrl` in MediaConfig to serve via CDN
- Use immutable cache headers (files are never overwritten)
- Configure CDN to pull from S3 bucket as origin

## Foundation Package

The `@saas-studio/media` package provides:

- `validateUpload()` — size/MIME validation
- `generateFileKey()` — unique key generation
- `createPresignedUpload()` — full presigned URL flow
- `StorageAdapter` — interface for S3/R2/MinIO/Supabase Storage
