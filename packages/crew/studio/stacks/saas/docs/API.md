# API Reference

This document provides the complete API reference for SaaS Studio services.

## Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

### Token Structure

```json
{
  "sub": "user-id",
  "tenantId": "tenant-id",
  "email": "user@example.com",
  "roles": ["admin"],
  "permissions": ["items:create", "items:read"],
  "iat": 1705312200,
  "exp": 1705315800
}
```

## Headers

### Required Headers

| Header | Description | Example |
|--------|-------------|---------|
| `Authorization` | JWT Bearer token | `Bearer eyJhbG...` |
| `Content-Type` | Request content type | `application/json` |

### Optional Headers

| Header | Description | Example |
|--------|-------------|---------|
| `X-Tenant-ID` | Override tenant (if not in JWT) | `tenant-123` |
| `X-Correlation-ID` | Request correlation ID | `req-456` |
| `X-Request-ID` | Unique request identifier | `abc-789` |

## Response Format

### Success Response

```json
{
  "data": {
    "id": "...",
    "...": "..."
  }
}
```

### List Response

```json
{
  "data": [
    { "id": "...", "...": "..." },
    { "id": "...", "...": "..." }
  ],
  "pagination": {
    "total": 100,
    "limit": 10,
    "offset": 0,
    "hasMore": true
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": [],
    "correlationId": "req-123"
  }
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `BAD_REQUEST` | 400 | Invalid request format |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `UNPROCESSABLE_ENTITY` | 422 | Validation error |
| `INTERNAL_SERVER_ERROR` | 500 | Server error |

---

## Health Endpoints

All services expose health check endpoints:

### Liveness Probe

```
GET /health
```

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Readiness Probe

```
GET /ready
```

**Response:**

```json
{
  "status": "ok",
  "checks": {
    "database": { "status": "ok" }
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

## Common Query Parameters

### Pagination

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 100 | Items per page (1-100) |
| `offset` | integer | 0 | Skip items |

### Filtering

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status |

---

## Media Service API

**Base URL:** `http://localhost:3001`

### List Media Files

```
GET /media
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status |
| `limit` | integer | Items per page |
| `offset` | integer | Skip items |

**Response:** `200 OK`

```json
{
  "data": [
    {
      "id": "550e8400-...",
      "tenantId": "tenant-123",
      "name": "photo.jpg",
      "originalName": "IMG_1234.jpg",
      "mimeType": "image/jpeg",
      "size": "1024000",
      "path": "uploads/photo.jpg",
      "bucket": "media",
      "url": "https://cdn.example.com/photo.jpg",
      "thumbnailUrl": "https://cdn.example.com/photo-thumb.jpg",
      "status": "ready",
      "version": 1,
      "createdAt": "2024-01-15T10:30:00.000Z",
      "updatedAt": "2024-01-15T10:30:00.000Z"
    }
  ]
}
```

### Get Media File

```
GET /media/:id
```

**Response:** `200 OK`

### Create Media File

```
POST /media
```

**Request Body:**

```json
{
  "name": "photo.jpg",
  "originalName": "IMG_1234.jpg",
  "mimeType": "image/jpeg",
  "size": 1024000,
  "path": "uploads/photo.jpg",
  "bucket": "media"
}
```

**Response:** `201 Created`

### Update Media File

```
PATCH /media/:id
```

**Request Body:**

```json
{
  "name": "renamed-photo.jpg",
  "metadata": { "tags": ["profile"] }
}
```

**Response:** `200 OK`

### Delete Media File

```
DELETE /media/:id
```

**Response:** `204 No Content`

---

## Form Service API

**Base URL:** `http://localhost:3002`

### List Forms

```
GET /forms
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `draft`, `published`, `archived` |

### Get Form

```
GET /forms/:id
```

### Create Form

```
POST /forms
```

**Request Body:**

```json
{
  "name": "Contact Form",
  "description": "Contact us form",
  "schema": {
    "fields": [
      {
        "id": "name",
        "name": "name",
        "label": "Your Name",
        "type": "text",
        "required": true,
        "validation": {
          "minLength": 2,
          "maxLength": 100
        }
      },
      {
        "id": "email",
        "name": "email",
        "label": "Email",
        "type": "email",
        "required": true
      }
    ]
  },
  "settings": {
    "submitButtonText": "Submit",
    "successMessage": "Thank you!"
  }
}
```

### Update Form

```
PATCH /forms/:id
```

### Publish Form

```
POST /forms/:id/publish
```

**Response:** `200 OK`

### Delete Form

```
DELETE /forms/:id
```

### Submit Form

```
POST /forms/:id/submit
```

**Request Body:**

```json
{
  "data": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "metadata": {
    "source": "website"
  }
}
```

**Response:** `201 Created`

### List Form Submissions

```
GET /forms/:id/submissions
```

---

## Mail Service API

**Base URL:** `http://localhost:3003`

### List Email Templates

```
GET /mail/templates
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Filter by category |
| `status` | string | `active`, `inactive`, `archived` |

### Get Email Template

```
GET /mail/templates/:id
```

### Create Email Template

```
POST /mail/templates
```

**Request Body:**

```json
{
  "name": "welcome",
  "subject": "Welcome, {{name}}!",
  "htmlBody": "<h1>Welcome, {{name}}!</h1><p>Thank you for joining.</p>",
  "textBody": "Welcome, {{name}}! Thank you for joining.",
  "variables": [
    { "name": "name", "required": true }
  ],
  "category": "onboarding"
}
```

### Update Email Template

```
PATCH /mail/templates/:id
```

### Delete Email Template

```
DELETE /mail/templates/:id
```

### List Emails

```
GET /mail/emails
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `pending`, `queued`, `sending`, `sent`, `failed`, `bounced` |

### Get Email

```
GET /mail/emails/:id
```

### Send Email

```
POST /mail/send
```

**Request Body (with template):**

```json
{
  "templateId": "template-123",
  "fromAddress": "noreply@example.com",
  "fromName": "Example App",
  "toAddresses": ["user@example.com"],
  "data": {
    "name": "John"
  },
  "priority": 1,
  "scheduledFor": "2024-01-16T09:00:00.000Z"
}
```

**Request Body (without template):**

```json
{
  "fromAddress": "noreply@example.com",
  "toAddresses": ["user@example.com"],
  "subject": "Hello!",
  "htmlBody": "<p>Hello, World!</p>",
  "textBody": "Hello, World!"
}
```

---

## PDF Service API

**Base URL:** `http://localhost:3004`

### List PDF Templates

```
GET /pdf/templates
```

### Get PDF Template

```
GET /pdf/templates/:id
```

### Create PDF Template

```
POST /pdf/templates
```

**Request Body:**

```json
{
  "name": "invoice",
  "description": "Invoice template",
  "htmlContent": "<h1>Invoice #{{number}}</h1><p>Amount: {{amount}}</p>",
  "cssStyles": "h1 { color: #333; }",
  "variables": [
    { "name": "number", "required": true },
    { "name": "amount", "required": true }
  ],
  "pageSize": "A4",
  "orientation": "portrait",
  "margins": {
    "top": "20mm",
    "right": "15mm",
    "bottom": "20mm",
    "left": "15mm"
  },
  "footer": "<div>Page {{page}} of {{pages}}</div>"
}
```

### Update PDF Template

```
PATCH /pdf/templates/:id
```

### Delete PDF Template

```
DELETE /pdf/templates/:id
```

### List PDF Documents

```
GET /pdf/documents
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `templateId` | string | Filter by template |
| `status` | string | `pending`, `generating`, `ready`, `failed`, `expired` |

### Get PDF Document

```
GET /pdf/documents/:id
```

### Generate PDF

```
POST /pdf/generate
```

**Request Body:**

```json
{
  "templateId": "template-123",
  "name": "Invoice-001.pdf",
  "data": {
    "number": "INV-001",
    "amount": "$500.00"
  },
  "expiresAt": "2024-02-15T00:00:00.000Z"
}
```

**Response:** `202 Accepted`

```json
{
  "data": {
    "id": "doc-123",
    "name": "Invoice-001.pdf",
    "status": "pending",
    "createdAt": "2024-01-15T10:30:00.000Z"
  }
}
```

### Delete PDF Document

```
DELETE /pdf/documents/:id
```

---

## Swagger Documentation

Each service exposes Swagger UI at `/docs`:

- Media Service: http://localhost:3001/docs
- Form Service: http://localhost:3002/docs
- Mail Service: http://localhost:3003/docs
- PDF Service: http://localhost:3004/docs
