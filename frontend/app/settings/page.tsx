"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CommandHeader } from "@/components/command-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  X,
  Mail,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Plug,
  Unplug,
  Settings,
  LogOut,
  User,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ConnectedAccount {
  id: number;
  email: string;
  provider: string;
  is_watching: boolean;
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function SettingsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [user, setUser] = useState<{ email: string; full_name: string; role: string } | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [connectingGoogle, setConnectingGoogle] = useState(false);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [disconnectingId, setDisconnectingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // OAuth callback result from URL
  useEffect(() => {
    const errorParam = searchParams.get("error");
    const connectedParam = searchParams.get("connected");
    if (errorParam) setError(decodeURIComponent(errorParam));
    if (connectedParam === "true") {
      setSuccessMsg("Google account connected successfully.");
      fetchAccounts();
    }
  }, [searchParams]);

  const fetchAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const res = await fetch(`${apiUrl}/api/auth/google/get_connected_accounts`, {
        credentials: "include",
      });
      if (res.ok) setAccounts(await res.json());
    } catch {
      // silently ignore
    } finally {
      setLoadingAccounts(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
    api.me().then(setUser).catch(() => {});
  }, []);

  const handleSignOut = async () => {
    setSigningOut(true);
    try {
      await api.logout();
    } finally {
      router.push("/login");
    }
  };

  const handleGoogleConnect = async () => {
    setConnectingGoogle(true);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/auth/google/login`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("Could not reach server.");
      const data = await res.json();
      if (data.auth_url) window.location.href = data.auth_url;
      else throw new Error("Missing auth URL from server.");
    } catch (err: any) {
      setError(err.message || "Failed to initiate authentication.");
      setConnectingGoogle(false);
    }
  };

  const handleDisconnect = async (accountId: number) => {
    setDisconnectingId(accountId);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/auth/google/disconnect`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Disconnect failed.");
      }
      setAccounts((prev) => prev.filter((a) => a.id !== accountId));
      setSuccessMsg("Google account disconnected.");
    } catch (err: any) {
      setError(err.message || "Failed to disconnect.");
    } finally {
      setDisconnectingId(null);
    }
  };

  const handleToggleWatch = async (accountId: number, current: boolean) => {
    setTogglingId(accountId);
    const next = !current;
    setAccounts((prev) =>
      prev.map((a) => (a.id === accountId ? { ...a, is_watching: next } : a))
    );
    try {
      await fetch(`${apiUrl}/api/gmail/watch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ account_id: accountId, active: next }),
      });
      await fetch(`${apiUrl}/api/gmail/set-status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ account_id: accountId, active: next }),
      });
    } catch {
      // revert optimistic update
      setAccounts((prev) =>
        prev.map((a) => (a.id === accountId ? { ...a, is_watching: current } : a))
      );
      setError("Failed to update monitoring status.");
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <CommandHeader />

      <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-3xl mx-auto w-full">

        {/* Page header */}
        <div className="mb-8 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10">
              <Settings className="size-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">Settings</h1>
              <p className="text-sm text-muted-foreground">
                Manage integrations and account preferences
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/")}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="size-4" />
          </Button>
        </div>

        {/* Alerts */}
        {successMsg && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/10 px-4 py-3 text-sm text-primary">
            <CheckCircle2 className="size-4 shrink-0" />
            <span>{successMsg}</span>
            <button
              onClick={() => setSuccessMsg(null)}
              className="ml-auto text-primary/60 hover:text-primary"
            >
              <X className="size-3.5" />
            </button>
          </div>
        )}
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <AlertCircle className="size-4 shrink-0" />
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-destructive/60 hover:text-destructive"
            >
              <X className="size-3.5" />
            </button>
          </div>
        )}

        {/* Profile section */}
        <div className="mb-4 rounded-lg border border-border bg-card px-4 sm:px-5 py-4">
          <h2 className="text-sm font-semibold text-foreground mb-3">Profile</h2>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/20 text-primary font-semibold text-sm">
                {user?.full_name
                  ? user.full_name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
                  : <User className="size-4" />}
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {user?.full_name ?? "—"}
                </p>
                <p className="text-xs text-muted-foreground">{user?.email ?? "—"}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 shrink-0"
              onClick={handleSignOut}
              disabled={signingOut}
            >
              {signingOut ? (
                <RefreshCw className="size-3.5 animate-spin" />
              ) : (
                <LogOut className="size-3.5" />
              )}
              Sign out
            </Button>
          </div>
        </div>

        {/* Integrations section */}
        <div className="rounded-lg border border-border bg-card">
          {/* Section header */}
          <div className="flex items-center justify-between gap-3 border-b border-border px-4 sm:px-5 py-4">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-foreground">Integrations</h2>
              <p className="text-xs text-muted-foreground mt-0.5 hidden sm:block">
                Connected accounts and sync preferences
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 shrink-0"
              onClick={handleGoogleConnect}
              disabled={connectingGoogle}
            >
              {connectingGoogle ? (
                <>
                  <RefreshCw className="size-3.5 animate-spin" />
                  <span className="hidden sm:inline">Connecting...</span>
                </>
              ) : (
                <>
                  <Plug className="size-3.5" />
                  <span className="hidden sm:inline">Connect Google</span>
                  <span className="sm:hidden">Connect</span>
                </>
              )}
            </Button>
          </div>

          {/* Account list */}
          <div className="px-4 sm:px-5 py-4">
            {loadingAccounts ? (
              <div className="space-y-3">
                {[1, 2].map((i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Skeleton className="size-10 rounded-full" />
                    <div className="flex-1 space-y-1.5">
                      <Skeleton className="h-3 w-40" />
                      <Skeleton className="h-2.5 w-24" />
                    </div>
                    <Skeleton className="h-8 w-20 rounded-md" />
                  </div>
                ))}
              </div>
            ) : accounts.length === 0 ? (
              <div className="flex flex-col items-center gap-3 py-10 text-center">
                <div className="flex size-12 items-center justify-center rounded-full bg-secondary">
                  <Mail className="size-5 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">No accounts connected</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Connect your Gmail to sync client messages into the CRM
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-1 gap-1.5"
                  onClick={handleGoogleConnect}
                  disabled={connectingGoogle}
                >
                  {connectingGoogle ? (
                    <><RefreshCw className="size-3.5 animate-spin" /> Connecting...</>
                  ) : (
                    <><Plug className="size-3.5" /> Connect Gmail</>
                  )}
                </Button>
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {accounts.map((account) => (
                  <li key={account.id} className="py-4 first:pt-0 last:pb-0">
                    <div className="flex items-center gap-3">
                      {/* Avatar */}
                      <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/20 text-primary font-bold text-sm">
                        G
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">
                          {account.email}
                        </p>
                        <div className="mt-0.5 flex items-center gap-2">
                          <span className="text-xs text-muted-foreground capitalize">
                            {account.provider}
                          </span>
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-[10px] h-4 px-1.5",
                              account.is_watching
                                ? "border-primary/40 text-primary"
                                : "border-muted-foreground/30 text-muted-foreground"
                            )}
                          >
                            {account.is_watching ? "Monitoring" : "Paused"}
                          </Badge>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        {/* Watch toggle */}
                        <button
                          type="button"
                          onClick={() => handleToggleWatch(account.id, account.is_watching)}
                          disabled={togglingId === account.id}
                          title={account.is_watching ? "Pause monitoring" : "Start monitoring"}
                          className={cn(
                            "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
                            account.is_watching ? "bg-primary" : "bg-secondary",
                            togglingId === account.id && "opacity-50 cursor-not-allowed"
                          )}
                          role="switch"
                          aria-checked={account.is_watching}
                        >
                          <span className="sr-only">Toggle monitoring</span>
                          <span
                            aria-hidden="true"
                            className={cn(
                              "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200 ease-in-out",
                              account.is_watching ? "translate-x-4" : "translate-x-0"
                            )}
                          />
                        </button>

                        {/* Disconnect — icon only on mobile, text on sm+ */}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 px-2 sm:px-3"
                          onClick={() => handleDisconnect(account.id)}
                          disabled={disconnectingId === account.id}
                        >
                          {disconnectingId === account.id ? (
                            <RefreshCw className="size-3.5 animate-spin" />
                          ) : (
                            <Unplug className="size-3.5" />
                          )}
                          <span className="hidden sm:inline">Disconnect</span>
                        </Button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* About section */}
        <div className="mt-4 rounded-lg border border-border bg-card px-4 sm:px-5 py-4">
          <h2 className="text-sm font-semibold text-foreground mb-3">About</h2>
          <div className="space-y-2 text-xs text-muted-foreground">
            <div className="flex items-center justify-between">
              <span>Platform</span>
              <span className="text-foreground font-medium">CRM Agentic AI</span>
            </div>
            <div className="flex items-center justify-between">
              <span>AI Model</span>
              <span className="text-foreground font-medium font-mono">llama3.2:3b</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Active Agents</span>
              <span className="text-foreground font-medium">4</span>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="size-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        </div>
      }
    >
      <SettingsContent />
    </Suspense>
  );
}
