"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import api from "@/lib/api";

export default function NewRunPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState({
        feature_request: "",
        repo_path: "",
        base_branch: "main",
        model_profile: "default",
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const run = await api.createRun(formData);
            router.push(`/runs/${run.run_id}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create run");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container max-w-screen-md py-8 px-4">
            <div className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight">Create New Run</h1>
                <p className="text-muted-foreground mt-1">
                    Start a new DevFlow agent run to implement a feature
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Feature Request</CardTitle>
                    <CardDescription>
                        Describe the feature or change you want the agent to implement
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium" htmlFor="feature_request">
                                Description
                            </label>
                            <Textarea
                                id="feature_request"
                                placeholder="Add retry limit to webhook processor..."
                                rows={4}
                                value={formData.feature_request}
                                onChange={(e) =>
                                    setFormData({ ...formData, feature_request: e.target.value })
                                }
                                required
                                className="resize-none"
                            />
                            <p className="text-xs text-muted-foreground">
                                Be specific about what you want to achieve. Include any constraints or requirements.
                            </p>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium" htmlFor="repo_path">
                                Repository Path
                            </label>
                            <Input
                                id="repo_path"
                                placeholder="/home/user/projects/my-app"
                                value={formData.repo_path}
                                onChange={(e) =>
                                    setFormData({ ...formData, repo_path: e.target.value })
                                }
                                required
                            />
                            <p className="text-xs text-muted-foreground">
                                Local path to the repository where changes will be made
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium" htmlFor="base_branch">
                                    Base Branch
                                </label>
                                <Input
                                    id="base_branch"
                                    placeholder="main"
                                    value={formData.base_branch}
                                    onChange={(e) =>
                                        setFormData({ ...formData, base_branch: e.target.value })
                                    }
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium">Model Profile</label>
                                <Select
                                    value={formData.model_profile}
                                    onValueChange={(value) =>
                                        setFormData({ ...formData, model_profile: value })
                                    }
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select profile" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="default">Default (Balanced)</SelectItem>
                                        <SelectItem value="fast">Fast (DeepSeek Chat)</SelectItem>
                                        <SelectItem value="quality">Quality (Reasoner)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {error && (
                            <div className="p-3 text-sm bg-destructive/10 text-destructive rounded-lg">
                                {error}
                            </div>
                        )}

                        <div className="flex gap-3">
                            <Button type="submit" disabled={loading} className="flex-1">
                                {loading ? (
                                    <>
                                        <svg
                                            className="animate-spin h-4 w-4 mr-2"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                        >
                                            <circle
                                                className="opacity-25"
                                                cx="12"
                                                cy="12"
                                                r="10"
                                                stroke="currentColor"
                                                strokeWidth="4"
                                            />
                                            <path
                                                className="opacity-75"
                                                fill="currentColor"
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                            />
                                        </svg>
                                        Creating Run...
                                    </>
                                ) : (
                                    <>
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
                                                d="M13 10V3L4 14h7v7l9-11h-7z"
                                            />
                                        </svg>
                                        Start Run
                                    </>
                                )}
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => router.push("/")}
                            >
                                Cancel
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}
