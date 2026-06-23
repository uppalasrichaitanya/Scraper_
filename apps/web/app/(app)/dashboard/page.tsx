/**
 * app/(app)/dashboard/page.tsx — Server component entry.
 *
 * Server-side auth guard: checks for the refresh_token cookie.
 * If missing, redirects immediately (no client-side flash).
 * If present, renders the client-side dashboard shell which
 * validates the session via /v1/users/me.
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { Metadata } from "next";
import DashboardShell from "./DashboardShell";

export const metadata: Metadata = {
  title: "Dashboard — JobsIndia",
  description: "Your personalised job dashboard with saved jobs, match scores, and application tracker.",
};

export default async function DashboardPage() {
  const cookieStore = await cookies();
  const hasRefreshToken = cookieStore.has("refresh_token");

  if (!hasRefreshToken) {
    redirect("/auth/login?redirect=/dashboard");
  }

  return <DashboardShell />;
}
