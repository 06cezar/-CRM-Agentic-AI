"use client"

import { useEffect, useState, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { api } from "@/lib/api"
import { Loader2, CheckCircle2, XCircle, Cpu } from "lucide-react"
import Link from "next/link"

function VerifyEmailContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading")
  const [message, setMessage] = useState("")

  useEffect(() => {
    if (!token) {
      setStatus("error")
      setMessage("Token-ul de verificare lipsește.")
      return
    }

    api.verifyEmail(token)
      .then((res) => {
        setStatus("success")
        setMessage(res.message)
      })
      .catch((err) => {
        setStatus("error")
        setMessage(err instanceof Error ? err.message : "A apărut o eroare la verificarea email-ului.")
      })
  }, [token])

  return (
    <>
      <div className="flex justify-center">
        {status === "loading" && <Loader2 className="size-12 animate-spin text-primary" />}
        {status === "success" && <CheckCircle2 className="size-12 text-green-500" />}
        {status === "error" && <XCircle className="size-12 text-destructive" />}
      </div>

      <div className="space-y-2">
        <h2 className="text-xl font-bold tracking-tight">
          {status === "loading" && "Verificăm email-ul..."}
          {status === "success" && "Email verificat!"}
          {status === "error" && "Eroare de verificare"}
        </h2>
        <p className="text-xs text-muted-foreground">{message}</p>
      </div>

      {status !== "loading" && (
        <Link
          href="/login"
          className="w-full h-10 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md font-medium transition-colors flex items-center justify-center"
        >
          Mergi la Login
        </Link>
      )}
    </>
  )
}

export default function VerifyEmailPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm p-8 text-center space-y-6 shadow-lg border border-border bg-card rounded-xl">
        <div className="flex items-center gap-3 text-left">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
            <Cpu className="size-5 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground">Agentic Command Center</h1>
            <p className="text-xs text-muted-foreground">Verificare email</p>
          </div>
        </div>

        <div className="h-px bg-border" />

        <Suspense fallback={<Loader2 className="size-12 animate-spin text-primary mx-auto" />}>
          <VerifyEmailContent />
        </Suspense>
      </div>
    </div>
  )
}
