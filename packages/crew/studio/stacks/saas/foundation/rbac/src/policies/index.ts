import { AuthorizationError } from '@saas-studio/contracts';
import type { Actor } from '@saas-studio/identity';
import { getActor } from '@saas-studio/identity';

export interface PolicyResult {
  allowed: boolean;
  reason?: string;
}

export interface Policy<TResource = unknown> {
  can(actor: Actor, action: string, resource: TResource): Promise<PolicyResult>;
  filter?(actor: Actor, action: string, resources: TResource[]): Promise<TResource[]>;
}

export class PolicyEvaluator {
  private policies = new Map<string, Policy>();

  register<TResource>(resourceType: string, policy: Policy<TResource>): void {
    this.policies.set(resourceType, policy as Policy);
  }

  get<TResource>(resourceType: string): Policy<TResource> | undefined {
    return this.policies.get(resourceType) as Policy<TResource> | undefined;
  }

  async can<TResource>(
    resourceType: string,
    action: string,
    resource: TResource,
    actor?: Actor,
  ): Promise<PolicyResult> {
    const policy = this.policies.get(resourceType);
    if (!policy) {
      return { allowed: true };
    }

    const resolvedActor = actor ?? getActor();
    if (!resolvedActor) {
      return { allowed: false, reason: 'No authenticated actor' };
    }

    return policy.can(resolvedActor, action, resource);
  }

  async authorize<TResource>(
    resourceType: string,
    action: string,
    resource: TResource,
    actor?: Actor,
  ): Promise<void> {
    const result = await this.can(resourceType, action, resource, actor);
    if (!result.allowed) {
      throw new AuthorizationError(
        result.reason ?? `Action '${action}' not allowed on ${resourceType}`,
      );
    }
  }

  async filter<TResource>(
    resourceType: string,
    action: string,
    resources: TResource[],
    actor?: Actor,
  ): Promise<TResource[]> {
    const policy = this.policies.get(resourceType);
    if (!policy?.filter) {
      return resources;
    }

    const resolvedActor = actor ?? getActor();
    if (!resolvedActor) {
      return [];
    }

    return policy.filter(resolvedActor, action, resources) as Promise<TResource[]>;
  }
}

export const policyEvaluator = new PolicyEvaluator();

export class PolicyBuilder<TResource extends { tenantId?: string; ownerId?: string }> {
  private rules: Array<{
    action: string | '*';
    check: (actor: Actor, resource: TResource) => boolean | Promise<boolean>;
  }> = [];

  ownerCan(action: string | '*'): this {
    this.rules.push({
      action,
      check: (actor, resource) => actor.id === resource.ownerId,
    });
    return this;
  }

  tenantMemberCan(action: string | '*'): this {
    this.rules.push({
      action,
      check: (actor, resource) => actor.tenantId === resource.tenantId,
    });
    return this;
  }

  roleCan(action: string | '*', role: string): this {
    this.rules.push({
      action,
      check: (actor) => actor.roles?.includes(role) ?? false,
    });
    return this;
  }

  can(
    action: string | '*',
    check: (actor: Actor, resource: TResource) => boolean | Promise<boolean>,
  ): this {
    this.rules.push({ action, check });
    return this;
  }

  build(): Policy<TResource> {
    const rules = this.rules;

    return {
      async can(actor: Actor, action: string, resource: TResource): Promise<PolicyResult> {
        for (const rule of rules) {
          if (rule.action === '*' || rule.action === action) {
            const allowed = await rule.check(actor, resource);
            if (allowed) {
              return { allowed: true };
            }
          }
        }

        return { allowed: false, reason: `Action '${action}' not allowed` };
      },

      async filter(actor: Actor, action: string, resources: TResource[]): Promise<TResource[]> {
        const results: TResource[] = [];

        for (const resource of resources) {
          for (const rule of rules) {
            if (rule.action === '*' || rule.action === action) {
              const allowed = await rule.check(actor, resource);
              if (allowed) {
                results.push(resource);
                break;
              }
            }
          }
        }

        return results;
      },
    };
  }
}

export function definePolicy<
  TResource extends { tenantId?: string; ownerId?: string },
>(): PolicyBuilder<TResource> {
  return new PolicyBuilder<TResource>();
}
