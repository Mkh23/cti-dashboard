// web/lib/roles.ts

export type Role = "admin" | "technician" | "farmer";

/** Choose a role by priority: admin > technician > farmer */
export function pickRole(roles: string[] | Role[] | null | undefined): Role {
  if (!roles || roles.length === 0) return "technician";
  if (roles.includes("admin")) return "admin";
  if (roles.includes("technician")) return "technician";
  return "farmer";
}

/** Map a role to its dashboard path */
export function roleToPath(role: string | Role | null | undefined): string {
  switch (role) {
    case "admin": return "/dashboard/admin";
    case "technician": return "/dashboard/technician";
    case "farmer": return "/dashboard/farmer";
    default: return "/login";
  }
}
