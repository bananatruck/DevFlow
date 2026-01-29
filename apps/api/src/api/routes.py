"""FastAPI routes for the DevFlow API.

Endpoints:
- POST /runs          - Create new agent run
- GET  /runs          - List runs for user
- GET  /runs/{id}     - Get run status
- GET  /runs/{id}/artifacts - Get run artifacts
- GET  /runs/{id}/diff - Get final diff
- DELETE /runs/{id}   - Cancel run

Authentication:
- POST /auth/github   - GitHub OAuth callback
- GET  /auth/me       - Current user info
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.config import get_settings
from src.database.session import get_db
from src.database.models import Run, Artifact, User
from src.schemas import (
    RunCreateRequest,
    RunResponse,
    RunArtifactsResponse,
    RunListResponse,
    RunStatus,
    FeatureRequest,
)
from src.agent.workflow import run_agent


logger = logging.getLogger(__name__)
router = APIRouter()

settings = get_settings()


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
    }


# =============================================================================
# Runs Endpoints
# =============================================================================

@router.post("/runs", response_model=RunResponse)
async def create_run(
    request: RunCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Create a new agent run.
    
    The run will be queued and processed asynchronously.
    Use GET /runs/{run_id} to poll for status updates.
    """
    run_id = str(uuid4())
    
    # Create run record
    run = Run(
        run_id=run_id,
        user_id=1,  # TODO: Get from auth
        repo_path=request.repo_path,
        feature_request=request.feature_request,
        base_branch=request.base_branch,
        status=RunStatus.QUEUED.value,
        model_primary=settings.deepseek_model_chat,
        model_fallback=settings.kimi_model,
        created_at=datetime.utcnow(),
    )
    
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # Queue the run for background processing
    background_tasks.add_task(
        execute_run_task,
        run_id=run_id,
        feature_request=FeatureRequest(
            description=request.feature_request,
            repo_path=request.repo_path,
            base_branch=request.base_branch,
            model_profile=request.model_profile,
        ),
    )
    
    logger.info(f"Created run {run_id}")
    
    return RunResponse(
        run_id=run_id,
        status=RunStatus.QUEUED,
        created_at=run.created_at,
    )


async def execute_run_task(run_id: str, feature_request: FeatureRequest) -> None:
    """Background task to execute an agent run."""
    from src.database.session import get_session
    
    try:
        logger.info(f"Starting execution of run {run_id}")
        
        # Run the agent
        state = await run_agent(feature_request, run_id)
        
        # Update run in database
        async with get_session() as db:
            result = await db.execute(
                select(Run).where(Run.run_id == run_id)
            )
            run = result.scalar_one_or_none()
            
            if run:
                run.status = state.get("status", RunStatus.COMPLETED.value)
                run.ended_at = datetime.utcnow()
                run.success = state.get("status") == RunStatus.COMPLETED.value
                
                # Store artifacts
                if state.get("plan"):
                    artifact = Artifact(
                        run_id=run_id,
                        artifact_type="plan_md",
                        content=state["plan"].to_markdown(),
                    )
                    db.add(artifact)
                
                if state.get("checklist"):
                    artifact = Artifact(
                        run_id=run_id,
                        artifact_type="checklist_md",
                        content=state["checklist"].to_markdown(),
                    )
                    db.add(artifact)
                
                if state.get("summary"):
                    artifact = Artifact(
                        run_id=run_id,
                        artifact_type="summary_md",
                        content=state["summary"].to_markdown(),
                    )
                    db.add(artifact)
                
                await db.commit()
        
        logger.info(f"Completed execution of run {run_id}")
        
    except Exception as e:
        logger.error(f"Error executing run {run_id}: {e}")
        
        # Update run as failed
        async with get_session() as db:
            result = await db.execute(
                select(Run).where(Run.run_id == run_id)
            )
            run = result.scalar_one_or_none()
            if run:
                run.status = RunStatus.FAILED.value
                run.error_message = str(e)
                run.ended_at = datetime.utcnow()
                await db.commit()


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> RunListResponse:
    """List runs for the current user."""
    # TODO: Filter by user from auth
    offset = (page - 1) * per_page
    
    result = await db.execute(
        select(Run)
        .order_by(Run.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    runs = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(select(Run))
    total = len(count_result.scalars().all())
    
    return RunListResponse(
        runs=[
            RunResponse(
                run_id=run.run_id,
                status=RunStatus(run.status),
                current_step=run.current_step,
                progress=run.progress,
                message=run.error_message,
                created_at=run.created_at,
                updated_at=run.ended_at,
            )
            for run in runs
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Get run status by ID."""
    result = await db.execute(
        select(Run).where(Run.run_id == run_id)
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RunResponse(
        run_id=run.run_id,
        status=RunStatus(run.status),
        current_step=run.current_step,
        progress=run.progress,
        message=run.error_message,
        created_at=run.created_at,
        updated_at=run.ended_at,
    )


@router.get("/runs/{run_id}/artifacts", response_model=RunArtifactsResponse)
async def get_run_artifacts(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> RunArtifactsResponse:
    """Get all artifacts from a run."""
    result = await db.execute(
        select(Run).where(Run.run_id == run_id)
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Get artifacts
    artifacts_result = await db.execute(
        select(Artifact).where(Artifact.run_id == run_id)
    )
    artifacts = artifacts_result.scalars().all()
    
    response = RunArtifactsResponse(run_id=run_id)
    
    for artifact in artifacts:
        if artifact.artifact_type == "plan_md":
            response.plan_markdown = artifact.content
        elif artifact.artifact_type == "checklist_md":
            response.checklist_markdown = artifact.content
        elif artifact.artifact_type == "summary_md":
            response.summary_markdown = artifact.content
        elif artifact.artifact_type == "diff":
            response.diff = artifact.content
    
    return response


@router.get("/runs/{run_id}/diff")
async def get_run_diff(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the git diff from a run."""
    result = await db.execute(
        select(Artifact)
        .where(Artifact.run_id == run_id)
        .where(Artifact.artifact_type == "diff")
    )
    artifact = result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Diff not found")
    
    return {"run_id": run_id, "diff": artifact.content}


@router.delete("/runs/{run_id}")
async def cancel_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a running agent run."""
    result = await db.execute(
        select(Run).where(Run.run_id == run_id)
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status not in [RunStatus.QUEUED.value, RunStatus.PLANNING.value, RunStatus.EXECUTING.value]:
        raise HTTPException(status_code=400, detail="Run cannot be cancelled")
    
    run.status = RunStatus.CANCELLED.value
    run.ended_at = datetime.utcnow()
    await db.commit()
    
    return {"status": "cancelled", "run_id": run_id}
