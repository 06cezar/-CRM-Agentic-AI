"use client"

import { useState, useRef } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Upload, FileText, CheckCircle, AlertCircle, X } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

interface ImportResult {
  imported: number
  skipped: number
  errors: string[]
}

interface ImportCsvModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function ImportCsvModal({ open, onClose, onSuccess }: ImportCsvModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleFile(f: File | null) {
    if (!f) return
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setError("Doar fișiere .csv sunt acceptate")
      return
    }
    setFile(f)
    setError(null)
    setResult(null)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    handleFile(e.dataTransfer.files[0] ?? null)
  }

  async function handleImport() {
    if (!file) return
    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("file", file)

      const res = await fetch(`${API_URL}/leads/import`, {
        method: "POST",
        credentials: "include",
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Import failed" }))
        throw new Error(err.detail ?? "Import failed")
      }

      const data: ImportResult = await res.json()
      setResult(data)
      if (data.imported > 0) onSuccess()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Import failed")
    } finally {
      setLoading(false)
    }
  }

  function handleClose() {
    setFile(null)
    setResult(null)
    setError(null)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Import CSV</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Format hint */}
          <p className="text-xs text-muted-foreground">
            Acceptă exporturi din <strong>LinkedIn</strong>, <strong>HubSpot</strong>, <strong>Excel</strong> sau orice CSV cu coloanele:{" "}
            <code className="text-xs bg-muted px-1 rounded">name, email, company, role, phone, deal_value, currency</code>
          </p>

          {/* Drop zone */}
          {!result && (
            <div
              className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-primary/5 transition-colors"
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
              />
              {file ? (
                <div className="flex items-center justify-center gap-2">
                  <FileText className="size-5 text-primary" />
                  <span className="text-sm font-medium">{file.name}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); setFile(null) }}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="size-4" />
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="size-8 text-muted-foreground mx-auto" />
                  <p className="text-sm text-muted-foreground">
                    Trage fișierul CSV aici sau <span className="text-primary underline">alege fișier</span>
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Result */}
          {result && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle className="size-4 text-green-500 shrink-0" />
                <span><strong>{result.imported}</strong> lead-uri importate cu succes</span>
              </div>
              {result.skipped > 0 && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <AlertCircle className="size-4 shrink-0" />
                  <span><strong>{result.skipped}</strong> rânduri sărite (lipsă name/email)</span>
                </div>
              )}
              {result.errors.length > 0 && (
                <div className="rounded-md bg-muted p-3 space-y-1">
                  {result.errors.map((e, i) => (
                    <p key={i} className="text-xs text-muted-foreground">{e}</p>
                  ))}
                </div>
              )}
              {result.imported > 0 && (
                <p className="text-xs text-muted-foreground">
                  Research AI pornit automat în background pentru fiecare lead importat.
                </p>
              )}
            </div>
          )}

          {/* Error */}
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            {result ? "Close" : "Cancel"}
          </Button>
          {!result && (
            <Button onClick={handleImport} disabled={!file || loading}>
              {loading ? "Importing…" : "Import"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
