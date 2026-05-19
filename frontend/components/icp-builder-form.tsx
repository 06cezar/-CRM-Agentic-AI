"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Loader2, Sparkles, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { api } from "@/lib/api"

const QUESTIONS = [
  {
    id: "target_persona",
    label: "The Target Persona",
    question: "Who is the exact person that buys this?",
    subtext: "Think about their job title, daily responsibilities, and seniority level.",
    placeholder: "e.g. VPs of Sales at Series B tech companies who manage teams of 20+..."
  },
  {
    id: "target_company",
    label: "The Target Company",
    question: "Describe the companies they work for.",
    subtext: "What industries are they in? How big are they? What tools do they already use?",
    placeholder: "e.g. SaaS companies in Fintech or Healthtech, 50-200 employees, using Salesforce..."
  },
  {
    id: "core_pain",
    label: "The Core Pain",
    question: "What is the bleeding-neck problem they are struggling with?",
    subtext: "What is the specific, expensive problem your product solves? What happens if they don't fix it?",
    placeholder: "e.g. They are losing 30% of pipeline because of manual data entry errors..."
  },
  {
    id: "trigger_event",
    label: "The Trigger Event",
    question: "What makes them buy right now?",
    subtext: "What event happens in their world that makes them actively look for a solution?",
    placeholder: "e.g. They just raised a new round of funding or hired a new Head of Sales..."
  },
  {
    id: "value_proposition",
    label: "The Value Proposition",
    question: "How do you uniquely solve this?",
    subtext: "In your own words, how does your product make their life better?",
    placeholder: "e.g. We automate lead research by combining 10+ data sources into one AI view..."
  }
]

export function ICPBuilderForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(true)
  const [formData, setFormData] = useState({
    target_persona: "",
    target_company: "",
    core_pain: "",
    trigger_event: "",
    value_proposition: ""
  })

  useEffect(() => {
    async function loadICP() {
      try {
        const data = await api.request<any>("/icp/")
        if (data && data.raw_inputs) {
          setFormData(data.raw_inputs)
        }
      } catch (err) {
        console.error("Failed to load ICP:", err)
      } finally {
        setFetching(false)
      }
    }
    loadICP()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate all fields are filled
    const isComplete = Object.values(formData).every(val => val.trim().length > 10)
    if (!isComplete) {
      toast.error("Please provide more detailed answers for all fields.")
      return
    }

    setLoading(true)
    try {
      await api.request("/icp/", {
        method: "POST",
        body: JSON.stringify(formData)
      })
      toast.success("ICP Blueprint saved successfully!", {
        description: "Your ideal customer profile is now active."
      })
      router.refresh()
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to save ICP"
      toast.error("Error saving ICP", { description: msg })
    } finally {
      setLoading(false)
    }
  }

  if (fetching) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="size-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-4xl mx-auto space-y-8 pb-12">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Ideal Customer Profile (ICP) Builder</h1>
          <p className="text-muted-foreground">
            Define your target market in natural language. Our AI will use this to find and rank leads.
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => router.push("/")}
          className="text-muted-foreground hover:text-foreground shrink-0 mt-1"
        >
          <X className="size-4" />
        </Button>
      </div>

      <div className="space-y-10">
        {QUESTIONS.map((q) => (
          <div key={q.id} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor={q.id} className="text-lg font-semibold">
                {q.label}
              </Label>
              <p className="text-sm font-medium text-foreground">
                {q.question}
              </p>
              <p className="text-sm text-muted-foreground">
                {q.subtext}
              </p>
            </div>
            <Textarea
              id={q.id}
              placeholder={q.placeholder}
              className="min-h-[120px] bg-card resize-none text-base p-4"
              value={formData[q.id as keyof typeof formData]}
              onChange={(e) => setFormData(prev => ({ ...prev, [q.id]: e.target.value }))}
              required
            />
          </div>
        ))}
      </div>

      <div className="pt-6 border-t border-border flex justify-end">
        <Button 
          type="submit" 
          size="lg" 
          disabled={loading}
          className="gap-2 px-8"
        >
          {loading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Sparkles className="size-4" />
          )}
          {loading ? "Saving..." : "Save ICP Blueprint"}
        </Button>
      </div>
    </form>
  )
}
