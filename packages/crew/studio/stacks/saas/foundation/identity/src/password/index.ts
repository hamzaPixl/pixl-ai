import * as argon2 from 'argon2';

export interface PasswordHashOptions {
  memoryCost?: number;
  timeCost?: number;
  parallelism?: number;
}

// OWASP recommended defaults
const DEFAULT_OPTIONS: PasswordHashOptions = {
  memoryCost: 65536, // 64 MB
  timeCost: 3,
  parallelism: 4,
};

export async function hashPassword(
  password: string,
  options: PasswordHashOptions = {},
): Promise<string> {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  return argon2.hash(password, {
    type: argon2.argon2id,
    memoryCost: opts.memoryCost,
    timeCost: opts.timeCost,
    parallelism: opts.parallelism,
  });
}

export async function verifyPassword(hash: string, password: string): Promise<boolean> {
  try {
    return await argon2.verify(hash, password);
  } catch {
    return false;
  }
}

export function needsRehash(hash: string, options: PasswordHashOptions = {}): boolean {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  return argon2.needsRehash(hash, {
    memoryCost: opts.memoryCost,
    timeCost: opts.timeCost,
    parallelism: opts.parallelism,
  });
}

export interface PasswordStrengthResult {
  valid: boolean;
  score: number;
  errors: string[];
}

export function validatePasswordStrength(
  password: string,
  options: {
    minLength?: number;
    requireUppercase?: boolean;
    requireLowercase?: boolean;
    requireNumbers?: boolean;
    requireSpecial?: boolean;
  } = {},
): PasswordStrengthResult {
  const {
    minLength = 8,
    requireUppercase = true,
    requireLowercase = true,
    requireNumbers = true,
    requireSpecial = true,
  } = options;

  const errors: string[] = [];
  let score = 0;

  if (password.length < minLength) {
    errors.push(`Password must be at least ${minLength} characters`);
  } else {
    score += Math.min(password.length / 4, 2);
  }

  if (requireUppercase && !/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  } else if (/[A-Z]/.test(password)) {
    score += 1;
  }

  if (requireLowercase && !/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  } else if (/[a-z]/.test(password)) {
    score += 1;
  }

  if (requireNumbers && !/\d/.test(password)) {
    errors.push('Password must contain at least one number');
  } else if (/\d/.test(password)) {
    score += 1;
  }

  if (requireSpecial && !/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) {
    errors.push('Password must contain at least one special character');
  } else if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) {
    score += 1;
  }

  return {
    valid: errors.length === 0,
    score: Math.min(score, 5),
    errors,
  };
}
