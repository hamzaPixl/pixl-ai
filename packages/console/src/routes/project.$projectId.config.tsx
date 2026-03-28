/**
 * Config — redirects to /workflows (legacy route support).
 */

import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/project/$projectId/config')({
  beforeLoad: ({ params, search }) => {
    const tab = (search as { tab?: string }).tab;
    throw redirect({
      to: tab === 'agents' ? '/project/$projectId/agents' : '/project/$projectId/workflows',
      params,
    });
  },
});
