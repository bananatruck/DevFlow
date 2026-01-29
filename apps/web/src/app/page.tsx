"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import api, { RunResponse, RunStatus } from "@/lib/api";

const statusColors: Record<RunStatus, string> = {
  queued: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  planning: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  checklist: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  executing: "bg-purple-500/10 text-purple-500 border-purple-500/20",
  validating: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  summarizing: "bg-cyan-500/10 text-cyan-500 border-cyan-500/20",
  completed: "bg-green-500/10 text-green-500 border-green-500/20",
  failed: "bg-red-500/10 text-red-500 border-red-500/20",
  cancelled: "bg-gray-500/10 text-gray-500 border-gray-500/20",
};

const statusLabels: Record<RunStatus, string> = {
  queued: "Queued",
  planning: "Planning",
  checklist: "Checklist",
  executing: "Executing",
  validating: "Validating",
  summarizing: "Summarizing",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function RunCard({ run }: { run: RunResponse }) {
  return (
    <Link href={`/runs/${run.run_id}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer group">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-mono text-sm truncate max-w-[200px]">
              {run.run_id.slice(0, 8)}
            </CardTitle>
            <Badge variant="outline" className={statusColors[run.status]}>
              {statusLabels[run.status]}
            </Badge>
          </div>
          <CardDescription className="text-xs">
            {formatDate(run.created_at)}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {run.progress > 0 && run.progress < 1 && (
              <div className="w-full bg-muted rounded-full h-1.5">
                <div
                  className="bg-primary h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${run.progress * 100}%` }}
                />
              </div>
            )}
            {run.current_step && (
              <p className="text-xs text-muted-foreground">
                Step: <span className="font-medium">{run.current_step}</span>
              </p>
            )}
            {run.message && (
              <p className="text-xs text-muted-foreground truncate">
                {run.message}
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 space-y-4">
      <div className="rounded-full bg-muted p-4">
        <svg
          className="h-8 w-8 text-muted-foreground"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
          />
        </svg>
      </div>
      <div className="text-center">
        <h3 className="text-lg font-semibold">No runs yet</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Create your first DevFlow run to get started
        </p>
      </div>
      <Link href="/runs/new">
        <Button>
          <svg
            className="h-4 w-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          Create New Run
        </Button>
      </Link>
    </div>
  );
}

export default function DashboardPage() {
  const [runs, setRuns] = useState<RunResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchRuns() {
      try {
        const data = await api.listRuns();
        setRuns(data.runs);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch runs");
      } finally {
        setLoading(false);
      }
    }

    fetchRuns();

    // Poll for updates every 5 seconds
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="container max-w-screen-xl py-8 px-4">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Manage your DevFlow agent runs
          </p>
        </div>
        <Link href="/runs/new">
          <Button size="lg">
            <svg
              className="h-4 w-4 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            New Run
          </Button>
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 bg-muted rounded w-1/2" />
                <div className="h-3 bg-muted rounded w-1/4 mt-2" />
              </CardHeader>
              <CardContent>
                <div className="h-2 bg-muted rounded w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card className="border-destructive">
          <CardContent className="py-8 text-center">
            <p className="text-destructive">{error}</p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => window.location.reload()}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : runs.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {runs.map((run) => (
            <RunCard key={run.run_id} run={run} />
          ))}
        </div>
      )}
    </div>
  );
}
