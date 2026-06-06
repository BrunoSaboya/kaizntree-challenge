import { useAuthStore } from "@/store/authStore";

export function useRole() {
  const user = useAuthStore((s) => s.user);
  return {
    isAdmin: user?.role === "admin",
    isOwner: user?.role === "owner",
    isMember: user?.role === "member",
    role: user?.role ?? null,
  };
}
