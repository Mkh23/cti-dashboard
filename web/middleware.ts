// web/middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const token = req.cookies.get("token")?.value;
  const { pathname } = req.nextUrl;

  const isAuthRoute = pathname === "/login" || pathname.startsWith("/login/");
  const isProtected = pathname.startsWith("/dashboard");

  // Block protected routes if no token
  if (isProtected && !token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  // If already logged in, keep users away from /login
  if (isAuthRoute && token) {
    const url = req.nextUrl.clone();
    // optional: send them to their last role or a default dashboard
    url.pathname = "/dashboard/admin";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login"],
};
