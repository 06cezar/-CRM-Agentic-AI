"use client"

import { useState, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { api } from "@/lib/api"
import { Loader2, CheckCircle2, Cpu } from "lucide-react"
import Link from "next/link"

function ResetPasswordForm() {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")

  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!token) {
      setError("Token-ul de resetare lipsește.")
      return
    }

    if (newPassword !== confirmPassword) {
      setError("Parolele nu se potrivesc.")
      return
    }

    setLoading(true)
    setError("")

    try {
      await api.resetPassword(token, newPassword)
      setSuccess(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "A apărut o eroare la resetarea parolei.")
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="text-center space-y-4">
        <p className="text-sm text-destructive">Token-ul de resetare lipsește sau este invalid.</p>
        <Link
          href="/login"
          className="w-full h-10 px-4 py-2 border border-input bg-background hover:bg-accent hover:text-accent-foreground rounded-md font-medium transition-colors flex items-center justify-center"
        >
          Înapoi la Login
        </Link>
      </div>
    )
  }

  if (success) {
    return (
      <div className="space-y-4 text-center animate-in fade-in slide-in-from-bottom-2 duration-500">
        <div className="flex justify-center">
          <CheckCircle2 className="size-12 text-green-500" />
        </div>
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Succes!</h2>
          <p className="text-xs text-muted-foreground">Parola ta a fost resetată cu succes.</p>
        </div>
        <Link
          href="/login"
          className="w-full h-10 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors flex items-center justify-center"
        >
          Mergi la Login
        </Link>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide" htmlFor="newPassword">Parolă nouă</label>
        <input
          id="newPassword"
          type="password"
          required
          className="flex h-10 w-full rounded-md border border-input bg-input px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide" htmlFor="confirmPassword">Confirmă parola</label>
        <input
          id="confirmPassword"
          type="password"
          required
          className="flex h-10 w-full rounded-md border border-input bg-input px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />
      </div>

      {error && <p className="text-xs text-destructive bg-destructive/10 p-2 rounded border border-destructive/20">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="w-full h-10 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
      >
        {loading && <Loader2 className="mr-2 size-4 animate-spin" />}
        Resetează Parola
      </button>
    </form>
  )
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm p-8 space-y-6 shadow-lg border border-border bg-card rounded-xl">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
            <Cpu className="size-5 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground">Agentic Command Center</h1>
            <p className="text-xs text-muted-foreground">Nouă parolă</p>
          </div>
        </div>

        <div className="h-px bg-border" />

        <Suspense fallback={<div className="text-xs text-muted-foreground text-center">Se încarcă...</div>}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  )
}
