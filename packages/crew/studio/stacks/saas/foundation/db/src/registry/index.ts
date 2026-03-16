import type { PrismaClientLike } from '../client';

export type RepositoryConstructor<T> = new (prisma: PrismaClientLike) => T;

class RepositoryRegistry {
  private static instance: RepositoryRegistry;
  private repositories = new Map<string, unknown>();
  private constructors = new Map<string, RepositoryConstructor<unknown>>();
  private prisma: PrismaClientLike | null = null;

  private constructor() {}

  static getInstance(): RepositoryRegistry {
    if (!RepositoryRegistry.instance) {
      RepositoryRegistry.instance = new RepositoryRegistry();
    }
    return RepositoryRegistry.instance;
  }

  initialize(prisma: PrismaClientLike): void {
    this.prisma = prisma;
    this.repositories.clear();
  }

  register<T>(name: string, constructor: RepositoryConstructor<T>): void {
    this.constructors.set(name, constructor as RepositoryConstructor<unknown>);
  }

  get<T>(name: string): T {
    if (!this.prisma) {
      throw new Error('RepositoryRegistry not initialized. Call initialize(prisma) first.');
    }

    if (this.repositories.has(name)) {
      return this.repositories.get(name) as T;
    }

    const Constructor = this.constructors.get(name);
    if (!Constructor) {
      throw new Error(`Repository '${name}' not registered.`);
    }

    const instance = new Constructor(this.prisma);
    this.repositories.set(name, instance);
    return instance as T;
  }

  get isInitialized(): boolean {
    return this.prisma !== null;
  }

  get names(): string[] {
    return Array.from(this.constructors.keys());
  }

  clear(): void {
    this.repositories.clear();
  }

  reset(): void {
    this.repositories.clear();
    this.constructors.clear();
    this.prisma = null;
  }
}

export const repositoryRegistry = RepositoryRegistry.getInstance();

export function Repository(name: string) {
  return function <T extends RepositoryConstructor<InstanceType<T>>>(
    constructor: T,
  ): T {
    repositoryRegistry.register(name, constructor);
    return constructor;
  };
}
