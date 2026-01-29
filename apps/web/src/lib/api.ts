/**
 * API client for DevFlow backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface RunCreateRequest {
    feature_request: string;
    repo_path: string;
    base_branch?: string;
    model_profile?: string;
}

export interface RunResponse {
    run_id: string;
    status: RunStatus;
    current_step: string | null;
    progress: number;
    message: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface RunArtifacts {
    run_id: string;
    plan_markdown: string | null;
    checklist_markdown: string | null;
    summary_markdown: string | null;
    diff: string | null;
    raw_events: Record<string, unknown>[];
}

export interface RunListResponse {
    runs: RunResponse[];
    total: number;
    page: number;
    per_page: number;
}

export type RunStatus =
    | 'queued'
    | 'planning'
    | 'checklist'
    | 'executing'
    | 'validating'
    | 'summarizing'
    | 'completed'
    | 'failed'
    | 'cancelled';

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;

        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `API error: ${response.status}`);
        }

        return response.json();
    }

    async healthCheck(): Promise<{ status: string; version: string }> {
        return this.request('/health');
    }

    async createRun(data: RunCreateRequest): Promise<RunResponse> {
        return this.request('/runs', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async listRuns(page = 1, perPage = 20): Promise<RunListResponse> {
        return this.request(`/runs?page=${page}&per_page=${perPage}`);
    }

    async getRun(runId: string): Promise<RunResponse> {
        return this.request(`/runs/${runId}`);
    }

    async getRunArtifacts(runId: string): Promise<RunArtifacts> {
        return this.request(`/runs/${runId}/artifacts`);
    }

    async cancelRun(runId: string): Promise<{ status: string; run_id: string }> {
        return this.request(`/runs/${runId}`, {
            method: 'DELETE',
        });
    }
}

export const api = new ApiClient();
export default api;
