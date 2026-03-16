/**
 * Media domain events
 */

export const MediaEvents = {
  FILE_UPLOADED: 'media.file.uploaded',
  FILE_PROCESSED: 'media.file.processed',
  FILE_DELETED: 'media.file.deleted',
  FOLDER_CREATED: 'media.folder.created',
  FOLDER_DELETED: 'media.folder.deleted',
} as const;

export type MediaEventType = (typeof MediaEvents)[keyof typeof MediaEvents];
