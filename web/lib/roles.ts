import type { Role } from "@/lib/api";

export function roleToPath(role: Role): string {
  switch (role) {
    case "admin": return "/dashboard/admin";
    case "tech":  return "/dashboard/technician"; // <- your tech route
    case "farmer":return "/dashboard/farmer";
    default:      return "/login";
  }
}
