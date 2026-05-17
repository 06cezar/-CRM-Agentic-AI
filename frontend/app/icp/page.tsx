"use client"

import { CommandHeader } from "@/components/command-header"
import { ICPBuilderForm } from "@/components/icp-builder-form"

export default function ICPPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <CommandHeader />
      <main className="flex-1 overflow-y-auto p-6 md:p-10">
        <ICPBuilderForm />
      </main>
    </div>
  )
}
