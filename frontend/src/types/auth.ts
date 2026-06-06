export type UserRole = "admin" | "owner" | "member";

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  organization_id: number | null;
  organization_name: string | null;
  date_joined: string;
}

export interface Organization {
  id: number;
  name: string;
  owner: number;
  owner_email: string;
  created_at: string;
}

export interface OrgMember {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  role: "member";
  organization: number;
  organization_name: string | null;
  is_active: boolean;
  date_joined: string;
}

export interface AuthTokens {
  access: string;
  user: User;
  /** Refresh token returned in the response body alongside the httpOnly cookie.
   *  Used as a sessionStorage fallback when cross-domain cookies are blocked. */
  refresh_token?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface CreateUserPayload {
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  role: UserRole;
  organization?: number | null;
  password: string;
}

export interface CreateMemberPayload {
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  password: string;
}

export interface UpdateMemberPayload {
  first_name?: string;
  last_name?: string;
  password?: string;
}

export interface CreateOrgPayload {
  name: string;
  owner: number;
}

export interface ProvisionOrgPayload {
  name: string;
  owner_email: string;
  owner_username: string;
  owner_password: string;
  owner_first_name?: string;
  owner_last_name?: string;
}
