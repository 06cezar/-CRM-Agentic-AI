"use client"

import { useState } from "react"
import { api } from "@/lib/api"
import { Loader2, Mail, Cpu } from "lucide-react"
import Link from "next/link"

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError("")

    try {
      await api.forgotPassword(email)
      setSubmitted(true)
    } catch (err: any) {
      setError(err.message || "A apărut o eroare. Te rugăm să încerci din nou.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm p-8 space-y-6 shadow-lg border border-border bg-card rounded-xl">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
            <Cpu className="size-5 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground">Agentic Command Center</h1>
            <p className="text-xs text-muted-foreground">Resetare parolă</p>
          </div>
        </div>

        <div className="h-px bg-border" />

        {submitted ? (
          <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="flex justify-center">
              <div className="rounded-full bg-primary/10 p-3">
                <Mail className="size-8 text-primary" />
              </div>
            </div>
            <div className="text-center space-y-2">
              <h2 className="text-lg font-semibold">Verifică email-ul</h2>
              <p className="text-xs text-muted-foreground">
                Dacă adresa <strong>{email}</strong> este înregistrată, vei primi instrucțiunile de resetare în scurt timp.
              </p>
            </div>
            <Link
              href="/login"
              className="w-full h-10 px-4 py-2 border border-input bg-background hover:bg-accent hover:text-accent-foreground rounded-md font-medium transition-colors flex items-center justify-center"
            >
              Înapoi la Login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide" htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                placeholder="you@company.com"
                required
                className="flex h-10 w-full rounded-md border border-input bg-input px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            {error && <p className="text-xs text-destructive bg-destructive/10 p-2 rounded border border-destructive/20">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-10 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="mr-2 size-4 animate-spin" />}
              Trimite link de resetare
            </button>

            <div className="text-center">
              <Link href="/login" className="text-xs text-primary hover:underline">
                Înapoi la Login
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
