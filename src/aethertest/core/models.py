"""
SQLAlchemy models for AetherTest analytics.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

Base = declarative_base()


class SimulationRun(Base):
    """
    Metadata about a simulation run.
    """
    __tablename__ = 'simulation_runs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    api_endpoint = Column(String(255), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), default='created', nullable=False)  # created, running, completed, failed
    config = Column(JSON, nullable=False)  # Store the simulation configuration
    total_interactions = Column(Integer, default=0)
    successful_interactions = Column(Integer, default=0)
    failed_interactions = Column(Integer, default=0)

    # Relationship to interactions
    interactions = relationship("AgentInteraction", back_populates="simulation", cascade="all, delete-orphan")


class AgentInteraction(Base):
    """
    Record of a single agent interaction during a simulation.
    """
    __tablename__ = 'agent_interactions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    simulation_id = Column(String(36), ForeignKey('simulation_runs.id'), nullable=False)
    agent_id = Column(String(255), nullable=False)
    agent_type = Column(String(100), nullable=False)  # e.g., 'synthetic', 'api_user', etc.
    persona_name = Column(String(255), nullable=True)  # For synthetic agents
    interaction_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action_taken = Column(JSON, nullable=False)  # The action decision
    action_result = Column(JSON, nullable=False)  # The result of the action
    reflection = Column(JSON, nullable=True)  # The reflection output
    duration_ms = Column(Float, nullable=True)

    # Relationship back to simulation
    simulation = relationship("SimulationRun", back_populates="interactions")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_agent_interaction_simulation_id', 'simulation_id'),
        Index('idx_agent_interaction_timestamp', 'timestamp'),
    )