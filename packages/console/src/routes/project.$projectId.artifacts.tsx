/**
 * Artifacts layout route.
 *
 * This is a layout route that renders an Outlet for child routes.
 * The artifacts list is at the index route (project.$projectId.artifacts.index.tsx).
 * Artifact detail is a child route (project.$projectId.artifacts.$artifactId.tsx).
 */

import { createFileRoute, Outlet } from '@tanstack/react-router';

export const Route = createFileRoute('/project/$projectId/artifacts')({
  component: ArtifactsLayout,
});

function ArtifactsLayout() {
  return <Outlet />;
}
