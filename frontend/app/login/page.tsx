"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Cpu, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { useEffect } from "react"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [shaking, setShaking] = useState(false)

  useEffect(() => {
    api.me().then(() => router.replace("/")).catch(() => {})
  }, [router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await api.login(email, password)
      router.push("/")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed")
      setShaking(true)
      setTimeout(() => setShaking(false), 500)
    } finally {
      setLoading(false)
    }
  }

  const inputClass = cn(
    "w-full rounded-md border bg-input px-3 py-2 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors",
    error ? "border-destructive focus:ring-destructive/50" : "border-border"
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm md:max-w-md lg:max-w-lg xl:max-w-sm space-y-6 p-8 rounded-xl border border-border bg-card shadow-lg">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
            <Cpu className="size-5 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground">Agentic Command Center</h1>
            <p className="text-xs text-muted-foreground">Sign in to your account</p>
          </div>
        </div>

        <div className="h-px bg-border" />

        <form onSubmit={handleSubmit} className={`space-y-4 ${shaking ? "shake" : ""}`}>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={e => { setEmail(e.target.value); setError("") }}
              className={inputClass}
              placeholder="you@company.com"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide" htmlFor="password">
                Password
              </label>
              <Link href="/forgot-password" className="text-xs text-primary hover:underline">
                Forgot password?
              </Link>
            </div>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={e => { setPassword(e.target.value); setError("") }}
              className={inputClass}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2">
              <AlertCircle className="size-4 text-destructive shrink-0" />
              <p className="text-xs text-destructive">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full h-10 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="size-4 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" />
                Signing in…
              </span>
            ) : "Sign in"}
          </button>
        </form>

        <p className="text-center text-xs text-muted-foreground">
          No account?{" "}
          <Link href="/register" className="text-primary hover:text-primary/80 transition-colors">
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}
