"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api"

export function useAuth() {
  const router = useRouter()
  const [user, setUser] = useState<{ id: number; email: string; full_name: string; role: string } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.me()
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false))
  }, [router])

  return { user, loading }
}
