export interface WorkspaceMember {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  joined_at?: string;
}

export interface Invitation {
  id: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

export interface Team {
  id: string;
  name: string;
  description: string | null;
  color: string | null;
  workspace_id: string;
}

export interface TeamMember {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  avatar: string | null;
}
