export type TemplateValue = string | number | boolean | Date | null | undefined;

export interface TemplateVariables {
  [key: string]: TemplateValue | TemplateVariables | TemplateValue[];
}

export interface NotificationTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  htmlBody?: string;
  variables: string[];
}

export interface ITemplateRenderer {
  render(template: string, variables: TemplateVariables): string;
}

export class SimpleTemplateRenderer implements ITemplateRenderer {
  render(template: string, variables: TemplateVariables): string {
    let result = template;

    // Replace {{variable}} patterns
    const pattern = /\{\{([^}]+)\}\}/g;
    result = result.replace(pattern, (_, key: string) => {
      const value = this.getValue(variables, key.trim());
      return value !== undefined && value !== null ? String(value) : '';
    });

    return result;
  }

  private getValue(obj: TemplateVariables, path: string): TemplateValue | undefined {
    const parts = path.split('.');
    let current: TemplateVariables | TemplateValue | TemplateValue[] = obj;

    for (const part of parts) {
      if (current === null || current === undefined) {
        return undefined;
      }
      if (typeof current === 'object' && !Array.isArray(current) && !(current instanceof Date)) {
        current = (current as TemplateVariables)[part];
      } else {
        return undefined;
      }
    }

    if (Array.isArray(current) || (typeof current === 'object' && !(current instanceof Date))) {
      return undefined;
    }

    return current;
  }
}

export class TemplateRegistry {
  private templates = new Map<string, NotificationTemplate>();
  private renderer: ITemplateRenderer;

  constructor(renderer?: ITemplateRenderer) {
    this.renderer = renderer ?? new SimpleTemplateRenderer();
  }

  register(template: NotificationTemplate): void {
    this.templates.set(template.id, template);
  }

  get(id: string): NotificationTemplate | undefined {
    return this.templates.get(id);
  }

  render(
    templateId: string,
    variables: TemplateVariables,
  ): { subject: string; body: string; htmlBody?: string } | null {
    const template = this.templates.get(templateId);
    if (!template) {
      return null;
    }

    return {
      subject: this.renderer.render(template.subject, variables),
      body: this.renderer.render(template.body, variables),
      htmlBody: template.htmlBody ? this.renderer.render(template.htmlBody, variables) : undefined,
    };
  }

  list(): NotificationTemplate[] {
    return Array.from(this.templates.values());
  }
}

export const CommonTemplates = {
  WELCOME: {
    id: 'welcome',
    name: 'Welcome Email',
    subject: 'Welcome to {{appName}}, {{user.name}}!',
    body: "Hi {{user.name}},\n\nWelcome to {{appName}}! We're excited to have you on board.\n\nBest regards,\nThe {{appName}} Team",
    variables: ['appName', 'user.name'],
  },
  PASSWORD_RESET: {
    id: 'password-reset',
    name: 'Password Reset',
    subject: 'Reset your {{appName}} password',
    body: "Hi {{user.name}},\n\nClick the link below to reset your password:\n{{resetLink}}\n\nThis link expires in {{expiresIn}} hours.\n\nIf you didn't request this, please ignore this email.",
    variables: ['appName', 'user.name', 'resetLink', 'expiresIn'],
  },
  EMAIL_VERIFICATION: {
    id: 'email-verification',
    name: 'Email Verification',
    subject: 'Verify your email for {{appName}}',
    body: 'Hi {{user.name}},\n\nPlease verify your email by clicking:\n{{verifyLink}}\n\nThis link expires in {{expiresIn}} hours.',
    variables: ['appName', 'user.name', 'verifyLink', 'expiresIn'],
  },
  INVOICE: {
    id: 'invoice',
    name: 'Invoice Notification',
    subject: 'Invoice #{{invoice.number}} from {{company.name}}',
    body: 'Hi {{recipient.name}},\n\nYou have a new invoice #{{invoice.number}} for {{invoice.amount}} {{invoice.currency}}.\n\nDue date: {{invoice.dueDate}}\n\nView invoice: {{invoiceLink}}',
    variables: [
      'recipient.name',
      'invoice.number',
      'invoice.amount',
      'invoice.currency',
      'invoice.dueDate',
      'invoiceLink',
      'company.name',
    ],
  },
} as const;
