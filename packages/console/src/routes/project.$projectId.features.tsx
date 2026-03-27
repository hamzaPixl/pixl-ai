/**
 * Features layout route.
 *
 * This is a layout route that renders an Outlet for child routes.
 * The features list is at the index route (project.$projectId.features.index.tsx).
 * Feature detail is a child route (project.$projectId.features.$featureId.tsx).
 */

import { createFileRoute, Outlet } from '@tanstack/react-router';

export const Route = createFileRoute('/project/$projectId/features')({
  component: FeaturesLayout,
});

function FeaturesLayout() {
  return <Outlet />;
}
