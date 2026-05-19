"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Cpu, AlertCircle, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { useEffect } from "react"

export default function RegisterPage() {
  const router = useRouter()
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [shaking, setShaking] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  useEffect(() => {
    api.me().then(() => router.replace("/")).catch(() => {})
  }, [router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await api.register(email, fullName, password)
      setIsSuccess(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed")
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

  const passwordValid = password.length >= 8

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
            <p className="text-xs text-muted-foreground">Create your account</p>
          </div>
        </div>

        <div className="h-px bg-border" />

        {isSuccess ? (
          <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="flex justify-center">
              <div className="rounded-full bg-primary/10 p-3">
                <CheckCircle2 className="size-8 text-primary" />
              </div>
            </div>
            <div className="text-center space-y-2">
              <h2 className="text-lg font-semibold">Verifică email-ul</h2>
              <p className="text-xs text-muted-foreground">
                Am trimis un link de activare la <strong>{email}</strong>. Te rugăm să îți verifici inbox-ul pentru a activa contul.
              </p>
            </div>
            <Link
              href="/login"
              className="w-full h-10 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors flex items-center justify-center"
            >
              Mergi la Login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className={`space-y-4 ${shaking ? "shake" : ""}`}>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide" htmlFor="full_name">
                Full name
              </label>
              <input
                id="full_name"
                type="text"
                required
                value={fullName}
                onChange={e => { setFullName(e.target.value); setError("") }}
                className={inputClass}
                placeholder="Ana Ionescu"
              />
            </div>

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
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={e => { setPassword(e.target.value); setError("") }}
                className={inputClass}
                placeholder="min. 8 characters"
              />
              {password.length > 0 && (
                <div className="flex items-center gap-1.5">
                  {passwordValid
                    ? <CheckCircle2 className="size-3 text-primary" />
                    : <AlertCircle className="size-3 text-destructive" />}
                  <span className={cn("text-xs", passwordValid ? "text-primary" : "text-destructive")}>
                    {passwordValid ? "Password looks good" : `${password.length}/8 characters`}
                  </span>
                </div>
              )}
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
              className="w-full h-10 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="size-4 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" />
                  Creating account…
                </>
              ) : "Create account"}
            </button>          </form>
        )}

        {!isSuccess && (
          <p className="text-center text-xs text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:text-primary/80 transition-colors">
              Sign in
            </Link>
          </p>
        )}
      </div>
    </div>
  )
}
