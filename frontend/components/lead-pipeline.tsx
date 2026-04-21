"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  TrendingUp,
  Building2,
  Flame,
  Zap,
  Snowflake,
  ArrowUpRight,
} from "lucide-react";
import { getLeads } from "@/lib/leads";

export interface Lead {
  id: string;
  name: string;
  company: string;
  score: number;
  status?: string;
  value: string;
  lastActivity: string;
  signals: string[];
  email: string;
  phone: string;
  role: string;
  winningArgument: string;
  draftMessage: string;
}

export interface LeadPipelineProps {
  selectedLead: Lead | null;
  onSelectLead: (lead: Lead) => void;
}

export function LeadPipeline({
  selectedLead,
  onSelectLead,
}: LeadPipelineProps) {
  const [filter, setFilter] = useState<"all" | "hot" | "warm" | "cool">("all");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    getLeads()
      .then((data) => {
        if (!mounted) return;
        // Strict mapping: use API-provided fields and avoid overwriting with defaults
        const transformedLeads = (data ?? []).map((lead: any) => ({
          ...lead,
          id: lead.id,
          name: lead.name,
          company: lead.company,
          // force numeric score from intent_score (but do not default to 0 if missing)
          score:
            lead.intent_score !== undefined
              ? Number(lead.intent_score)
              : lead.score,
          // use API status as-is (lowercase if present)
          status: lead.status ? String(lead.status).toLowerCase() : lead.status,
          // map deal_value directly
          value: lead.deal_value ?? lead.value,
          // ensure arrays/strings exist to avoid runtime errors in detail view
          signals: lead.signals ?? [],
          lastActivity: lead.lastActivity ?? lead.last_activity ?? "",
          winningArgument: lead.winningArgument ?? lead.winning_argument ?? "",
          draftMessage: lead.draftMessage ?? lead.draft_message ?? "",
          role: lead.role ?? "",
          email: lead.email ?? "",
          phone: lead.phone ?? "",
        })) as Lead[];

        setLeads(transformedLeads);
      })
      .catch((err) => console.error("Failed loading leads", err))
      .finally(() => mounted && setLoading(false));

    return () => {
      mounted = false;
    };
  }, []);

  const filteredLeads = leads.filter((lead) => {
    if (filter === "all") return true;
    if (filter === "hot") return lead.status === "hot";
    if (filter === "warm") return lead.status === "warm";
    return lead.status === "cool";
  });

  const stats = {
    hot: leads.filter((l) => l.status === "hot").length,
    warm: leads.filter((l) => l.status === "warm").length,
    cool: leads.filter((l) => l.status === "cool").length,
  };

  function getScoreColor(statusOrScore: string | number) {
    if (typeof statusOrScore === "string") {
      if (statusOrScore === "hot") return "text-score-hot";
      if (statusOrScore === "warm") return "text-score-warm";
      return "text-score-cool";
    }
    const score = Number(statusOrScore);
    if (score >= 80) return "text-score-hot";
    if (score >= 60) return "text-score-warm";
    return "text-score-cool";
  }

  function getScoreBg(statusOrScore: string | number) {
    if (typeof statusOrScore === "string") {
      if (statusOrScore === "hot") return "bg-score-hot/10 border-score-hot/30";
      if (statusOrScore === "warm")
        return "bg-score-warm/10 border-score-warm/30";
      return "bg-score-cool/10 border-score-cool/30";
    }
    const score = Number(statusOrScore);
    if (score >= 80) return "bg-score-hot/10 border-score-hot/30";
    if (score >= 60) return "bg-score-warm/10 border-score-warm/30";
    return "bg-score-cool/10 border-score-cool/30";
  }

  function getScoreIcon(statusOrScore: string | number) {
    if (typeof statusOrScore === "string") {
      if (statusOrScore === "hot") return Flame;
      if (statusOrScore === "warm") return Zap;
      return Snowflake;
    }
    const score = Number(statusOrScore);
    if (score >= 80) return Flame;
    if (score >= 60) return Zap;
    return Snowflake;
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary/10">
              <TrendingUp className="size-4 text-primary" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">
                Intent Pipeline
              </h2>
              <p className="text-xs text-muted-foreground">
                Sorted by closing probability
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs">
            <span className="font-mono text-foreground">{leads.length}</span>
            <span className="text-muted-foreground">leads</span>
          </div>
        </div>

        {/* Score filter tabs */}
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => setFilter("all")}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              filter === "all"
                ? "bg-secondary text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            All
          </button>
          <button
            onClick={() => setFilter("hot")}
            className={cn(
              "flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              filter === "hot"
                ? "bg-score-hot/20 text-score-hot"
                : "text-muted-foreground hover:text-score-hot",
            )}
          >
            <Flame className="size-3" />
            Hot ({stats.hot})
          </button>
          <button
            onClick={() => setFilter("warm")}
            className={cn(
              "flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              filter === "warm"
                ? "bg-score-warm/20 text-score-warm"
                : "text-muted-foreground hover:text-score-warm",
            )}
          >
            <Zap className="size-3" />
            Warm ({stats.warm})
          </button>
          <button
            onClick={() => setFilter("cool")}
            className={cn(
              "flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              filter === "cool"
                ? "bg-score-cool/20 text-score-cool"
                : "text-muted-foreground hover:text-score-cool",
            )}
          >
            <Snowflake className="size-3" />
            Cool ({stats.cool})
          </button>
        </div>
      </div>

      {/* Lead list */}
      <ScrollArea className="flex-1">
        <div className="space-y-1 p-2">
          {loading && leads.length === 0 ? (
            <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
              Loading leads…
            </div>
          ) : (
            <>
              {filteredLeads.map((lead) => {
                const ScoreIcon = getScoreIcon(lead.status ?? lead.score);
                const isSelected = selectedLead?.id === lead.id;

                return (
                  <button
                    key={lead.id}
                    onClick={() => onSelectLead(lead)}
                    className={cn(
                      "w-full rounded-lg p-3 text-left transition-all",
                      isSelected
                        ? "bg-primary/10 border border-primary/30"
                        : "hover:bg-accent/50 border border-transparent",
                    )}
                  >
                    <div className="flex items-start gap-3">
                      {/* Score indicator */}
                      <div
                        className={cn(
                          "flex size-10 shrink-0 items-center justify-center rounded-lg border",
                          getScoreBg(lead.status ?? lead.score),
                        )}
                      >
                        <ScoreIcon
                          className={cn(
                            "size-5",
                            getScoreColor(lead.status ?? lead.score),
                          )}
                        />
                      </div>

                      {/* Lead info */}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-foreground truncate">
                            {lead.name}
                          </span>
                          <span
                            className={cn(
                              "font-mono text-sm font-bold",
                              getScoreColor(lead.status ?? lead.score),
                            )}
                          >
                            {lead.score}%
                          </span>
                        </div>
                        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Building2 className="size-3" />
                          <span className="truncate">{lead.company}</span>
                          <span className="text-muted-foreground/50">•</span>
                          <span className="text-primary font-medium">
                            {lead.value}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground truncate">
                          {lead.lastActivity}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {(lead.signals ?? []).map((signal) => (
                            <Badge
                              key={signal}
                              variant="outline"
                              className="text-[10px] px-1.5 py-0 h-5 border-border/50"
                            >
                              {signal}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      {/* Arrow indicator */}
                      <ArrowUpRight
                        className={cn(
                          "size-4 shrink-0 transition-all",
                          isSelected
                            ? "text-primary translate-x-0.5 -translate-y-0.5"
                            : "text-muted-foreground/50",
                        )}
                      />
                    </div>
                  </button>
                );
              })}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

export {};
