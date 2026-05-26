export interface User {
  id: number;
  email: string;
  username: string;
  date_joined: string;
}

export interface AuthTokens {
  access: string;
  user: User;
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
