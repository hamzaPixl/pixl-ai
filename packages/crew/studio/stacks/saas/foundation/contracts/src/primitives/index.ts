import { z } from 'zod';

export const UuidSchema = z.string().uuid();
export type Uuid = z.infer<typeof UuidSchema>;

export const EmailSchema = z.string().email().toLowerCase();
export type Email = z.infer<typeof EmailSchema>;

export const TimestampSchema = z.string().datetime();
export type Timestamp = z.infer<typeof TimestampSchema>;

export const DateOnlySchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
export type DateOnly = z.infer<typeof DateOnlySchema>;

export const NonEmptyStringSchema = z.string().min(1);
export type NonEmptyString = z.infer<typeof NonEmptyStringSchema>;

export const PositiveIntSchema = z.number().int().positive();
export type PositiveInt = z.infer<typeof PositiveIntSchema>;

export const NonNegativeIntSchema = z.number().int().nonnegative();
export type NonNegativeInt = z.infer<typeof NonNegativeIntSchema>;

export const PositiveDecimalSchema = z.number().positive();
export type PositiveDecimal = z.infer<typeof PositiveDecimalSchema>;

export const UrlSchema = z.string().url();
export type Url = z.infer<typeof UrlSchema>;

// Lowercase alphanumeric with dashes
export const SlugSchema = z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/);
export type Slug = z.infer<typeof SlugSchema>;

export const TenantIdSchema = UuidSchema.brand<'TenantId'>();
export type TenantId = z.infer<typeof TenantIdSchema>;

export const UserIdSchema = UuidSchema.brand<'UserId'>();
export type UserId = z.infer<typeof UserIdSchema>;

export const CorrelationIdSchema = UuidSchema.brand<'CorrelationId'>();
export type CorrelationId = z.infer<typeof CorrelationIdSchema>;
