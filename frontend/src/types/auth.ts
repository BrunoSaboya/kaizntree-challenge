export interface User {
  id: number;
  email: string;
  username: string;
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

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
  password_confirm: string;
}
