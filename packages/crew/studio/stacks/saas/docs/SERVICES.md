# Services Guide

This document describes each microservice in SaaS Studio.

## Overview

| Service | Port | Description |
|---------|------|-------------|
| **media-service** | 3001 | File uploads, image processing, storage |
| **form-service** | 3002 | Dynamic forms, validation, submissions |
| **mail-service** | 3003 | Email templates, sending, delivery |
| **pdf-service** | 3004 | PDF generation, templates |

All services follow the same DDD/Onion architecture pattern and share foundation packages.

---

## Media Service

**Port**: 3001

**Purpose**: Handle file uploads, image processing, and storage management.

### Domain Model

```typescript
// MediaFile entity
interface MediaFile {
  id: string;
  tenantId: string;
  name: string;
  originalName: string;
  mimeType: string;
  size: bigint;
  path: string;
  bucket: string;
  url: string | null;
  thumbnailUrl: string | null;
  metadata: Record<string, unknown> | null;
  status: 'pending' | 'processing' | 'ready' | 'failed' | 'archived';
  version: number;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}
```

### API Endpoints

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/media` | List media files | `media:list` |
| GET | `/media/:id` | Get media file | `media:read` |
| POST | `/media` | Create media file | `media:create` |
| PATCH | `/media/:id` | Update media file | `media:update` |
| DELETE | `/media/:id` | Delete media file | `media:delete` |

### Request/Response Examples

**Create Media File**

```bash
POST /media
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-ID: <tenant-id>

{
  "name": "profile-photo.jpg",
  "originalName": "IMG_1234.jpg",
  "mimeType": "image/jpeg",
  "size": 1024000,
  "path": "uploads/2024/01/abc123.jpg",
  "bucket": "media-bucket"
}
```

**Response**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tenantId": "tenant-123",
    "name": "profile-photo.jpg",
    "originalName": "IMG_1234.jpg",
    "mimeType": "image/jpeg",
    "size": "1024000",
    "path": "uploads/2024/01/abc123.jpg",
    "bucket": "media-bucket",
    "url": null,
    "thumbnailUrl": null,
    "metadata": null,
    "status": "pending",
    "version": 0,
    "createdBy": "user-456",
    "createdAt": "2024-01-15T10:30:00.000Z",
    "updatedAt": "2024-01-15T10:30:00.000Z"
  }
}
```

### Features

- **File Status Lifecycle**: pending → processing → ready (or failed)
- **Image Detection**: Automatic detection of image MIME types
- **Thumbnails**: Support for thumbnail URL storage
- **Metadata**: Flexible JSON metadata field
- **Soft Delete**: Files are archived, not permanently deleted

---

## Form Service

**Port**: 3002

**Purpose**: Create dynamic forms with validation and handle submissions.

### Domain Models

```typescript
// Form entity
interface Form {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  schema: FormSchema;
  settings: FormSettings | null;
  status: 'draft' | 'published' | 'archived';
  version: number;
  publishedAt: Date | null;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}

// FormSchema
interface FormSchema {
  fields: FormField[];
  sections?: Array<{
    id: string;
    title: string;
    description?: string;
    fields: string[];
  }>;
}

// FormField
interface FormField {
  id: string;
  name: string;
  label: string;
  type: FieldType;
  placeholder?: string;
  defaultValue?: unknown;
  required: boolean;
  validation?: FieldValidation;
  options?: Array<{ value: string; label: string }>;
  conditionalLogic?: ConditionalLogic;
}

// FieldType
type FieldType =
  | 'text' | 'textarea' | 'number' | 'email' | 'phone'
  | 'date' | 'time' | 'datetime'
  | 'select' | 'multiselect' | 'checkbox' | 'radio'
  | 'file' | 'hidden';

// FormSubmission entity
interface FormSubmission {
  id: string;
  tenantId: string;
  formId: string;
  data: Record<string, unknown>;
  metadata: Record<string, unknown> | null;
  status: 'pending' | 'processed' | 'rejected' | 'spam';
  submittedBy: string | null;
  submittedAt: Date;
  processedAt: Date | null;
}
```

### API Endpoints

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/forms` | List forms | `forms:list` |
| GET | `/forms/:id` | Get form | `forms:read` |
| POST | `/forms` | Create form | `forms:create` |
| PATCH | `/forms/:id` | Update form | `forms:update` |
| DELETE | `/forms/:id` | Delete form | `forms:delete` |
| POST | `/forms/:id/publish` | Publish form | `forms:update` |
| POST | `/forms/:id/submit` | Submit form | (public or `forms:submit`) |
| GET | `/forms/:id/submissions` | List submissions | `forms:read` |

### Request/Response Examples

**Create Form**

```bash
POST /forms
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Contact Form",
  "description": "General contact form",
  "schema": {
    "fields": [
      {
        "id": "name",
        "name": "name",
        "label": "Full Name",
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
        "label": "Email Address",
        "type": "email",
        "required": true
      },
      {
        "id": "message",
        "name": "message",
        "label": "Message",
        "type": "textarea",
        "required": true,
        "validation": {
          "minLength": 10,
          "maxLength": 1000
        }
      }
    ]
  },
  "settings": {
    "submitButtonText": "Send Message",
    "successMessage": "Thank you for your message!",
    "notifyOnSubmission": true,
    "notificationEmails": ["admin@example.com"]
  }
}
```

**Submit Form**

```bash
POST /forms/:id/submit
Content-Type: application/json

{
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "I have a question about your services."
  },
  "metadata": {
    "source": "website",
    "userAgent": "Mozilla/5.0..."
  }
}
```

### Features

- **14 Field Types**: text, textarea, number, email, phone, date, time, datetime, select, multiselect, checkbox, radio, file, hidden
- **Validation Rules**: minLength, maxLength, min, max, pattern
- **Conditional Logic**: Show/hide fields based on other field values
- **Form Sections**: Organize fields into logical sections
- **Publication Workflow**: Forms must be published before accepting submissions
- **Submission Tracking**: Track status (pending, processed, rejected, spam)

---

## Mail Service

**Port**: 3003

**Purpose**: Send emails with templates and queue-based delivery.

### Domain Models

```typescript
// EmailTemplate entity
interface EmailTemplate {
  id: string;
  tenantId: string;
  name: string;
  subject: string;
  htmlBody: string;
  textBody: string | null;
  variables: TemplateVariable[] | null;
  category: string | null;
  status: 'active' | 'inactive' | 'archived';
  version: number;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}

// TemplateVariable
interface TemplateVariable {
  name: string;
  description?: string;
  required: boolean;
  defaultValue?: string;
}

// Email entity
interface Email {
  id: string;
  tenantId: string;
  templateId: string | null;
  fromAddress: string;
  fromName: string | null;
  toAddresses: string[];
  ccAddresses: string[] | null;
  bccAddresses: string[] | null;
  subject: string;
  htmlBody: string | null;
  textBody: string | null;
  attachments: EmailAttachment[] | null;
  metadata: Record<string, unknown> | null;
  status: 'pending' | 'queued' | 'sending' | 'sent' | 'failed' | 'bounced';
  priority: number;
  scheduledFor: Date | null;
  sentAt: Date | null;
  failedAt: Date | null;
  failureReason: string | null;
  retryCount: number;
  maxRetries: number;
  createdBy: string | null;
  createdAt: Date;
}
```

### API Endpoints

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/mail/templates` | List templates | `mail-templates:list` |
| GET | `/mail/templates/:id` | Get template | `mail-templates:read` |
| POST | `/mail/templates` | Create template | `mail-templates:create` |
| PATCH | `/mail/templates/:id` | Update template | `mail-templates:update` |
| DELETE | `/mail/templates/:id` | Delete template | `mail-templates:delete` |
| GET | `/mail/emails` | List emails | `mail:list` |
| GET | `/mail/emails/:id` | Get email | `mail:read` |
| POST | `/mail/send` | Send email | `mail:send` |

### Request/Response Examples

**Create Template**

```bash
POST /mail/templates
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "welcome-email",
  "subject": "Welcome to {{company}}!",
  "htmlBody": "<h1>Welcome, {{firstName}}!</h1><p>Thank you for joining {{company}}.</p>",
  "textBody": "Welcome, {{firstName}}! Thank you for joining {{company}}.",
  "variables": [
    { "name": "firstName", "required": true },
    { "name": "company", "required": true, "defaultValue": "Our Platform" }
  ],
  "category": "onboarding"
}
```

**Send Email with Template**

```bash
POST /mail/send
Content-Type: application/json
Authorization: Bearer <token>

{
  "templateId": "template-123",
  "fromAddress": "noreply@example.com",
  "fromName": "Example App",
  "toAddresses": ["user@example.com"],
  "data": {
    "firstName": "John",
    "company": "Example Corp"
  },
  "priority": 1
}
```

**Send Email without Template**

```bash
POST /mail/send
Content-Type: application/json
Authorization: Bearer <token>

{
  "fromAddress": "noreply@example.com",
  "toAddresses": ["user@example.com"],
  "subject": "Important Update",
  "htmlBody": "<p>Hello! This is an important update.</p>",
  "textBody": "Hello! This is an important update."
}
```

### Features

- **Template Variables**: `{{variable}}` syntax for dynamic content
- **Multi-Recipient**: Support for to, cc, bcc addresses
- **Attachments**: Send files with emails
- **Priority Queue**: Higher priority emails sent first
- **Scheduling**: Schedule emails for future delivery
- **Retry Logic**: Automatic retries on failure (max 3 by default)
- **Status Tracking**: pending → queued → sending → sent (or failed/bounced)

---

## PDF Service

**Port**: 3004

**Purpose**: Generate PDFs from HTML templates.

### Domain Models

```typescript
// PdfTemplate entity
interface PdfTemplate {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  htmlContent: string;
  cssStyles: string | null;
  variables: TemplateVariable[] | null;
  pageSize: 'A4' | 'A3' | 'Letter' | 'Legal' | 'Tabloid';
  orientation: 'portrait' | 'landscape';
  margins: PageMargins | null;
  header: string | null;
  footer: string | null;
  status: 'active' | 'inactive' | 'archived';
  version: number;
  createdBy: string | null;
  createdAt: Date;
  updatedAt: Date;
}

// PageMargins
interface PageMargins {
  top: string;
  right: string;
  bottom: string;
  left: string;
}

// PdfDocument entity
interface PdfDocument {
  id: string;
  tenantId: string;
  templateId: string | null;
  name: string;
  data: Record<string, unknown> | null;
  filePath: string | null;
  fileSize: bigint | null;
  pageCount: number | null;
  status: 'pending' | 'generating' | 'ready' | 'failed' | 'expired';
  generatedAt: Date | null;
  expiresAt: Date | null;
  metadata: Record<string, unknown> | null;
  createdBy: string | null;
  createdAt: Date;
}
```

### API Endpoints

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| GET | `/pdf/templates` | List templates | `pdf-templates:list` |
| GET | `/pdf/templates/:id` | Get template | `pdf-templates:read` |
| POST | `/pdf/templates` | Create template | `pdf-templates:create` |
| PATCH | `/pdf/templates/:id` | Update template | `pdf-templates:update` |
| DELETE | `/pdf/templates/:id` | Delete template | `pdf-templates:delete` |
| GET | `/pdf/documents` | List documents | `pdf:list` |
| GET | `/pdf/documents/:id` | Get document | `pdf:read` |
| POST | `/pdf/generate` | Generate PDF | `pdf:generate` |
| DELETE | `/pdf/documents/:id` | Delete document | `pdf:delete` |

### Request/Response Examples

**Create Template**

```bash
POST /pdf/templates
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "invoice-template",
  "description": "Standard invoice template",
  "htmlContent": "<div class=\"invoice\"><h1>Invoice #{{invoiceNumber}}</h1><p>To: {{customerName}}</p><table>{{#items}}<tr><td>{{name}}</td><td>{{price}}</td></tr>{{/items}}</table><p><strong>Total: {{total}}</strong></p></div>",
  "cssStyles": ".invoice { font-family: Arial; } table { width: 100%; }",
  "variables": [
    { "name": "invoiceNumber", "required": true },
    { "name": "customerName", "required": true },
    { "name": "items", "required": true },
    { "name": "total", "required": true }
  ],
  "pageSize": "A4",
  "orientation": "portrait",
  "margins": {
    "top": "20mm",
    "right": "15mm",
    "bottom": "20mm",
    "left": "15mm"
  },
  "footer": "<div style=\"text-align: center;\">Page {{page}} of {{pages}}</div>"
}
```

**Generate PDF**

```bash
POST /pdf/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "templateId": "template-123",
  "name": "Invoice-2024-001.pdf",
  "data": {
    "invoiceNumber": "2024-001",
    "customerName": "Acme Corp",
    "items": [
      { "name": "Widget A", "price": "$100" },
      { "name": "Widget B", "price": "$200" }
    ],
    "total": "$300"
  },
  "expiresAt": "2024-02-15T00:00:00Z"
}
```

**Response (202 Accepted)**

```json
{
  "data": {
    "id": "doc-123",
    "tenantId": "tenant-456",
    "templateId": "template-123",
    "name": "Invoice-2024-001.pdf",
    "status": "pending",
    "createdAt": "2024-01-15T10:30:00.000Z"
  }
}
```

### Features

- **HTML to PDF**: Convert HTML/CSS to PDF using Puppeteer
- **Template Variables**: `{{variable}}` syntax for dynamic content
- **Page Sizes**: A4, A3, Letter, Legal, Tabloid
- **Orientation**: Portrait or Landscape
- **Margins**: Configurable page margins
- **Headers/Footers**: Custom header and footer content
- **Page Numbers**: `{{page}}` and `{{pages}}` variables in headers/footers
- **Expiration**: Set document expiration dates
- **Async Generation**: Returns 202 Accepted, generates in background

---

## Common Patterns

### Service Bootstrap

All services follow this pattern in `main.ts`:

```typescript
async function bootstrap(): Promise<void> {
  // 1. Create Prisma client with tenant scoping
  const prisma = new PrismaClient().$extends(
    createTenantScopeExtension({
      excludedModels: ['Tenant', 'AuditLog', 'Outbox'],
    }),
  ) as unknown as PrismaClient;

  // 2. Register permissions
  permissionRegistry.registerCrud('resource');

  // 3. Register roles
  roleRegistry.register({
    name: 'admin',
    permissions: crudPermissions('resource'),
  });

  // 4. Create API factory
  const { app, logger, start } = await createApiFactory({
    name: 'service-name',
    version: '0.1.0',
    port: 3001,
    jwt: { secret: process.env['JWT_SECRET'] },
    swagger: { title: 'Service API' },
    healthChecks: {
      readyChecks: {
        database: async () => {
          await prisma.$queryRaw`SELECT 1`;
          return true;
        },
      },
    },
  });

  // 5. Create dependencies
  const unitOfWork = createUnitOfWork(prisma);
  const repository = new PrismaRepository(prisma);

  // 6. Register routes
  registerRoutes(app, { repository, unitOfWork });

  // 7. Graceful shutdown
  app.addHook('onClose', async () => {
    await prisma.$disconnect();
  });

  // 8. Start server
  await start();
}
```

### Route Handler Pattern

```typescript
fastify.post<{ Body: CreateRequest }>(
  '/resource',
  {
    preHandler: [permissionGuard(permission('resource', 'create'))],
  },
  async (request, reply) => {
    requireAuth(request);

    return withRequestContext(request, async (ctx) => {
      const body = CreateRequestSchema.parse(request.body);

      const entity = Entity.create({
        tenantId: ctx.tenantId,
        ...body,
        createdBy: ctx.actor?.id,
      });

      const saved = await unitOfWork.execute(async (tx) => {
        const result = await repository.save(entity, tx);
        return {
          result,
          auditEntries: [],
          outboxEntries: [],
        };
      });

      reply.status(201);
      return { data: toResponse(saved) };
    });
  },
);
```

### Database Schema Pattern

Each service includes these shared tables:

```prisma
model AuditLog {
  id            String   @id @default(uuid())
  tenantId      String   @map("tenant_id")
  aggregateType String   @map("aggregate_type")
  aggregateId   String   @map("aggregate_id")
  action        String
  actorType     String   @map("actor_type")
  actorId       String?  @map("actor_id")
  before        Json?
  after         Json?
  metadata      Json?
  correlationId String?  @map("correlation_id")
  occurredAt    DateTime @default(now()) @map("occurred_at")

  @@map("audit_log")
}

model Outbox {
  id            String    @id @default(uuid())
  tenantId      String    @map("tenant_id")
  eventType     String    @map("event_type")
  aggregateType String    @map("aggregate_type")
  aggregateId   String    @map("aggregate_id")
  payload       Json
  metadata      Json?
  status        String    @default("pending")
  retryCount    Int       @default(0) @map("retry_count")
  maxRetries    Int       @default(3) @map("max_retries")
  lastError     String?   @map("last_error")
  correlationId String?   @map("correlation_id")
  scheduledFor  DateTime? @map("scheduled_for")
  processedAt   DateTime? @map("processed_at")
  createdAt     DateTime  @default(now()) @map("created_at")

  @@map("outbox")
}
```
