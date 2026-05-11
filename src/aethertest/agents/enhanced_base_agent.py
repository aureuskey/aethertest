"""
Enhanced base class for infrastructure-realistic agents in AetherTest.
Implements stateful workflows, session management, intelligent error handling,
rate limit awareness, and realistic behavior patterns.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
import httpx
import json
import time
import asyncio
import random
from enum import Enum
from dataclasses import dataclass, field
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of HTTP errors for retry decisions."""
    TRANSIENT = "transient"    # 5xx, 429, timeout, network errors
    PERMANENT = "permanent"    # 4xx (except 429) - client errors
    AUTH_RECOVERABLE = "auth_recoverable"  # 401 - might be fixed by refresh


class RetryStrategy(Enum):
    """Different retry strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class RateLimitInfo:
    """Information about rate limits from response headers."""
    limit: Optional[int] = None
    remaining: Optional[int] = None
    reset_time: Optional[float] = None  # Unix timestamp
    retry_after: Optional[float] = None  # Seconds to wait


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    jitter: float = 0.1      # 0-1 fraction to add randomness
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.base_delay
        else:  # EXPONENTIAL_BACKOFF
            delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)

        # Add jitter
        jitter_amount = delay * self.jitter * (2 * random.random() - 1)
        return max(0, delay + jitter_amount)


@dataclass
class SessionState:
    """State maintained across API calls for a session."""
    auth_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires: Optional[float] = None  # Unix timestamp
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    rate_limit_info: RateLimitInfo = field(default_factory=RateLimitInfo)

    def is_authenticated(self) -> bool:
        """Check if we have a valid auth token."""
        if not self.auth_token:
            return False
        if self.token_expires and time.time() >= self.token_expires:
            return False
        return True

    def needs_refresh(self) -> bool:
        """Check if token needs refreshing (expires soon)."""
        if not self.auth_token or not self.token_expires:
            return False
        # Refresh if expires in less than 5 minutes
        return time.time() >= (self.token_expires - 300)


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    method: str
    endpoint: str
    data: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    expected_status: List[int] = field(default_factory=lambda: [200, 201])
    validate_response: Optional[Callable[[Dict[str, Any]], bool]] = None
    extract_data: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    critical: bool = True  # If False, workflow continues even if this fails


@dataclass
class WorkflowResult:
    """Result of executing a workflow step."""
    step_name: str
    success: bool
    status_code: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    duration_ms: float = 0
    rate_limit_info: RateLimitInfo = field(default_factory=RateLimitInfo)


class EnhancedBaseAgent(ABC):
    """
    Enhanced base class for infrastructure-realistic agents.
    Provides session management, workflow execution, intelligent error handling,
    and realistic behavior patterns.
    """

    def __init__(self, agent_id: str, api_endpoint: str, api_key: Optional[str] = None):
        self.agent_id = agent_id
        self.api_endpoint = api_endpoint.rstrip("/")
        self.api_key = api_key

        # Session state
        self.session = SessionState()

        # Initialize headers
        self.session.headers = {
            "Content-Type": "application/json",
            "User-Agent": f"AetherTest-Agent/{self.agent_id}",
        }
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

        # Workflow state
        self.current_workflow: Optional[List[WorkflowStep]] = None
        self.workflow_step_index: int = 0
        self.workflow_variables: Dict[str, Any] = {}  # For extracting data from responses

        # Metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries_attempted": 0,
            "rate_limit_hits": 0,
            "auth_refreshes": 0,
            "workflows_completed": 0,
            "workflows_failed": 0,
        }

        # Resource tracking for cleanup
        self.created_resources: List[Dict[str, Any]] = []

    async def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> WorkflowResult:
        """
        Make an HTTP request with intelligent error handling, retries,
        rate limit awareness, and session management.
        """
        start_time = time.time()
        url = urljoin(self.api_endpoint + "/", path.lstrip("/"))

        # Use provided retry config or default
        retry_config = retry_config or RetryConfig()

        last_exception = None

        for attempt in range(1, retry_config.max_attempts + 1):
            # Prepare headers with session state for this attempt
            print(f"[DEBUG] Preparing request. Session auth_token present: {bool(self.session.auth_token)}, authenticated: {self.session.is_authenticated()}")
            headers = self.session.headers.copy()
            if self.session.auth_token and self.session.is_authenticated():
                headers["Authorization"] = f"Bearer {self.session.auth_token}"
                print(f"[DEBUG] Added Authorization header (token length: {len(self.session.auth_token)})")
            else:
                print(f"[DEBUG] Not adding Authorization header")

            # Add cookies if any
            if self.session.cookies:
                # httpx handles cookies differently, we'll simplify for now
                pass

            try:
                self.metrics["total_requests"] += 1

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data if data else None,
                        params=params,
                    )

                # Update rate limit info from headers
                rate_limit_info = self._extract_rate_limit_info(response)
                self.session.rate_limit_info = rate_limit_info

                # Check if we hit rate limit
                if response.status_code == 429:
                    self.metrics["rate_limit_hits"] += 1
                    # If we have retry-after, respect it
                    if rate_limit_info.retry_after:
                        await asyncio.sleep(rate_limit_info.retry_after)
                        # Retry immediately after waiting
                        continue

                # Handle authentication
                if response.status_code == 401:
                    # Try to refresh token if we have refresh capability
                    if await self._try_refresh_token():
                        self.metrics["auth_refreshes"] += 1
                        # Retry with new token
                        continue
                    # If refresh fails or not available, treat as permanent error
                    error_type = ErrorType.PERMANENT
                else:
                    # Classify error type
                    if 500 <= response.status_code < 600:
                        error_type = ErrorType.TRANSIENT
                    elif response.status_code == 429:
                        error_type = ErrorType.TRANSIENT
                    elif 400 <= response.status_code < 500:
                        if response.status_code == 401:
                            error_type = ErrorType.AUTH_RECOVERABLE
                        else:
                            error_type = ErrorType.PERMANENT
                    else:
                        # Success or other
                        error_type = None

                # Determine if we should retry
                should_retry = (
                    error_type == ErrorType.TRANSIENT and
                    attempt < retry_config.max_attempts
                )

                if should_retry:
                    self.metrics["retries_attempted"] += 1
                    delay = retry_config.calculate_delay(attempt)
                    await asyncio.sleep(delay)
                    continue

                # Final attempt - process response
                duration_ms = (time.time() - start_time) * 1000

                if 200 <= response.status_code < 300:
                    self.metrics["successful_requests"] += 1
                    try:
                        response_data = response.json() if response.content else {}
                    except:
                        response_data = {}

                    return WorkflowResult(
                        step_name="",  # Will be filled by caller
                        success=True,
                        status_code=response.status_code,
                        data=response_data,
                        duration_ms=duration_ms,
                        rate_limit_info=rate_limit_info,
                    )
                else:
                    self.metrics["failed_requests"] += 1
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json() if response.content else {}
                        error_msg += f": {error_data}"
                    except:
                        pass

                    return WorkflowResult(
                        step_name="",
                        success=False,
                        status_code=response.status_code,
                        error=error_msg,
                        duration_ms=duration_ms,
                        rate_limit_info=rate_limit_info,
                        retry_count=attempt - 1,
                    )

            except httpx.TimeoutException as e:
                last_exception = e
                error_type = ErrorType.TRANSIENT
                if attempt < retry_config.max_attempts:
                    self.metrics["retries_attempted"] += 1
                    delay = retry_config.calculate_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                break

            except httpx.NetworkError as e:
                last_exception = e
                error_type = ErrorType.TRANSIENT
                if attempt < retry_config.max_attempts:
                    self.metrics["retries_attempted"] += 1
                    delay = retry_config.calculate_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                break

            except Exception as e:
                last_exception = e
                # Non-HTTP errors are typically transient (network issues)
                error_type = ErrorType.TRANSIENT
                if attempt < retry_config.max_attempts:
                    self.metrics["retries_attempted"] += 1
                    delay = retry_config.calculate_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                break

        # If we get here, all retries exhausted
        duration_ms = (time.time() - start_time) * 1000
        error_msg = str(last_exception) if last_exception else "Max retries exceeded"

        return WorkflowResult(
            step_name="",
            success=False,
            error=error_msg,
            duration_ms=duration_ms,
            retry_count=retry_config.max_attempts - 1,
        )

    def _extract_rate_limit_info(self, response: httpx.Response) -> RateLimitInfo:
        """Extract rate limit information from response headers."""
        info = RateLimitInfo()

        # Common rate limit headers
        if "X-RateLimit-Limit" in response.headers:
            try:
                info.limit = int(response.headers["X-RateLimit-Limit"])
            except ValueError:
                pass

        if "X-RateLimit-Remaining" in response.headers:
            try:
                info.remaining = int(response.headers["X-RateLimit-Remaining"])
            except ValueError:
                pass

        if "X-RateLimit-Reset" in response.headers:
            try:
                reset_timestamp = int(response.headers["X-RateLimit-Reset"])
                info.reset_time = float(reset_timestamp)
            except ValueError:
                pass

        if "Retry-After" in response.headers:
            try:
                info.retry_after = float(response.headers["Retry-After"])
            except ValueError:
                pass

        # Also check for standard RateLimit-* headers
        if "RateLimit-Limit" in response.headers:
            try:
                info.limit = int(response.headers["RateLimit-Limit"])
            except ValueError:
                pass

        if "RateLimit-Remaining" in response.headers:
            try:
                info.remaining = int(response.headers["RateLimit-Remaining"])
            except ValueError:
                pass

        if "RateLimit-Reset" in response.headers:
            try:
                reset_timestamp = int(response.headers["RateLimit-Reset"])
                info.reset_time = float(reset_timestamp)
            except ValueError:
                pass

        return info

    async def _try_refresh_token(self) -> bool:
        """
        Attempt to refresh authentication token.
        Returns True if successful, False otherwise.
        """
        # This should be overridden by subclasses that need token refresh
        # For now, return False to indicate no refresh capability
        return False

    async def execute_workflow(self, workflow: List[WorkflowStep]) -> List[WorkflowResult]:
        """
        Execute a multi-step workflow, maintaining state between steps.
        """
        self.current_workflow = workflow
        self.workflow_step_index = 0
        results = []

        for step in workflow:
            self.workflow_step_index += 1

            # Apply variable substitution to step
            processed_step = self._substitute_variables(step)

            # Execute step with retry logic
            result = await self._make_request(
                method=processed_step.method,
                path=processed_step.endpoint,
                data=processed_step.data,
                params=processed_step.params,
                retry_config=processed_step.retry_config,
            )

            result.step_name = processed_step.name

            # Validate response if validator provided
            if result.success and processed_step.validate_response:
                try:
                    validation_passed = processed_step.validate_response(result.data)
                    if not validation_passed:
                        result.success = False
                        result.error = "Response validation failed"
                except Exception as e:
                    result.success = False
                    result.error = f"Validation error: {str(e)}"

            # Extract data if extractor provided
            if result.success and processed_step.extract_data:
                try:
                    extracted = processed_step.extract_data(result.data)
                    self.workflow_variables.update(extracted)

                    # If this is an auth token extraction, update session
                    if "auth_token" in extracted:
                        self.session.auth_token = extracted["auth_token"]
                        # Set expiration if provided
                        if "token_expires" in extracted:
                            self.session.token_expires = extracted["token_expires"]
                        logger.debug(f"[{self.agent_id}] Updated session auth token (length: {len(self.session.auth_token)}), expires: {self.session.token_expires}")
                    else:
                        logger.debug(f"[{self.agent_id}] No auth_token in extracted data")
                except Exception as e:
                    # Don't fail workflow for extraction errors, just log
                    logger.warning(f"Failed to extract data from {processed_step.name}: {e}")

            # Track successful resource creation for cleanup
            if result.success and processed_step.method in ["POST", "PUT", "PATCH"]:
                resource_info = {
                    "step": processed_step.name,
                    "method": processed_step.method,
                    "endpoint": processed_step.endpoint,
                    "data": processed_step.data,
                    "created_at": time.time(),
                }
                # Try to extract ID from response
                if result.data:
                    # Common ID field names
                    for id_field in ["id", "ID", "_id", "uid", "resourceId"]:
                        if id_field in result.data:
                            resource_info["resource_id"] = result.data[id_field]
                            break
                self.created_resources.append(resource_info)

            results.append(result)

            # If this step was critical and failed, stop workflow
            if not result.success and processed_step.critical:
                self.metrics["workflows_failed"] += 1
                break

        # If we completed all steps (or didn't break on critical failure)
        if len(results) == len(workflow) or \
           (len(results) < len(workflow) and not workflow[len(results)].critical):
            self.metrics["workflows_completed"] += 1

        self.current_workflow = None
        self.workflow_step_index = 0
        # Keep workflow variables for potential use in future workflows
        # self.workflow_variables.clear()  # Uncomment if you want to reset each workflow

        return results

    def _substitute_variables(self, step: WorkflowStep) -> WorkflowStep:
        """Substitute workflow variables into step fields."""
        # Simple string substitution for demonstration
        # In a full implementation, you might want a more robust templating system

        def substitute_value(value):
            if isinstance(value, str):
                for var_name, var_value in self.workflow_variables.items():
                    placeholder = f"{{{{{var_name}}}}}"
                    if placeholder in value:
                        value = value.replace(placeholder, str(var_value))
                return value
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value

        return WorkflowStep(
            name=substitute_value(step.name),
            method=substitute_value(step.method),
            endpoint=substitute_value(step.endpoint),
            data=substitute_value(step.data),
            params=substitute_value(step.params),
            expected_status=step.expected_status,
            validate_response=step.validate_response,
            extract_data=step.extract_data,
            retry_config=step.retry_config,
            critical=step.critical,
        )

    async def cleanup_resources(self):
        """Clean up any resources created during the session."""
        # Cleanup in reverse order (last created, first deleted)
        for resource in reversed(self.created_resources):
            try:
                if "resource_id" in resource and resource["endpoint"]:
                    # Construct DELETE endpoint
                    delete_endpoint = f"{resource['endpoint']}/{resource['resource_id']}"
                    await self._make_request(
                        method="DELETE",
                        path=delete_endpoint,
                        retry_config=RetryConfig(max_attempts=1),  # Don't retry cleanup
                    )
                    logger.info(f"Cleaned up resource {resource['resource_id']} from {resource['endpoint']}")
            except Exception as e:
                logger.warning(f"Failed to cleanup resource {resource.get('resource_id')}: {e}")

        self.created_resources.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics.copy()

    @abstractmethod
    async def interact(self) -> Dict[str, Any]:
        """
        Perform an interaction with the target API.
        Must be implemented by each agent type.
        Should return structured data including intent, decision, outcome.
        """
        pass