import { createFileRoute, Navigate } from "@tanstack/react-router";

export const Route = createFileRoute("/project/$projectId/settings/")({
  component: SettingsIndex,
});

function SettingsIndex() {
  const { projectId } = Route.useParams();
  return (
    <Navigate
      to="/project/$projectId/settings/general"
      params={{ projectId }}
      replace
    />
  );
}
