"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { toast } from "sonner"
import {
  X,
  Upload,
  FileText,
  CheckCircle,
  AlertCircle,
  Loader2,
  Linkedin,
  Sparkles,
  Search,
  ChevronRight,
} from "lucide-react"
import { api, type ScrapeJobAPI, type SearchQuerySuggestion } from "@/lib/api"

interface LinkedInScraperModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

type Tab = "credentials" | "scrape" | "suggest"

export function LinkedInScraperModal({ open, onClose, onSuccess }: LinkedInScraperModalProps) {
  const [tab, setTab] = useState<Tab>("credentials")
  const [hasCredentials, setHasCredentials] = useState(false)

  // Credentials tab
  const [cookieFile, setCookieFile] = useState<File | null>(null)
  const [credLoading, setCredLoading] = useState(false)
  const [credError, setCredError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Scrape tab
  const [query, setQuery] = useState("")
  const [pages, setPages] = useState(2)
  const [scrapeLoading, setScrapeLoading] = useState(false)
  const [scrapeError, setScrapeError] = useState<string | null>(null)
  const [activeJob, setActiveJob] = useState<ScrapeJobAPI | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Suggest tab
  const [suggestLoading, setSuggestLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<SearchQuerySuggestion[]>([])
  const [suggestError, setSuggestError] = useState<string | null>(null)

  const fetchCredStatus = useCallback(async () => {
    try {
      const { has_credentials } = await api.getLinkedInCredentialStatus()
      setHasCredentials(has_credentials)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    if (open) fetchCredStatus()
  }, [open, fetchCredStatus])

  // Poll active job
  useEffect(() => {
    if (activeJob && (activeJob.status === "pending" || activeJob.status === "running")) {
      pollRef.current = setInterval(async () => {
        try {
          const updated = await api.getScrapeJob(activeJob.id)
          setActiveJob(updated)
          if (updated.status === "completed") {
            clearInterval(pollRef.current!)
            toast.success(`Scrape completed`, {
              description: `${updated.leads_created} leads added to pipeline`,
            })
            onSuccess()
          } else if (updated.status === "failed") {
            clearInterval(pollRef.current!)
            toast.error("Scrape failed", { description: updated.error_message ?? "Unknown error" })
          }
        } catch {
          // ignore transient errors
        }
      }, 3000)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [activeJob?.id, activeJob?.status, onSuccess])

  function handleClose() {
    setCookieFile(null)
    setCredError(null)
    setScrapeError(null)
    onClose()
  }

  // ── Credentials tab ──────────────────────────────────────────────────────

  function handleCookieFile(f: File | null) {
    if (!f) return
    if (!f.name.toLowerCase().endsWith(".json")) {
      setCredError("Please upload a .json file exported from Cookie-Editor")
      return
    }
    setCookieFile(f)
    setCredError(null)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    handleCookieFile(e.dataTransfer.files[0] ?? null)
  }

  async function handleSaveCookies() {
    if (!cookieFile) return
    setCredLoading(true)
    setCredError(null)
    try {
      const text = await cookieFile.text()
      JSON.parse(text) // validate JSON
      await api.uploadLinkedInCookies(text)
      setHasCredentials(true)
      setCookieFile(null)
      toast.success("Cookies saved", { description: "LinkedIn session is now active" })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save cookies"
      setCredError(msg.includes("JSON") ? "Invalid JSON — make sure you exported from Cookie-Editor" : msg)
      toast.error("Failed to save cookies", { description: msg })
    } finally {
      setCredLoading(false)
    }
  }

  async function handleRemoveCookies() {
    try {
      await api.deleteLinkedInCredentials()
      setHasCredentials(false)
      toast.info("Credentials removed")
    } catch {
      toast.error("Failed to remove credentials")
    }
  }

  // ── Scrape tab ───────────────────────────────────────────────────────────

  async function handleStartScrape() {
    if (!query.trim()) return
    setScrapeLoading(true)
    setScrapeError(null)
    try {
      const job = await api.startScrapeJob(query.trim(), pages)
      setActiveJob(job)
      toast.info(`Scrape job started`, { description: `Searching for "${query}"` })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start scrape"
      setScrapeError(msg)
      toast.error("Failed to start scrape", { description: msg })
    } finally {
      setScrapeLoading(false)
    }
  }

  function handleStartAnother() {
    setActiveJob(null)
    setQuery("")
    setScrapeError(null)
  }

  function progressPercent(job: ScrapeJobAPI) {
    const estimated = job.pages_requested * 25
    return Math.min(100, Math.round((job.scraped_count / estimated) * 100))
  }

  // ── Suggest tab ──────────────────────────────────────────────────────────

  async function handleSuggest() {
    setSuggestLoading(true)
    setSuggestError(null)
    setSuggestions([])
    try {
      const result = await api.suggestSearchQueries()
      setSuggestions(result.queries)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Agent failed"
      setSuggestError(msg)
      toast.error("AI agent failed", { description: msg })
    } finally {
      setSuggestLoading(false)
    }
  }

  function handleUseQuery(q: string) {
    setQuery(q)
    setTab("scrape")
  }

  if (!open) return null

  const statusBadge = (status: ScrapeJobAPI["status"]) => {
    const map = {
      pending: "bg-yellow-500/20 text-yellow-400",
      running: "bg-blue-500/20 text-blue-400",
      completed: "bg-green-500/20 text-green-400",
      failed: "bg-red-500/20 text-red-400",
    }
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${map[status]}`}>
        {status === "running" && <Loader2 className="size-3 animate-spin" />}
        {status}
      </span>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="glass-panel border rounded-lg shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <Linkedin className="size-5 text-[#0A66C2]" />
            <h2 className="text-lg font-semibold">LinkedIn Scraper</h2>
            {hasCredentials && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-400">
                <span className="size-1.5 rounded-full bg-green-400 inline-block" />
                Active
              </span>
            )}
          </div>
          <button onClick={handleClose} className="p-1 hover:bg-accent rounded-md transition-colors">
            <X className="size-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border shrink-0">
          {(["credentials", "scrape", "suggest"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 px-3 py-2.5 text-xs font-medium transition-colors capitalize ${
                tab === t
                  ? "border-b-2 border-primary text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "credentials" && "Credentials"}
              {t === "scrape" && "Scrape"}
              {t === "suggest" && "AI Suggest"}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {/* ── Credentials Tab ── */}
          {tab === "credentials" && (
            <div className="space-y-4">
              <p className="text-xs text-muted-foreground">
                Export your LinkedIn Sales Navigator session cookies using the{" "}
                <strong>Cookie-Editor</strong> browser extension, then upload the JSON file here.
              </p>

              {hasCredentials && !cookieFile && (
                <div className="flex items-center justify-between p-3 rounded-lg border border-green-500/30 bg-green-500/10">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="size-4 text-green-400" />
                    <span className="text-sm text-green-400 font-medium">Credentials active</span>
                  </div>
                  <button
                    onClick={handleRemoveCookies}
                    className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                  >
                    Remove
                  </button>
                </div>
              )}

              <div
                className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-primary/5 transition-colors"
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  className="hidden"
                  onChange={(e) => handleCookieFile(e.target.files?.[0] ?? null)}
                />
                {cookieFile ? (
                  <div className="flex items-center justify-center gap-2">
                    <FileText className="size-5 text-primary" />
                    <span className="text-sm font-medium">{cookieFile.name}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); setCookieFile(null) }}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <X className="size-4" />
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Upload className="size-8 text-muted-foreground mx-auto" />
                    <p className="text-sm text-muted-foreground">
                      Drop your <code className="text-xs bg-muted px-1 rounded">cookies.json</code> here or{" "}
                      <span className="text-primary underline">browse file</span>
                    </p>
                  </div>
                )}
              </div>

              {credError && (
                <p className="text-sm text-destructive flex items-center gap-1.5">
                  <AlertCircle className="size-4 shrink-0" />
                  {credError}
                </p>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  onClick={handleSaveCookies}
                  disabled={!cookieFile || credLoading}
                  className="h-9 px-4 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {credLoading && <Loader2 className="size-4 animate-spin" />}
                  Save Cookies
                </button>
              </div>
            </div>
          )}

          {/* ── Scrape Tab ── */}
          {tab === "scrape" && (
            <div className="space-y-4">
              {!hasCredentials && (
                <div className="flex items-center gap-2 p-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10">
                  <AlertCircle className="size-4 text-yellow-400 shrink-0" />
                  <p className="text-xs text-yellow-400">
                    No credentials. Go to the{" "}
                    <button className="underline" onClick={() => setTab("credentials")}>Credentials</button>{" "}
                    tab to upload your LinkedIn cookies first.
                  </p>
                </div>
              )}

              {!activeJob ? (
                <>
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-muted-foreground">Search Query</label>
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder='e.g. "CEO fintech Europe" or "VP Sales SaaS"'
                      disabled={!hasCredentials}
                      className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-medium text-muted-foreground">
                      Pages to scrape (~25 leads/page)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={pages}
                      onChange={(e) => setPages(Math.min(10, Math.max(1, parseInt(e.target.value) || 1)))}
                      disabled={!hasCredentials}
                      className="w-24 h-9 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
                    />
                    <p className="text-xs text-muted-foreground">
                      Estimated {pages * 25} leads, takes ~{pages * 10}–{pages * 15}s
                    </p>
                  </div>

                  {scrapeError && (
                    <p className="text-sm text-destructive flex items-center gap-1.5">
                      <AlertCircle className="size-4 shrink-0" />
                      {scrapeError}
                    </p>
                  )}

                  <div className="flex justify-end pt-2 border-t border-border">
                    <button
                      onClick={handleStartScrape}
                      disabled={!hasCredentials || !query.trim() || scrapeLoading}
                      className="h-9 px-4 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                      {scrapeLoading ? (
                        <><Loader2 className="size-4 animate-spin" /> Starting…</>
                      ) : (
                        <><Search className="size-4" /> Start Scraping</>
                      )}
                    </button>
                  </div>
                </>
              ) : (
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border border-border bg-muted/30 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">"{activeJob.query}"</span>
                      {statusBadge(activeJob.status)}
                    </div>

                    {/* Progress bar */}
                    {(activeJob.status === "running" || activeJob.status === "pending") && (
                      <div className="space-y-1">
                        <div className="w-full bg-muted rounded-full h-1.5">
                          <div
                            className="bg-primary h-1.5 rounded-full transition-all duration-500"
                            style={{ width: `${progressPercent(activeJob)}%` }}
                          />
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {activeJob.scraped_count} scraped · {activeJob.leads_created} added to CRM
                        </p>
                      </div>
                    )}

                    {activeJob.status === "completed" && (
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm">
                          <CheckCircle className="size-4 text-green-400" />
                          <span>
                            <strong>{activeJob.leads_created}</strong> leads added to pipeline
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          AI research started automatically for each new lead.
                        </p>
                      </div>
                    )}

                    {activeJob.status === "failed" && (
                      <div className="flex items-start gap-2 text-sm text-destructive">
                        <AlertCircle className="size-4 shrink-0 mt-0.5" />
                        <span>{activeJob.error_message ?? "Scrape failed"}</span>
                      </div>
                    )}
                  </div>

                  {(activeJob.status === "completed" || activeJob.status === "failed") && (
                    <div className="flex justify-end">
                      <button
                        onClick={handleStartAnother}
                        className="h-9 px-4 border border-input bg-background hover:bg-accent rounded-md text-sm font-medium transition-colors"
                      >
                        Start Another
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Suggest Tab ── */}
          {tab === "suggest" && (
            <div className="space-y-4">
              <p className="text-xs text-muted-foreground">
                The AI analyzes your existing leads and suggests targeted LinkedIn Sales Navigator
                search queries to find similar high-intent prospects.
              </p>

              <button
                onClick={handleSuggest}
                disabled={suggestLoading}
                className="w-full h-10 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {suggestLoading ? (
                  <><Loader2 className="size-4 animate-spin" /> Analyzing leads…</>
                ) : (
                  <><Sparkles className="size-4" /> Suggest Search Queries</>
                )}
              </button>

              {suggestError && (
                <p className="text-sm text-destructive flex items-center gap-1.5">
                  <AlertCircle className="size-4 shrink-0" />
                  {suggestError}
                </p>
              )}

              {suggestions.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">
                    {suggestions.length} queries suggested
                  </p>
                  {suggestions.map((s, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg border border-border bg-muted/20 space-y-1.5 hover:border-primary/40 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-0.5">
                          <p className="text-sm font-medium font-mono">{s.query}</p>
                          <p className="text-xs text-muted-foreground">{s.expected_title}</p>
                        </div>
                        <button
                          onClick={() => handleUseQuery(s.query)}
                          className="shrink-0 flex items-center gap-1 h-7 px-2.5 text-xs bg-primary/10 text-primary hover:bg-primary/20 rounded-md transition-colors"
                        >
                          Use <ChevronRight className="size-3" />
                        </button>
                      </div>
                      <p className="text-xs text-muted-foreground">{s.reasoning}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
