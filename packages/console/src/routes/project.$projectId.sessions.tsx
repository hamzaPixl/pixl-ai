/**
 * Sessions layout route.
 *
 * This is a layout route that renders an Outlet for child routes.
 * The sessions list is now at the index route (project.$projectId.sessions.index.tsx).
 * Session detail is a child route (project.$projectId.sessions.$sessionId.tsx).
 */

import { createFileRoute, Outlet } from '@tanstack/react-router';

export const Route = createFileRoute('/project/$projectId/sessions')({
  component: SessionsLayout,
});

function SessionsLayout() {
  return <Outlet />;
}
