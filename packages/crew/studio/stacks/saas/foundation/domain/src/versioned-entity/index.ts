/**
 * VersionedEntity mixin — adds draft/published content versioning.
 *
 * Tracks version history with copy-on-write semantics.
 * Each publish creates a new version snapshot; drafts are mutable.
 */

import type { TenantEntityProps } from "../entity";
import { TenantAggregateRoot } from "../aggregate-root";

export type ContentStatus = "draft" | "published" | "archived";

export interface VersionedEntityProps extends TenantEntityProps {
  status: ContentStatus;
  contentVersion: number;
  publishedVersion: number | null;
  publishedAt: Date | null;
}

export interface VersionSnapshot {
  version: number;
  status: ContentStatus;
  snapshotData: Record<string, unknown>;
  createdAt: Date;
  createdBy: string | null;
}

/**
 * Abstract base for entities that support draft/published versioning.
 *
 * Usage:
 * ```typescript
 * class Article extends VersionedAggregateRoot<ArticleProps> {
 *   publish(): Article { return this.doPublish(); }
 *   unpublish(): Article { return this.doUnpublish(); }
 * }
 * ```
 */
/**
 * Compare two version snapshots and return the keys whose values differ.
 */
export function diffSnapshots(
  a: VersionSnapshot,
  b: VersionSnapshot,
): { key: string; before: unknown; after: unknown }[] {
  const allKeys = new Set([
    ...Object.keys(a.snapshotData),
    ...Object.keys(b.snapshotData),
  ]);
  const changes: { key: string; before: unknown; after: unknown }[] = [];
  for (const key of allKeys) {
    const av = a.snapshotData[key];
    const bv = b.snapshotData[key];
    if (JSON.stringify(av) !== JSON.stringify(bv)) {
      changes.push({ key, before: av, after: bv });
    }
  }
  return changes;
}

export abstract class VersionedAggregateRoot<
  TProps extends VersionedEntityProps,
> extends TenantAggregateRoot<TProps> {
  private _versionHistory: VersionSnapshot[] = [];

  protected constructor(props: TProps) {
    super(props);
  }

  get status(): ContentStatus {
    return this.props.status;
  }

  get contentVersion(): number {
    return this.props.contentVersion;
  }

  get publishedVersion(): number | null {
    return this.props.publishedVersion;
  }

  get publishedAt(): Date | null {
    return this.props.publishedAt;
  }

  get isDraft(): boolean {
    return this.props.status === "draft";
  }

  get isPublished(): boolean {
    return this.props.status === "published";
  }

  get versionHistory(): ReadonlyArray<VersionSnapshot> {
    return [...this._versionHistory];
  }

  protected setVersionHistory(history: VersionSnapshot[]): void {
    this._versionHistory = history;
  }

  /**
   * Snapshot the current content for version history.
   * Override to include entity-specific data.
   */
  protected abstract getSnapshotData(): Record<string, unknown>;

  /**
   * Transition to published state, creating a version snapshot.
   */
  protected doPublish(publishedBy?: string): TProps {
    if (this.isDeleted) {
      throw new Error("Cannot publish deleted entity");
    }

    const newVersion = this.props.contentVersion + 1;
    const now = new Date();

    this._versionHistory.push({
      version: newVersion,
      status: "published",
      snapshotData: this.getSnapshotData(),
      createdAt: now,
      createdBy: publishedBy ?? null,
    });

    return {
      ...this.props,
      status: "published" as ContentStatus,
      contentVersion: newVersion,
      publishedVersion: newVersion,
      publishedAt: now,
      updatedBy: publishedBy ?? this.props.updatedBy,
      updatedAt: now,
    };
  }

  /**
   * Revert to draft state.
   */
  protected doUnpublish(updatedBy?: string): TProps {
    if (this.props.status !== "published") {
      throw new Error("Can only unpublish a published entity");
    }

    return {
      ...this.props,
      status: "draft" as ContentStatus,
      updatedBy: updatedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
    };
  }

  /**
   * Archive the entity (soft removal from public access).
   */
  protected doArchive(updatedBy?: string): TProps {
    return {
      ...this.props,
      status: "archived" as ContentStatus,
      updatedBy: updatedBy ?? this.props.updatedBy,
      updatedAt: new Date(),
    };
  }
}
