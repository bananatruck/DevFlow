"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import api, { RunResponse, RunArtifacts, RunStatus } from "@/lib/api";

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

const steps = ["planning", "checklist", "executing", "validating", "summarizing", "completed"];

function StepTimeline({ currentStatus }: { currentStatus: RunStatus }) {
    const currentIndex = steps.indexOf(currentStatus);

    return (
        <div className="flex items-center justify-between">
            {steps.map((step, index) => {
                const isCompleted = index < currentIndex || currentStatus === "completed";
                const isCurrent = step === currentStatus;
                const isFailed = currentStatus === "failed" && index === currentIndex;

                return (
                    <div key={step} className="flex items-center flex-1">
                        <div className="relative flex flex-col items-center">
                            <div
                                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all ${isFailed
                                        ? "bg-red-500/20 text-red-500 border-2 border-red-500"
                                        : isCompleted
                                            ? "bg-green-500/20 text-green-500 border-2 border-green-500"
                                            : isCurrent
                                                ? "bg-primary/20 text-primary border-2 border-primary animate-pulse"
                                                : "bg-muted text-muted-foreground border-2 border-muted"
                                    }`}
                            >
                                {isCompleted ? (
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                ) : isFailed ? (
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                ) : (
                                    index + 1
                                )}
                            </div>
                            <span className="absolute -bottom-6 text-xs text-muted-foreground capitalize whitespace-nowrap">
                                {step}
                            </span>
                        </div>
                        {index < steps.length - 1 && (
                            <div
                                className={`flex-1 h-0.5 mx-2 transition-all ${index < currentIndex || currentStatus === "completed"
                                        ? "bg-green-500"
                                        : "bg-muted"
                                    }`}
                            />
                        )}
                    </div>
                );
            })}
        </div>
    );
}

function MarkdownViewer({ content, title }: { content: string | null; title: string }) {
    if (!content) {
        return (
            <div className="flex items-center justify-center h-48 text-muted-foreground">
                <p>No {title.toLowerCase()} available yet</p>
            </div>
        );
    }

    return (
        <div className="prose prose-invert prose-sm max-w-none">
            <pre className="whitespace-pre-wrap bg-muted/50 p-4 rounded-lg text-sm font-mono overflow-auto">
                {content}
            </pre>
        </div>
    );
}

function DiffViewer({ diff }: { diff: string | null }) {
    if (!diff) {
        return (
            <div className="flex items-center justify-center h-48 text-muted-foreground">
                <p>No diff available yet</p>
            </div>
        );
    }

    return (
        <div className="overflow-auto max-h-[600px]">
            <pre className="text-sm font-mono">
                {diff.split("\n").map((line, i) => {
                    let className = "px-4 py-0.5 block";
                    if (line.startsWith("+") && !line.startsWith("+++")) {
                        className += " bg-green-500/10 text-green-400";
                    } else if (line.startsWith("-") && !line.startsWith("---")) {
                        className += " bg-red-500/10 text-red-400";
                    } else if (line.startsWith("@@")) {
                        className += " bg-blue-500/10 text-blue-400";
                    }
                    return (
                        <code key={i} className={className}>
                            {line}
                        </code>
                    );
                })}
            </pre>
        </div>
    );
}

export default function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const router = useRouter();
    const [run, setRun] = useState<RunResponse | null>(null);
    const [artifacts, setArtifacts] = useState<RunArtifacts | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchData() {
            try {
                const [runData, artifactsData] = await Promise.all([
                    api.getRun(id),
                    api.getRunArtifacts(id),
                ]);
                setRun(runData);
                setArtifacts(artifactsData);
            } catch (err) {
                setError(err instanceof Error ? err.message : "Failed to fetch run");
            } finally {
                setLoading(false);
            }
        }

        fetchData();

        // Poll while run is in progress
        const interval = setInterval(async () => {
            try {
                const runData = await api.getRun(id);
                setRun(runData);

                if (["completed", "failed", "cancelled"].includes(runData.status)) {
                    const artifactsData = await api.getRunArtifacts(id);
                    setArtifacts(artifactsData);
                    clearInterval(interval);
                }
            } catch {
                // Ignore polling errors
            }
        }, 3000);

        return () => clearInterval(interval);
    }, [id]);

    if (loading) {
        return (
            <div className="container max-w-screen-xl py-8 px-4">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-muted rounded w-1/4" />
                    <div className="h-4 bg-muted rounded w-1/2" />
                    <div className="h-64 bg-muted rounded" />
                </div>
            </div>
        );
    }

    if (error || !run) {
        return (
            <div className="container max-w-screen-xl py-8 px-4">
                <Card className="border-destructive">
                    <CardContent className="py-8 text-center">
                        <p className="text-destructive">{error || "Run not found"}</p>
                        <Button variant="outline" className="mt-4" onClick={() => router.push("/")}>
                            Back to Dashboard
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="container max-w-screen-xl py-8 px-4 space-y-8">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
                            <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                            Back
                        </Button>
                        <h1 className="text-2xl font-bold font-mono">{run.run_id.slice(0, 8)}</h1>
                        <Badge variant="outline" className={statusColors[run.status]}>
                            {run.status}
                        </Badge>
                    </div>
                    <p className="text-muted-foreground mt-1 ml-16">
                        Created {new Date(run.created_at).toLocaleString()}
                    </p>
                </div>
                {["queued", "planning", "executing"].includes(run.status) && (
                    <Button
                        variant="destructive"
                        size="sm"
                        onClick={async () => {
                            await api.cancelRun(run.run_id);
                            const updated = await api.getRun(run.run_id);
                            setRun(updated);
                        }}
                    >
                        Cancel Run
                    </Button>
                )}
            </div>

            {/* Timeline */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Progress</CardTitle>
                </CardHeader>
                <CardContent className="pb-12">
                    <StepTimeline currentStatus={run.status} />
                </CardContent>
            </Card>

            {/* Artifacts */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Artifacts</CardTitle>
                </CardHeader>
                <CardContent>
                    <Tabs defaultValue="plan">
                        <TabsList className="mb-4">
                            <TabsTrigger value="plan">Plan</TabsTrigger>
                            <TabsTrigger value="checklist">Checklist</TabsTrigger>
                            <TabsTrigger value="summary">Summary</TabsTrigger>
                            <TabsTrigger value="diff">Diff</TabsTrigger>
                        </TabsList>
                        <TabsContent value="plan">
                            <MarkdownViewer content={artifacts?.plan_markdown ?? null} title="Plan" />
                        </TabsContent>
                        <TabsContent value="checklist">
                            <MarkdownViewer content={artifacts?.checklist_markdown ?? null} title="Checklist" />
                        </TabsContent>
                        <TabsContent value="summary">
                            <MarkdownViewer content={artifacts?.summary_markdown ?? null} title="Summary" />
                        </TabsContent>
                        <TabsContent value="diff">
                            <DiffViewer diff={artifacts?.diff ?? null} />
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>
        </div>
    );
}
