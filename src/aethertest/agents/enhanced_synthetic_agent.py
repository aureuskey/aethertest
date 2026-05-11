"""
Enhanced SyntheticAgent class representing infrastructure-realistic users.
Implements sophisticated behaviors for testing infrastructure APIs:
- Multi-step stateful workflows (auth → operation → validation → cleanup)
- Proper authentication & token/session management (handle 401 → refresh)
- Adaptive error handling with retry strategies
- Rate limit awareness
- Persona-driven behavior with distinct decision-making
- Semantic response validation
- Self-instrumentation with structured logging
- Resource lifecycle awareness (CRUD patterns, idempotency, partial failures)
"""
from typing import Dict, Any, Optional, List, Callable
import json
import time
import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .enhanced_base_agent import (
    EnhancedBaseAgent,
    WorkflowStep,
    WorkflowResult,
    ErrorType,
    RetryConfig,
    RetryStrategy,
    SessionState,
)
from .synthetic_agent import AgentPersona

logger = logging.getLogger(__name__)


class WorkflowType(Enum):
    """Types of workflows that infrastructure users might perform."""
    AUTHENTICATE_AND_OPERATE = "authenticate_and_operate"
    RESOURCE_LIFECYCLE = "resource_lifecycle"  # CRUD operations
    HEALTH_CHECK = "health_check"
    BATCH_PROCESSING = "batch_processing"
    CONFIGURATION_UPDATE = "configuration_update"
    DATA_PIPELINE = "data_pipeline"


@dataclass
class InfrastructureWorkflow:
    """A predefined workflow for infrastructure testing."""
    name: str
    workflow_type: WorkflowType
    steps: List[WorkflowStep]
    description: str
    # Optional: probability of selecting this workflow based on persona
    base_weight: float = 1.0


class EnhancedSyntheticAgent(EnhancedBaseAgent):
    """
    Enhanced synthetic agent that behaves like an infrastructure user.
    Implements sophisticated behaviors for realistic API testing.
    """

    def __init__(
        self,
        agent_id: str,
        api_endpoint: str,
        api_key: Optional[str] = None,
        persona: Optional[AgentPersona] = None,
        anthropic_api_key: Optional[str] = None,
        workflow_library: Optional[List[InfrastructureWorkflow]] = None,
        endpoint_config: Optional[Dict[str, str]] = None,
    ):
        # Initialize enhanced base agent
        super().__init__(agent_id, api_endpoint, api_key)

        self.persona = persona or self._default_persona()
        self.anthropic_api_key = anthropic_api_key
        self.anthropic_client = None

        if ANTHROPIC_AVAILABLE and anthropic_api_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")

        # Memory systems (retained from original for learning)
        self.short_term_memory: List[Dict[str, Any]] = []
        self.long_term_memory: List[Dict[str, Any]] = []
        self.max_short_term = 10
        self.max_long_term = 100

        # Endpoint configuration for flexible API endpoints
        self.endpoint_config = endpoint_config or {}

        # Workflow library
        self.workflow_library = workflow_library or self._create_default_workflow_library()

        # Track recent workflows for variety
        self.recent_workflows: List[str] = []
        self.max_recent_workflows = 5

        # Infrastructure-specific state
        self.infrastructure_state = {
            "last_auth_time": 0,
            "auth_method": None,
            "discovered_endpoints": set(),
            "failed_endpoints": set(),
            "rate_limited_endpoints": set(),
            "successful_patterns": [],
            "failed_patterns": [],
        }

        # Self-instrumentation for structured logging
        self.interaction_log: List[Dict[str, Any]] = []

        # Set logger to DEBUG to see detailed logs
        logger.setLevel(logging.DEBUG)
        # Set logger for base agent to DEBUG as well
        from src.aethertest.agents.enhanced_base_agent import logger as base_logger
        base_logger.setLevel(logging.DEBUG)

        logger.info(
            f"Initialized EnhancedSyntheticAgent {agent_id} "
            f"with persona {self.persona.name}"
        )

    def _default_persona(self) -> AgentPersona:
        """Create a default generic persona."""
        return AgentPersona(
            name="Infrastructure Tester",
            description="A generic infrastructure tester",
            goals=["Discover API capabilities", "Test reliability", "Measure performance"],
            budget=100.0,
            risk_tolerance=0.5,
            technical_expertise=0.5,
            communication_style="technical",
        )

    # ============================================================================
    # WORKFLOW LIBRARY - Predefined infrastructure-realistic workflows
    # ============================================================================

    def _create_default_workflow_library(self) -> List[InfrastructureWorkflow]:
        """Create a library of common infrastructure workflows."""
        workflows = []

        # 1. Authentication workflow
        auth_workflow = InfrastructureWorkflow(
            name="Bearer Token Auth",
            workflow_type=WorkflowType.AUTHENTICATE_AND_OPERATE,
            description="Authenticate with bearer token, then access protected resource",
            steps=[
                WorkflowStep(
                    name="auth_login",
                    method="POST",
                    endpoint=self._resolve_endpoint("{auth_login}"),
                    data={  # Will be filled by persona
                        "username": "{{username}}",
                        "password": "{{password}}"
                    },
                    expected_status=[200, 201],
                    extract_data=self._extract_auth_token,
                    critical=True,
                ),
                WorkflowStep(
                    name="access_protected_resource",
                    method="GET",
                    endpoint=self._resolve_endpoint("{resource_base}"),
                    expected_status=[200],
                    validate_response=self._validate_resource_data,
                    critical=True,
                ),
            ],
            base_weight=1.0,
        )
        workflows.append(auth_workflow)

        # 2. API Key workflow
        api_key_workflow = InfrastructureWorkflow(
            name="API Key Auth",
            workflow_type=WorkflowType.AUTHENTICATE_AND_OPERATE,
            description="Use API key header to access resources",
            steps=[
                WorkflowStep(
                    name="set_api_key_header",
                    method="GET",
                    endpoint=self._resolve_endpoint("{resource_base}"),
                    expected_status=[200],
                    # Headers handled by session
                ),
            ],
            base_weight=0.8,
        )
        workflows.append(api_key_workflow)

        # 3. Resource lifecycle workflow (CRUD)
        resource_lifecycle_workflow = InfrastructureWorkflow(
            name="Resource Lifecycle",
            workflow_type=WorkflowType.RESOURCE_LIFECYCLE,
            description="Create, read, update, delete a resource",
            steps=[
                WorkflowStep(
                    name="create_resource",
                    method="POST",
                    endpoint=self._resolve_endpoint("{resource_base}"),
                    data={
                        "name": "{{resource_name}}",
                        "description": "{{resource_description}}",
                        "tags": ["test", "infrastructure"]
                    },
                    expected_status=[201],
                    extract_data=self._extract_resource_id,
                    critical=True,
                ),
                WorkflowStep(
                    name="read_resource",
                    method="GET",
                    endpoint=self._resolve_endpoint("{resource_base}") + "/{{resource_id}}",
                    expected_status=[200],
                    validate_response=self._validate_resource_data,
                    critical=True,
                ),
                WorkflowStep(
                    name="update_resource",
                    method="PATCH",
                    endpoint=self._resolve_endpoint("{resource_base}") + "/{{resource_id}}",
                    data={
                        "description": "{{updated_description}}",
                        "updated_at": "{{timestamp}}"
                    },
                    expected_status=[200, 204],
                    critical=True,
                ),
                WorkflowStep(
                    name="delete_resource",
                    method="DELETE",
                    endpoint=self._resolve_endpoint("{resource_base}") + "/{{resource_id}}",
                    expected_status=[200, 204],
                    critical=True,
                ),
            ],
            base_weight=1.2,
        )
        workflows.append(resource_lifecycle_workflow)

        # 4. Health check workflow
        health_check_workflow = InfrastructureWorkflow(
            name="Health Check",
            workflow_type=WorkflowType.HEALTH_CHECK,
            description="Check API health and performance",
            steps=[
                WorkflowStep(
                    name="health_endpoint",
                    method="GET",
                    endpoint="/health",
                    expected_status=[200],
                    validate_response=self._validate_health_response,
                ),
                WorkflowStep(
                    name="metrics_endpoint",
                    method="GET",
                    endpoint="/metrics",
                    expected_status=[200],
                    validate_response=self._validate_metrics_response,
                ),
                WorkflowStep(
                    name="version_endpoint",
                    method="GET",
                    endpoint="/version",
                    expected_status=[200],
                    validate_response=self._validate_version_response,
                ),
            ],
            base_weight=0.5,
        )
        workflows.append(health_check_workflow)

        # 5. Batch processing workflow
        batch_workflow = InfrastructureWorkflow(
            name="Batch Processing",
            workflow_type=WorkflowType.BATCH_PROCESSING,
            description="Submit a batch job and check its status",
            steps=[
                WorkflowStep(
                    name="submit_batch",
                    method="POST",
                    endpoint=self._resolve_endpoint("{batch_submit}"),
                    data={
                        "operation": "{{batch_operation}}",
                        "items": "{{batch_items}}",
                        "priority": "{{priority}}"
                    },
                    expected_status=[200, 202],
                    extract_data=self._extract_batch_id,
                    critical=True,
                ),
                WorkflowStep(
                    name="check_batch_status",
                    method="GET",
                    endpoint=self._resolve_endpoint("{batch_submit}") + "/{{batch_id}}",
                    expected_status=[200],
                    validate_response=self._validate_batch_status,
                    # This might be retried several times
                    retry_config=RetryConfig(
                        max_attempts=5,
                        base_delay=2.0,
                        max_delay=30.0,
                    ),
                    critical=True,
                ),
            ],
            base_weight=0.8,
        )
        workflows.append(batch_workflow)

        # 6. Configuration workflow
        config_workflow = InfrastructureWorkflow(
            name="Configuration Update",
            workflow_type=WorkflowType.CONFIGURATION_UPDATE,
            description="Get current config, update it, verify change",
            steps=[
                WorkflowStep(
                    name="get_config",
                    method="GET",
                    endpoint=self._resolve_endpoint("{config_get}"),
                    expected_status=[200],
                    extract_data=self._extract_config,
                    critical=True,
                ),
                WorkflowStep(
                    name="update_config",
                    method="PUT",
                    endpoint=self._resolve_endpoint("{config_update}"),
                    data={
                        "setting": "{{config_setting}}",
                        "value": "{{config_value}}",
                        "updated_by": "{{user_id}}"
                    },
                    expected_status=[200],
                    critical=True,
                ),
                WorkflowStep(
                    name="verify_config_update",
                    method="GET",
                    endpoint=self._resolve_endpoint("{config_get}") + "/{{config_setting}}",
                    expected_status=[200],
                    validate_response=self._validate_config_update,
                    critical=True,
                ),
            ],
            base_weight=0.6,
        )
        workflows.append(config_workflow)

        # 7. Data pipeline workflow
        pipeline_workflow = InfrastructureWorkflow(
            name="Data Pipeline",
            workflow_type=WorkflowType.DATA_PIPELINE,
            description="Ingest data, process it, retrieve results",
            steps=[
                WorkflowStep(
                    name="ingest_data",
                    method="POST",
                    endpoint=self._resolve_endpoint("{ingest}"),
                    data={
                        "data_source": "{{data_source}}",
                        "format": "{{data_format}}",
                        "records": "{{record_count}}"
                    },
                    expected_status=[200, 202],
                    extract_data=self._extract_ingest_id,
                    critical=True,
                ),
                WorkflowStep(
                    name="check_processing_status",
                    method="GET",
                    endpoint=self._resolve_endpoint("{process_status}") + "/{{ingest_id}}",
                    expected_status=[200],
                    validate_response=self._validate_processing_status,
                    retry_config=RetryConfig(
                        max_attempts=10,
                        base_delay=3.0,
                        max_delay=60.0,
                    ),
                    critical=True,
                ),
                WorkflowStep(
                    name="retrieve_results",
                    method="GET",
                    endpoint=self._resolve_endpoint("{results_get}") + "/{{ingest_id}}",
                    expected_status=[200],
                    validate_response=self._validate_results_exist,
                    critical=True,
                ),
            ],
            base_weight=0.7,
        )
        workflows.append(pipeline_workflow)

        return workflows

    # ============================================================================
    # DATA EXTRACTION AND VALIDATION HELPERS
    # ============================================================================

    def _extract_auth_token(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract authentication token from login response."""
        logger.debug(f"[{self.agent_id}] Extracting auth token from data keys: {list(data.keys())}")
        result = {}
        # Common token field names
        token_fields = ["token", "access_token", "authToken", "jwt", "id_token"]
        for field in token_fields:
            if field in data:
                result["auth_token"] = data[field]
                break

        # Extract expiration if present
        if "expires_in" in data:
            try:
                expires_in = int(data["expires_in"])
                result["token_expires"] = time.time() + expires_in
            except (ValueError, TypeError):
                pass
        elif "expires_at" in data:
            try:
                result["token_expires"] = float(data["expires_at"])
            except (ValueError, TypeError):
                pass

        # Extract refresh token
        refresh_fields = ["refresh_token", "refreshToken"]
        for field in refresh_fields:
            if field in data:
                result["refresh_token"] = data[field]
                break

        logger.debug(f"[{self.agent_id}] Extracted token: {result.get('auth_token', '')[:10] if result.get('auth_token') else None}..., expires: {result.get('token_expires')}")
        return result

    def _extract_resource_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract resource ID from creation response."""
        result = {}
        for id_field in ["id", "ID", "_id", "resourceId", "resource_id"]:
            if id_field in data:
                result["resource_id"] = data[id_field]
                break
        return result

    def _extract_batch_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract batch ID from batch submission response."""
        result = {}
        for id_field in ["id", "batchId", "batch_id", "jobId"]:
            if id_field in data:
                result["batch_id"] = data[id_field]
                break
        return result

    def _extract_ingest_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ingest ID from data ingestion response."""
        result = {}
        for id_field in ["id", "ingestId", "ingest_id", "jobId"]:
            if id_field in data:
                result["ingest_id"] = data[id_field]
                break
        return result

    def _extract_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract configuration data."""
        # Just pass through - the whole config might be useful
        return {"config": data} if data else {}

    # ============================================================================
    # VALIDATION FUNCTIONS
    # ============================================================================

    def _validate_user_profile(self, data: Dict[str, Any]) -> bool:
        """Validate that user profile response contains expected fields."""
        required_fields = ["id", "username", "email"]
        return all(field in data for field in required_fields)

    def _validate_resource_data(self, data: Dict[str, Any]) -> bool:
        """Validate that resource data matches what we expect."""
        # At minimum, should have an id
        return "id" in data

    def _validate_health_response(self, data: Dict[str, Any]) -> bool:
        """Validate health check response."""
        # Most health endpoints return {"status": "ok"} or similar
        return "status" in data and data["status"] in ["ok", "healthy", "up"]

    def _validate_metrics_response(self, data: Dict[str, Any]) -> bool:
        """Validate metrics response."""
        # Should have some metric data
        return isinstance(data, dict) and len(data) > 0

    def _validate_version_response(self, data: Dict[str, Any]) -> bool:
        """Validate version response."""
        return "version" in data or "release" in data

    def _validate_batch_status(self, data: Dict[str, Any]) -> bool:
        """Validate batch status response."""
        # Should indicate the batch is processed or processing
        status = data.get("status", "").lower()
        return status in ["completed", "processed", "finished", "processing", "running"]

    def _validate_config_update(self, data: Dict[str, Any]) -> bool:
        """Validate that config was updated correctly."""
        # Should reflect the updated value
        setting = self.workflow_variables.get("config_setting")
        if setting and setting in data:
            expected_value = self.workflow_variables.get("config_value")
            if expected_value is not None:
                return data[setting] == expected_value
        return True  # If we can't validate, assume it worked

    def _validate_processing_status(self, data: Dict[str, Any]) -> bool:
        """Validate data processing status."""
        status = data.get("status", "").lower()
        return status in ["completed", "finished", "processed", "ready"]

    def _validate_results_exist(self, data: Dict[str, Any]) -> bool:
        """Validate that results exist and are accessible."""
        # Could be a list, or have a results field
        if isinstance(data, list):
            return len(data) > 0
        if isinstance(data, dict):
            return ("results" in data and len(data["results"]) > 0) or \
                   ("data" in data and len(data["data"]) > 0) or \
                   len(data) > 0
        return False

    # ============================================================================
    # PERSONA-DRIVEN BEHAVIOR
    # ============================================================================

    def _select_workflow_based_on_persona(self) -> InfrastructureWorkflow:
        """
        Select a workflow based on persona characteristics.
        Different personas prefer different types of workflows.
        """
        # Calculate weights for each workflow based on persona
        weighted_workflows = []

        for workflow in self.workflow_library:
            weight = workflow.base_weight

            # Adjust weight based on persona traits
            if self.persona.name == "Cautious DevOps Engineer":
                # Prefer health checks, configuration, reliable workflows
                if workflow.workflow_type in [WorkflowType.HEALTH_CHECK,
                                            WorkflowType.CONFIGURATION_UPDATE]:
                    weight *= 1.5
                # Avoid overly aggressive workflows
                elif workflow.workflow_type == WorkflowType.BATCH_PROCESSING:
                    weight *= 0.7

            elif self.persona.name == "Aggressive Startup Founder":
                # Prefer batch processing, data pipelines, feature-heavy workflows
                if workflow.workflow_type in [WorkflowType.BATCH_PROCESSING,
                                            WorkflowType.DATA_PIPELINE]:
                    weight *= 1.8
                # Less interested in pure health checks
                elif workflow.workflow_type == WorkflowType.HEALTH_CHECK:
                    weight *= 0.5

            elif self.persona.name == "SRE / Platform Engineer":
                # Strong preference for monitoring, health checks, batch systems
                if workflow.workflow_type in [WorkflowType.HEALTH_CHECK,
                                            WorkflowType.BATCH_PROCESSING,
                                            WorkflowType.DATA_PIPELINE]:
                    weight *= 1.6
                # Configuration changes need careful consideration
                elif workflow.workflow_type == WorkflowType.CONFIGURATION_UPDATE:
                    weight *= 0.8

            elif self.persona.name == "QA Engineer":
                # Likes to test edge cases, error conditions, lifecycle
                if workflow.workflow_type == WorkflowType.RESOURCE_LIFECYCLE:
                    weight *= 1.7
                # Also likes health checks for baseline
                elif workflow.workflow_type == WorkflowType.HEALTH_CHECK:
                    weight *= 1.3

            # Adjust for risk tolerance
            if self.persona.risk_tolerance < 0.3:  # Risk-averse
                if workflow.workflow_type in [WorkflowType.HEALTH_CHECK,
                                            WorkflowType.CONFIGURATION_UPDATE]:
                    weight *= (1.0 + (0.3 - self.persona.risk_tolerance))
                elif workflow.workflow_type in [WorkflowType.BATCH_PROCESSING,
                                              WorkflowType.DATA_PIPELINE]:
                    weight *= (0.5 + self.persona.risk_tolerance)
            elif self.persona.risk_tolerance > 0.7:  # Risk-seeking
                if workflow.workflow_type in [WorkflowType.BATCH_PROCESSING,
                                              WorkflowType.DATA_PIPELINE]:
                    weight *= (0.5 + (self.persona.risk_tolerance - 0.5) * 2)

            # Adjust for technical expertise
            if self.persona.technical_expertise > 0.7:  # Technical
                if workflow.workflow_type in [WorkflowType.DATA_PIPELINE,
                                            WorkflowType.BATCH_PROCESSING]:
                    weight *= (0.5 + self.persona.technical_expertise)
            elif self.persona.technical_expertise < 0.3:  # Non-technical
                if workflow.workflow_type == WorkflowType.HEALTH_CHECK:
                    weight *= (0.5 + self.persona.technical_expertise)

            # Avoid recent workflows for variety (unless forced)
            if workflow.name in self.recent_workflows:
                weight *= 0.3  # Reduce but don't eliminate

            weighted_workflows.append((workflow, weight))

        # Normalize weights and select
        total_weight = sum(weight for _, weight in weighted_workflows)
        if total_weight == 0:
            # Fallback to uniform selection
            selected = random.choice(self.workflow_library)
        else:
            # Weighted random selection
            rand_val = random.uniform(0, total_weight)
            cumulative = 0
            selected = self.workflow_library[0]  # fallback
            for workflow, weight in weighted_workflows:
                cumulative += weight
                if cumulative >= rand_val:
                    selected = workflow
                    break

        # Update recent workflows
        self.recent_workflows.append(selected.name)
        if len(self.recent_workflows) > self.max_recent_workflows:
            self.recent_workflows.pop(0)

        return selected

    def _prepare_workflow_variables(self, workflow: InfrastructureWorkflow) -> Dict[str, Any]:
        """Prepare variables for workflow substitution based on persona and context."""
        variables = {}

        # Common variables that might be needed
        variables.update({
            "timestamp": str(int(time.time())),
            "username": self._get_credential("username", "testuser"),
            "password": self._get_credential("password", "testpass123"),
            "resource_name": f"{self.persona.name}_{int(time.time())}",
            "resource_description": f"Test resource created by {self.persona.name}",
            "updated_description": f"Updated by {self.persona.name} at {time.time()}",
            "batch_operation": random.choice(["process", "transform", "analyze", "validate"]),
            "batch_items": random.randint(5, 50),
            "priority": random.choice(["low", "medium", "high"]),
            "data_source": random.choice(["api", "file", "stream", "database"]),
            "data_format": random.choice(["json", "csv", "parquet", "avro"]),
            "record_count": random.randint(100, 10000),
            "config_setting": random.choice(["timeout", "retries", "batch_size", "log_level"]),
            "user_id": self.agent_id,
        })

        # Generate appropriate value based on setting type
        if variables["config_setting"] in ["timeout", "retries", "batch_size"]:
            variables["config_value"] = str(random.choice([30, 60, 120, 3, 5, 10, 100]))
        else:  # log_level
            variables["config_value"] = random.choice(["INFO", "DEBUG", "WARN", "ERROR"])

        # Persona-specific adjustments
        if self.persona.name == "Cautious DevOps Engineer":
            # Smaller batches, more conservative settings
            variables["batch_items"] = random.randint(1, 10)
            variables["record_count"] = random.randint(10, 100)
            variables["priority"] = "low"
            # Only apply min/max for numeric settings
            if variables.get("config_setting") in ["timeout", "retries", "batch_size"]:
                try:
                    current_value = int(variables.get("config_value", 30))
                    new_value = min(current_value, 30)
                    variables["config_value"] = str(new_value)
                except ValueError:
                    # If conversion fails, keep the original value
                    pass

        elif self.persona.name == "Aggressive Startup Founder":
            # Larger batches, aggressive settings
            variables["batch_items"] = random.randint(50, 500)
            variables["record_count"] = random.randint(1000, 50000)
            variables["priority"] = random.choice(["high", "medium"])
            # Only apply min/max for numeric settings
            if variables.get("config_setting") in ["timeout", "retries", "batch_size"]:
                try:
                    current_value = int(variables.get("config_value", 30))
                    new_value = max(current_value, 60)
                    variables["config_value"] = str(new_value)
                except ValueError:
                    # If conversion fails, keep the original value
                    pass

        elif self.persona.name == "SRE / Platform Engineer":
            # Focus on stability and performance
            variables["priority"] = "medium"
            variables["config_value"] = str(random.choice([30, 60, 120]))  # sane timeouts

        elif self.persona.name == "QA Engineer":
            # Mix of scenarios for testing
            variables["batch_items"] = random.randint(1, 100)
            variables["record_count"] = random.randint(1, 1000)

        return variables

    def _get_credential(self, cred_type: str, default: str) -> str:
        """Get credentials - in real implementation, these would come from secure storage."""
        # For simulation, we'll use deterministic but varied credentials
        # based on agent ID to avoid collisions
        seed = f"{self.agent_id}_{cred_type}"
        hash_obj = hashlib.md5(seed.encode())
        hash_hex = hash_obj.hexdigest()

        if cred_type == "username":
            return f"user_{hash_hex[:8]}"
        elif cred_type == "password":
            # Generate a pseudo-random password
            return f"Pass{hash_hex[8:16]}!{hash_hex[16:24]}"
        else:
            return default

    def _resolve_endpoint(self, endpoint_str: str) -> str:
        """Replace endpoint configuration placeholders in the endpoint string."""
        import re
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, endpoint_str)
        for match in matches:
            replacement = self.endpoint_config.get(match, match)  # if not found, keep the original
            endpoint_str = endpoint_str.replace('{' + match + '}', replacement)
        return endpoint_str

    # ============================================================================
    # CORE INTERACTION LOGIC
    # ============================================================================

    async def interact(self) -> Dict[str, Any]:
        """
        Perform one interaction cycle: select workflow based on persona,
        execute it with full infrastructure-aware behavior, and return
        structured results for self-instrumentation and learning.
        """
        start_time = time.time()
        interaction_id = f"{self.agent_id}_{int(time.time() * 1000)}"

        # Select workflow based on persona
        workflow = self._select_workflow_based_on_persona()

        # Prepare workflow variables
        workflow_variables = self._prepare_workflow_variables(workflow)
        # Save the current workflow_variables (which includes persistent state like auth_token from previous interactions)
        original_variables = self.workflow_variables.copy()
        # Update with workflow-specific variables for this interaction
        self.workflow_variables.update(workflow_variables)

        try:
            # Execute the workflow
            workflow_results = await self.execute_workflow(workflow.steps)

            # Determine overall success
            successful_steps = sum(1 for r in workflow_results if r.success)
            total_steps = len(workflow_results)
            overall_success = successful_steps == total_steps

            # Update infrastructure state based on results
            self._update_infrastructure_state(workflow, workflow_results)

            # Create structured interaction log entry
            interaction_log = {
                "interaction_id": interaction_id,
                "timestamp": start_time,
                "persona": self.persona.name,
                "workflow_name": workflow.name,
                "workflow_type": workflow.workflow_type.value,
                "steps_attempted": total_steps,
                "steps_succeeded": successful_steps,
                "overall_success": overall_success,
                "workflow_results": [
                    {
                        "step_name": r.step_name,
                        "success": r.success,
                        "status_code": r.status_code,
                        "error": r.error,
                        "retry_count": r.retry_count,
                        "duration_ms": r.duration_ms,
                        "rate_limit_hit": r.rate_limit_info.remaining is not None and r.rate_limit_info.remaining < 10,
                    }
                    for r in workflow_results
                ],
                "infrastructure_state_snapshot": {
                    "discovered_endpoints_count": len(self.infrastructure_state["discovered_endpoints"]),
                    "failed_endpoints_count": len(self.infrastructure_state["failed_endpoints"]),
                    "rate_limited_endpoints_count": len(self.infrastructure_state["rate_limited_endpoints"]),
                },
                "persona_factors": {
                    "risk_tolerance": self.persona.risk_tolerance,
                    "technical_expertise": self.persona.technical_expertise,
                },
            }

            # Add to interaction log
            self.interaction_log.append(interaction_log)
            # Keep interaction log manageable
            if len(self.interaction_log) > 50:
                self.interaction_log.pop(0)

            # Update memory systems for learning
            await self._update_memory_systems(interaction_log, workflow)

            # Prepare final result
            end_time = time.time()

            result = {
                "interaction_id": interaction_id,
                "agent_id": self.agent_id,
                "persona": self.persona.name,
                "workflow_name": workflow.name,
                "workflow_type": workflow.workflow_type.value,
                "start_time": start_time,
                "end_time": end_time,
                "duration_ms": (end_time - start_time) * 1000,
                "overall_success": overall_success,
                "steps_attempted": total_steps,
                "steps_succeeded": successful_steps,
                "workflow_results": [
                    {
                        "step_name": r.step_name,
                        "success": r.success,
                        "status_code": r.status_code,
                        "error": r.error,
                        "retry_count": r.retry_count,
                        "duration_ms": r.duration_ms,
                    }
                    for r in workflow_results
                ],
                "metrics": self.get_metrics(),
                "infrastructure_state": {
                    "discovered_endpoints": list(self.infrastructure_state["discovered_endpoints"])[-5:],  # Last 5
                    "failed_endpoints": list(self.infrastructure_state["failed_endpoints"])[-5:],
                    "rate_limited_endpoints": list(self.infrastructure_state["rate_limited_endpoints"])[-5:],
                },
                "workflow_variables_used": workflow_variables.copy(),
                "structured_log": interaction_log,  # For external consumption
            }

            # Log summary
            logger.info(
                f"Agent {self.agent_id} ({self.persona.name}) completed workflow '{workflow.name}': "
                f"{successful_steps}/{total_steps} steps successful "
                f"in {(end_time - start_time)*1000:.1f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Error in agent {self.agent_id} interaction: {e}", exc_info=True)

            # Return error result
            end_time = time.time()
            return {
                "interaction_id": interaction_id,
                "agent_id": self.agent_id,
                "persona": self.persona.name,
                "workflow_name": workflow.name if 'workflow' in locals() else "unknown",
                "error": str(e),
                "start_time": start_time,
                "end_time": end_time,
                "duration_ms": (end_time - start_time) * 1000,
                "overall_success": False,
                "metrics": self.get_metrics(),
            }
        finally:
            # Determine which auth-related keys have been updated during this workflow
            auth_keys = {'auth_token', 'refresh_token', 'token_expires'}
            updated_auth = {}
            for key in auth_keys:
                if key in self.workflow_variables:
                    orig_val = original_variables.get(key)
                    if orig_val is None or self.workflow_variables[key] != orig_val:
                        updated_auth[key] = self.workflow_variables[key]

            # Reset workflow_variables to the state at the beginning of the interaction
            self.workflow_variables = original_variables.copy()

            # Put back the updated auth tokens
            self.workflow_variables.update(updated_auth)

            logger.debug(f"[{self.agent_id}] Preserved auth tokens in workflow_variables: {list(updated_auth.keys())}")

    def _update_infrastructure_state(self, workflow: InfrastructureWorkflow, results: List[WorkflowResult]):
        """Update internal state based on workflow execution results."""
        # Track discovered endpoints
        for step, result in zip(workflow.steps, results):
            endpoint_key = f"{step.method}:{step.endpoint}"
            if result.success:
                self.infrastructure_state["discovered_endpoints"].add(endpoint_key)
                # Remove from failed if it was there
                self.infrastructure_state["failed_endpoints"].discard(endpoint_key)
                self.infrastructure_state["rate_limited_endpoints"].discard(endpoint_key)
            else:
                self.infrastructure_state["failed_endpoints"].add(endpoint_key)
                # Check if it was a rate limit
                if result.status_code == 429 or (result.rate_limit_info.remaining is not None and result.rate_limit_info.remaining == 0):
                    self.infrastructure_state["rate_limited_endpoints"].add(endpoint_key)

        # Update auth timing if this was an auth workflow
        if workflow.workflow_type == WorkflowType.AUTHENTICATE_AND_OPERATE:
            # Check if any step was authentication
            for step, result in zip(workflow.steps, results):
                if "auth" in step.name.lower() or "login" in step.name.lower():
                    if result.success:
                        self.infrastructure_state["last_auth_time"] = time.time()
                        self.infrastructure_state["auth_method"] = step.method
                    break

    async def _update_memory_systems(self, interaction_log: Dict[str, Any], workflow: InfrastructureWorkflow):
        """Update short-term and long-term memory for learning."""
        # Short-term memory: recent interaction
        self.short_term_memory.append({
            "timestamp": interaction_log["timestamp"],
            "type": "interaction",
            "workflow": workflow.name,
            "success": interaction_log["overall_success"],
            "duration_ms": interaction_log["workflow_results"][-1]["duration_ms"] if interaction_log["workflow_results"] else 0,
        })

        # Keep short-term memory within limit
        if len(self.short_term_memory) > self.max_short_term:
            # Move important items to long-term
            oldest = self.short_term_memory.pop(0)
            # Consider it important if it was a learning experience (failure or success after retries)
            is_important = (
                not oldest["success"] or
                any(r.get("retry_count", 0) > 0 for r in oldest.get("workflow_results", []))
            )
            if is_important:
                self.long_term_memory.append(oldest)

        # Long-term memory: periodically consolidate
        if len(self.long_term_memory) > self.max_long_term:
            # Sort by importance (we'll simplify: failures and retries are important)
            self.long_term_memory.sort(key=lambda x: (
                0 if not x.get("success", True) else  # Failures first
                len([r for r in x.get("workflow_results", []) if r.get("retry_count", 0) > 0])  # Then by retry count
            ), reverse=True)
            self.long_term_memory = self.long_term_memory[:self.max_long_term]

    async def _try_refresh_token(self) -> bool:
        """
        Attempt to refresh authentication token by re-login with credentials.
        Returns True if successful, False otherwise.
        """
        try:
            # Get credentials using the same method as used in workflows
            username = self._get_credential("username", "testuser")
            password = self._get_credential("password", "testpass123")

            # Get the auth login endpoint from config
            auth_login_endpoint = self._resolve_endpoint("{auth_login}")

            # Make login request
            login_data = {
                "username": username,
                "password": password
            }

            # Use a short timeout for refresh attempts
            result = await self._make_request(
                method="POST",
                path=auth_login_endpoint,
                data=login_data,
                retry_config=RetryConfig(max_attempts=1)  # Don't retry refresh attempts
            )

            if result.success and result.data:
                # Extract token from response
                extracted = self._extract_auth_token(result.data)
                if "auth_token" in extracted:
                    # Update session with new token
                    self.session.auth_token = extracted["auth_token"]
                    if "token_expires" in extracted:
                        self.session.token_expires = extracted["token_expires"]
                    # Also update workflow_variables for consistency
                    self.workflow_variables.update(extracted)
                    logger.debug(f"[{self.agent_id}] Successfully refreshed auth token (length: {len(self.session.auth_token)})")
                    return True
                else:
                    logger.warning(f"[{self.agent_id}] Refresh login successful but no token in response")
            else:
                logger.warning(f"[{self.agent_id}] Refresh login failed: {result.error}")

        except Exception as e:
            logger.warning(f"[{self.agent_id}] Error during token refresh: {e}")

        return False

    async def cleanup_resources(self):
        """Clean up resources and call parent cleanup."""
        await super().cleanup_resources()
        # Note: We do NOT clear auth tokens here to preserve them across interactions
        # Auth token preservation is handled in the interact() method's finally block

    def get_detailed_state(self) -> Dict[str, Any]:
        """Get comprehensive state for debugging/monitoring."""
        base_state = {
            "agent_id": self.agent_id,
            "persona": {
                "name": self.persona.name,
                "description": self.persona.description,
                "goals": self.persona.goals,
                "budget": self.persona.budget,
                "risk_tolerance": self.persona.risk_tolerance,
                "technical_expertise": self.persona.technical_expertise,
                "communication_style": self.persona.communication_style,
            },
            "metrics": self.get_metrics(),
            "memory": {
                "short_term_count": len(self.short_term_memory),
                "long_term_count": len(self.long_term_memory),
                "recent_interactions": [
                    {
                        "timestamp": m["timestamp"],
                        "workflow": m.get("workflow", "unknown"),
                        "success": m.get("success", False),
                    }
                    for m in self.short_term_memory[-3:]  # Last 3
                ],
            },
            "interaction_log_count": len(self.interaction_log),
            "recent_workflows": self.recent_workflows.copy(),
        }

        # Add infrastructure-specific state
        base_state["infrastructure_state"] = {
            "discovered_endpoints_count": len(self.infrastructure_state["discovered_endpoints"]),
            "failed_endpoints_count": len(self.infrastructure_state["failed_endpoints"]),
            "rate_limited_endpoints_count": len(self.infrastructure_state["rate_limited_endpoints"]),
            "last_auth_time": self.infrastructure_state["last_auth_time"],
            "auth_method": self.infrastructure_state["auth_method"],
        }

        return base_state