"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Cpu,
  Bell,
  Settings,
  ChevronDown,
  Plus,
  LogOut,
} from "lucide-react"
import { api } from "@/lib/api"
import { useAuth } from "@/hooks/useAuth"

export function CommandHeader() {
  const router = useRouter()
  const { user } = useAuth()
  const [open, setOpen] = useState(false)

  const initials = user?.full_name
    ? user.full_name.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase()
    : "?"

  async function handleLogout() {
    await api.logout()
    router.push("/login")
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4">
      {/* Logo and title */}
      <div className="flex items-center gap-3">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
          <Cpu className="size-5 text-primary" />
        </div>
        <div className="hidden sm:block">
          <h1 className="text-sm font-semibold text-foreground">
            Agentic Command Center
          </h1>
          <p className="text-xs text-muted-foreground">
            AI-powered sales intelligence
          </p>
        </div>
      </div>

      {/* Center stats */}
      <div className="hidden md:flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className="size-2 rounded-full bg-score-hot animate-pulse" />
          <span className="text-xs text-muted-foreground">
            <span className="font-mono text-foreground">3</span> hot leads today
          </span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            AI processed <span className="font-mono text-foreground">47</span> actions
          </span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            Pipeline value: <span className="font-mono text-primary font-semibold">€237K</span>
          </span>
        </div>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" className="hidden sm:flex gap-1.5">
          <Plus className="size-3.5" />
          Add Lead
        </Button>
        <Button variant="ghost" size="icon-sm" className="relative">
          <Bell className="size-4" />
          <span className="absolute -top-0.5 -right-0.5 flex size-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
            3
          </span>
        </Button>
        <Button variant="ghost" size="icon-sm">
          <Settings className="size-4" />
        </Button>
        <div className="ml-2 h-6 w-px bg-border hidden sm:block" />
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            className="flex gap-2"
            onClick={() => setOpen(o => !o)}
          >
            <div className="flex size-6 items-center justify-center rounded-full bg-primary/20 text-xs font-semibold text-primary">
              {initials}
            </div>
            <span className="hidden sm:block text-sm">{user?.full_name ?? "…"}</span>
            <ChevronDown className="size-3 text-muted-foreground" />
          </Button>

          {open && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
              <div className="absolute right-0 top-10 z-20 w-44 rounded-lg border border-border bg-card shadow-lg py-1">
                {user && (
                  <>
                    <div className="px-3 py-2 border-b border-border">
                      <p className="text-xs font-medium text-foreground truncate">{user.full_name}</p>
                      <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                    </div>
                  </>
                )}
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                >
                  <LogOut className="size-4" />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
