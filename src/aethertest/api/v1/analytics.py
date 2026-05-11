"""
Analytics endpoints for AetherTest dashboard.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case, Integer, text, cast, String

from src.aethertest.core.database import SessionLocal
from src.aethertest.core.models import SimulationRun, AgentInteraction

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/adoption-rate")
async def get_adoption_rate(
    simulation_id: Optional[str] = None,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get adoption rate (successful interactions / total interactions) over time.
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Base query - using strftime for SQLite compatibility
        hour_expr = func.strftime('%Y-%m-%d %H:00:00', SimulationRun.start_time).label('hour')

        query = db.query(
            hour_expr,
            func.count(AgentInteraction.id).label('total_interactions'),
            func.sum(
                case(
                    (
                        and_(
                            AgentInteraction.action_result['status'].as_integer() >= 200,
                            AgentInteraction.action_result['status'].as_integer() < 300
                        ),
                        1
                    ),
                    else_=0
                )
            ).label('successful_interactions')
        ).join(
            AgentInteraction, SimulationRun.id == AgentInteraction.simulation_id
        ).filter(
            SimulationRun.start_time >= start_time
        )

        if simulation_id:
            query = query.filter(SimulationRun.id == simulation_id)

        # Group by hour
        results = query.group_by(
            hour_expr
        ).order_by(
            hour_expr
        ).all()

        # Format response
        adoption_data = []
        for row in results:
            hour = row.hour
            total = row.total_interactions or 0
            successful = row.successful_interactions or 0
            rate = (successful / total * 100) if total > 0 else 0

            adoption_data.append({
                "timestamp": hour,  # Already formatted as string
                "total_interactions": total,
                "successful_interactions": successful,
                "adoption_rate": round(rate, 2)
            })

        return {
            "adoption_rate": adoption_data,
            "time_range_hours": hours,
            "simulation_id": simulation_id
        }

    except Exception as e:
        logger.error(f"Error getting adoption rate: {e}")
        # Fallback to simpler query if JSON operations fail
        try:
            # Simpler fallback query
            hour_expr = func.strftime('%Y-%m-%d %H:00:00', SimulationRun.start_time).label('hour')
            query = db.query(
                hour_expr,
                func.count(AgentInteraction.id).label('total_interactions')
            ).join(
                AgentInteraction, SimulationRun.id == AgentInteraction.simulation_id
            ).filter(
                SimulationRun.start_time >= start_time
            )

            if simulation_id:
                query = query.filter(SimulationRun.id == simulation_id)

            results = query.group_by(
                hour_expr
            ).order_by(
                hour_expr
            ).all()

            # Return basic data without success rate calculation
            adoption_data = []
            for row in results:
                hour = row.hour
                total = row.total_interactions or 0

                adoption_data.append({
                    "timestamp": hour,
                    "total_interactions": total,
                    "successful_interactions": 0,  # Unknown in fallback
                    "adoption_rate": 0.0
                })

            return {
                "adoption_rate": adoption_data,
                "time_range_hours": hours,
                "simulation_id": simulation_id,
                "note": "Fallback data - success rate calculation unavailable"
            }
        except Exception as fallback_error:
            logger.error(f"Fallback query also failed: {fallback_error}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost-curves")
async def get_cost_curves(
    simulation_id: Optional[str] = None,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get cost curves over time (would need cost field in model).
    For now, returning placeholder structure.
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Base query - in a real implementation, this would use actual cost data
        hour_expr = func.strftime('%Y-%m-%d %H:00:00', SimulationRun.start_time).label('hour')
        query = db.query(
            hour_expr,
            func.count(AgentInteraction.id).label('interactions_count')
        ).join(
            AgentInteraction, SimulationRun.id == AgentInteraction.simulation_id
        ).filter(
            SimulationRun.start_time >= start_time
        )

        if simulation_id:
            query = query.filter(SimulationRun.id == simulation_id)

        # Group by hour
        results = query.group_by(
            hour_expr
        ).order_by(
            hour_expr
        ).all()

        # Format response (placeholder cost calculation)
        cost_data = []
        for row in results:
            hour = row.hour
            interactions = row.interactions_count or 0
            # Placeholder: $0.01 per interaction (would be replaced with real cost calculation)
            estimated_cost = interactions * 0.01

            cost_data.append({
                "timestamp": hour,
                "interactions_count": interactions,
                "estimated_cost": round(estimated_cost, 2),
                "cost_per_interaction": 0.01
            })

        return {
            "cost_curves": cost_data,
            "time_range_hours": hours,
            "simulation_id": simulation_id,
            "note": "Cost calculation is placeholder - implement actual cost tracking in models"
        }

    except Exception as e:
        logger.error(f"Error getting cost curves: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failure-modes")
async def get_failure_modes(
    simulation_id: Optional[str] = None,
    hours: int = 24,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get top failure modes (error types/status codes) over time.
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Query for failed interactions (non-2xx status codes)
        # Using a more compatible approach for different databases
        query = db.query(
            AgentInteraction.action_result['status'].as_string().label('status_code'),
            func.count(AgentInteraction.id).label('failure_count')
        ).join(
            SimulationRun, AgentInteraction.simulation_id == SimulationRun.id
        ).filter(
            SimulationRun.start_time >= start_time
        )

        if simulation_id:
            query = query.filter(SimulationRun.id == simulation_id)

        # Filter for failures (not 2xx status) - handled in processing for compatibility
        results = query.group_by(
            AgentInteraction.action_result['status'].as_string()
        ).order_by(
            desc(func.count(AgentInteraction.id))
        ).limit(limit).all()

        # Format response
        failure_data = []
        total_failures = 0
        for row in results:
            status_code = row.status_code
            failure_count = row.failure_count or 0

            # Check if this is actually a failure (non-2xx)
            try:
                code = int(status_code) if status_code else None
                is_failure = code is None or not (200 <= code < 300)
            except ValueError:
                is_failure = True  # Non-numeric status is considered failure

            if is_failure:
                failure_data.append({
                    "status_code": status_code,
                    "failure_count": failure_count,
                    "failure_type": _get_failure_type(status_code)
                })
                total_failures += failure_count

        return {
            "failure_modes": failure_data,
            "time_range_hours": hours,
            "simulation_id": simulation_id,
            "total_failures": total_failures
        }

    except Exception as e:
        logger.error(f"Error getting failure modes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/successful-strategies")
async def get_successful_strategies(
    simulation_id: Optional[str] = None,
    hours: int = 24,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get most successful agent strategies based on successful interactions.
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Query for successful interactions with agent details
        # Using compatible approach
        query = db.query(
            AgentInteraction.agent_id,
            AgentInteraction.agent_type,
            AgentInteraction.persona_name,
            func.count(AgentInteraction.id).label('success_count')
        ).join(
            SimulationRun, AgentInteraction.simulation_id == SimulationRun.id
        ).filter(
            SimulationRun.start_time >= start_time
        )

        if simulation_id:
            query = query.filter(SimulationRun.id == simulation_id)

        # Filter for successes (2xx status)
        query = query.filter(
            AgentInteraction.action_result['status'].as_integer() >= 200,
            AgentInteraction.action_result['status'].as_integer() < 300
        )

        # Group by agent details and order by success count
        results = query.group_by(
            AgentInteraction.agent_id,
            AgentInteraction.agent_type,
            AgentInteraction.persona_name
        ).order_by(
            desc(func.count(AgentInteraction.id))
        ).limit(limit).all()

        # Format response
        strategies_data = []
        total_successful = 0
        for row in results:
            strategies_data.append({
                "agent_id": row.agent_id,
                "agent_type": row.agent_type,
                "persona_name": row.persona_name,
                "successful_interactions": row.success_count
            })
            total_successful += row.success_count

        return {
            "successful_strategies": strategies_data,
            "time_range_hours": hours,
            "simulation_id": simulation_id,
            "total_successful_interactions": total_successful
        }

    except Exception as e:
        logger.error(f"Error getting successful strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visual-replay/{simulation_id}")
async def get_visual_replay(
    simulation_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get detailed interaction data for visual replay of a simulation.
    """
    try:
        # Verify simulation exists
        simulation = db.query(SimulationRun).filter(SimulationRun.id == simulation_id).first()
        if not simulation:
            raise HTTPException(status_code=404, detail="Simulation not found")

        # Get interactions for this simulation, ordered by timestamp
        interactions = db.query(AgentInteraction).filter(
            AgentInteraction.simulation_id == simulation_id
        ).order_by(
            AgentInteraction.timestamp
        ).limit(limit).all()

        # Format response for visual replay
        replay_data = []
        for interaction in interactions:
            replay_data.append({
                "id": interaction.id,
                "agent_id": interaction.agent_id,
                "agent_type": interaction.agent_type,
                "persona_name": interaction.persona_name,
                "interaction_number": interaction.interaction_number,
                "timestamp": interaction.timestamp.isoformat() if interaction.timestamp else None,
                "action_taken": interaction.action_taken,
                "action_result": interaction.action_result,
                "reflection": interaction.reflection,
                "duration_ms": interaction.duration_ms
            })

        return {
            "simulation": {
                "id": simulation.id,
                "api_endpoint": simulation.api_endpoint,
                "start_time": simulation.start_time.isoformat() if simulation.start_time else None,
                "end_time": simulation.end_time.isoformat() if simulation.end_time else None,
                "status": simulation.status,
                "total_interactions": simulation.total_interactions,
                "successful_interactions": simulation.successful_interactions,
                "failed_interactions": simulation.failed_interactions
            },
            "interactions": replay_data,
            "total_interactions_returned": len(replay_data)
        }

    except Exception as e:
        logger.error(f"Error getting visual replay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_failure_type(status_code: Optional[str]) -> str:
    """Convert status code to failure type description."""
    if not status_code:
        return "Unknown Error"

    try:
        code = int(status_code)
        if 400 <= code < 500:
            return f"Client Error {code}"
        elif 500 <= code < 600:
            return f"Server Error {code}"
        elif code == 408:
            return "Request Timeout"
        elif code == 429:
            return "Rate Limited"
        elif code == 503:
            return "Service Unavailable"
        else:
            return f"HTTP Error {code}"
    except ValueError:
        return f"Non-HTTP Error: {status_code}"