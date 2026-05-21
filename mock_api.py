"""
Mock Infrastructure API for testing.
Simulates a realistic infrastructure API with auth, CRUD, rate limiting, and error handling.
"""
print("mock_api.py loaded!")
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
import asyncio
from contextlib import asynccontextmanager

# Global state for the mock API
class MockAPIState:
    def __init__(self):
        self.tokens: Dict[str, Dict] = {}  # token -> token_data
        self.resources: Dict[str, Dict] = {}  # resource_id -> resource_data
        self.batch_jobs: Dict[str, Dict] = {}  # job_id -> job_data
        self.request_counts: Dict[str, int] = {}  # endpoint -> count
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max_requests = 5  # requests per window (reduced for testing)
        self.error_rate = 0.05  # 5% chance of random errors
        self.start_time = time.time()

state = MockAPIState()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class Resource(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

class ResourceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tags: List[str] = []

class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []

class BatchJob(BaseModel):
    id: str
    operation: str
    items: List[Any]
    status: str  # pending, processing, completed, failed
    result: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

class BatchJobCreate(BaseModel):
    operation: str
    items: List[Any]

# Security
security = HTTPBearer(auto_error=False)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the JWT token."""
    # Log to file for debugging
    with open("verify_token_debug.log", "a") as f:
        f.write(f"!!!!!! VERIFY_TOKEN CALLED with credentials: {credentials} !!!!!!\n")
    if credentials is None:
        with open("verify_token_debug.log", "a") as f:
            f.write("!!!!!! NO CREDENTIALS !!!!!!\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    with open("verify_token_debug.log", "a") as f:
        f.write(f"!!!!!! TOKEN EXTRACTED: '{token}' !!!!!!\n")
        f.write(f"!!!!!! TOKEN LENGTH: {len(token) if token else 0} !!!!!!\n")
        f.write(f"!!!!!! AVAILABLE TOKENS: {list(state.tokens.keys())} !!!!!!\n")

    if state.tokens:
        stored_token_list = list(state.tokens.keys())
        with open("verify_token_debug.log", "a") as f:
            f.write(f"!!!!!! FIRST STORED TOKEN: '{stored_token_list[0]}' (length: {len(stored_token_list[0])}) !!!!!!\n")
            f.write(f"!!!!!! LAST STORED TOKEN: '{stored_token_list[-1]}' (length: {len(stored_token_list[-1])}) !!!!!\n")

    # Strip whitespace that might cause issues
    if token:
        token = token.strip()
        with open("verify_token_debug.log", "a") as f:
            f.write(f"!!!!!! TOKEN AFTER STRIP: '{token}' (length: {len(token)}) !!!!!!\n")

    # Check if token exists in state and is not expired
    token_found = False
    matched_token = None
    if token:
        current_time = time.time()
        # We need to iterate over a copy of the keys because we might modify the dict
        for stored_token in list(state.tokens.keys()):
            # Get the token data
            token_data = state.tokens.get(stored_token)
            if token_data is None:
                # Token was removed, skip
                continue
            # Check if token has expired
            expires_at_str = token_data.get("expires_at")
            if expires_at_str:
                try:
                    expires_at = float(expires_at_str)
                    if current_time >= expires_at:
                        # Token has expired, remove it
                        del state.tokens[stored_token]
                        continue
                except (ValueError, TypeError):
                    # If we can't parse the date, assume it's not expired
                    pass
            # Compare stripped versions to handle whitespace on either side
            if token == stored_token.strip():
                token_found = True
                matched_token = stored_token
                with open("verify_token_debug.log", "a") as f:
                    f.write(f"!!!!!! MATCH FOUND: stored_token='{stored_token[:10]}...' !!!!!!\n")
                break
            else:
                with open("verify_token_debug.log", "a") as f:
                    f.write(f"!!!!!! COMPARE FAILED: token='{token[:10]}...', stored_token='{stored_token[:10]}...', equal={token == stored_token.strip()} !!!!!!\n")

    if token_found and matched_token:
        with open("verify_token_debug.log", "a") as f:
            f.write(f"!!!!!! TOKEN FOUND: {matched_token[:10]}... !!!!!!\n")
        return state.tokens[matched_token]
    else:
        with open("verify_token_debug.log", "a") as f:
            f.write(f"!!!!!! TOKEN NOT FOUND: {token[:10] if token else 'None'}... !!!!!!\n")
        # Show first few tokens for comparison
        if state.tokens:
            sample_tokens = list(state.tokens.keys())[:3]
            sample_info = [f"'{t[:8]}...' (len:{len(t)})" for t in sample_tokens]
            detail_msg = f"Token not found. Token: '{token[:10] if token else 'None'}...' (len:{len(token) if token else 0}), Samples: {sample_info}"
        else:
            detail_msg = f"Token not found. Token: '{token}', No tokens available"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )

def check_rate_limit(endpoint: str):
    """Check if the request exceeds rate limit."""
    now = time.time()
    window_start = now - state.rate_limit_window

    # Clean old entries (simple approach - in production you'd use a proper sliding window)
    if random.random() < 0.1:  # 10% chance to clean on each request
        keys_to_delete = []
        for key, timestamp in list(state.request_counts.items()):
            if isinstance(timestamp, (int, float)) and timestamp < window_start:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del state.request_counts[key]

    # Increment counter for this endpoint
    state.request_counts[endpoint] = state.request_counts.get(endpoint, 0) + 1

    # Check if rate limit exceeded
    if state.request_counts[endpoint] > state.rate_limit_max_requests:
        # Calculate retry-after time (simplified)
        retry_after = state.rate_limit_window
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(state.rate_limit_max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(now + state.rate_limit_window)),
                "Retry-After": str(retry_after)
            }
        )

    # Add rate limit info to response headers (will be added by endpoint functions)
    return {
        "X-RateLimit-Limit": str(state.rate_limit_max_requests),
        "X-RateLimit-Remaining": str(state.rate_limit_max_requests - state.request_counts[endpoint]),
        "X-RateLimit-Reset": str(int(now + state.rate_limit_window))
    }

def maybe_return_error():
    """Randomly return an error based on error_rate."""
    if random.random() < state.error_rate:
        # Choose random error type
        error_types = [
            (status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error"),
            (status.HTTP_503_SERVICE_UNAVAILABLE, "Service temporarily unavailable"),
            (status.HTTP_408_REQUEST_TIMEOUT, "Request timeout"),
            (status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
        ]
        status_code, detail = random.choice(error_types)
        raise HTTPException(status_code=status_code, detail=detail)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Mock Infrastructure API...")
    yield
    # Shutdown
    print("Shutting down Mock Infrastructure API...")

# Create FastAPI app
app = FastAPI(
    title="Mock Infrastructure API",
    description="A mock API for testing infrastructure tools",
    version="1.0.0",
    lifespan=lifespan
)

# Routes
@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # Check for random errors
    maybe_return_error()

    # Validate credentials (in reality, check against database)
    # For demo, accept any non-empty username/password
    if not request.username or not request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Generate token
    token = str(uuid.uuid4())
    expires_at = time.time() + 3600

    # Store token
    state.tokens[token] = {
        "username": request.username,
        "expires_at": expires_at,
        "created_at": datetime.utcnow().isoformat()
    }
    print(f"Generated token: {token}")
    print(f"Stored tokens: {list(state.tokens.keys())}")

    return LoginResponse(
        access_token=token,
        expires_in=3600  # 1 hour
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.05, 0.2))

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - state.start_time,
        "version": "1.0.0"
    }

@app.get("/api/v1/resources", response_model=List[Resource])
async def list_resources(token_data: dict = Depends(verify_token)):
    """List all resources."""
    print("!!!!!! LIST_RESOURCES CALLED !!!!!!")
    # Check rate limit
    headers = check_rate_limit("/api/v1/resources")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.1, 0.3))

    # Return resources
    resources = list(state.resources.values())

    # Add headers (in a real implementation, these would be returned properly)
    # For now, we'll just return the data and note that headers should be included
    return resources

@app.post("/api/v1/resources", response_model=Resource)
async def create_resource(
    resource: ResourceCreate,
    token_data: dict = Depends(verify_token)
):
    """Create a new resource."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/resources")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.2, 0.5))

    # Create resource
    resource_id = str(uuid.uuid4())
    now = datetime.utcnow()

    resource_data = Resource(
        id=resource_id,
        name=resource.name,
        description=resource.description,
        tags=resource.tags,
        created_at=now,
        updated_at=now
    )

    # Store resource
    state.resources[resource_id] = resource_data.dict()

    return resource_data

@app.get("/api/v1/resources/{resource_id}", response_model=Resource)
async def get_resource(
    resource_id: str,
    token_data: dict = Depends(verify_token)
):
    """Get a specific resource."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/resources")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.1, 0.3))

    # Check if resource exists
    if resource_id not in state.resources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    return state.resources[resource_id]

@app.patch("/api/v1/resources/{resource_id}", response_model=Resource)
async def update_resource(
    resource_id: str,
    resource_update: ResourceUpdate,
    token_data: dict = Depends(verify_token)
):
    """Update a resource."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/resources")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.2, 0.5))

    # Check if resource exists
    if resource_id not in state.resources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Update resource
    resource_data = state.resources[resource_id]
    if resource_update.name is not None:
        resource_data["name"] = resource_update.name
    if resource_update.description is not None:
        resource_data["description"] = resource_update.description
    if resource_update.tags is not None:
        resource_data["tags"] = resource_update.tags

    resource_data["updated_at"] = datetime.utcnow().isoformat()

    # Update in storage
    state.resources[resource_id] = resource_data

    return resource_data

@app.delete("/api/v1/resources/{resource_id}")
async def delete_resource(
    resource_id: str,
    token_data: dict = Depends(verify_token)
):
    """Delete a resource."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/resources")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.1, 0.3))

    # Check if resource exists
    if resource_id not in state.resources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Delete resource
    del state.resources[resource_id]

    return {"message": "Resource deleted successfully"}

@app.post("/api/v1/batch", response_model=BatchJob)
async def create_batch_job(
    job: BatchJobCreate,
    token_data: dict = Depends(verify_token)
):
    """Create a new batch job."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/batch")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.2, 0.5))

    # Create batch job
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()

    job_data = BatchJob(
        id=job_id,
        operation=job.operation,
        items=job.items,
        status="pending",
        created_at=now,
        updated_at=now
    )

    # Store job
    state.batch_jobs[job_id] = job_data.dict()

    return job_data

@app.get("/api/v1/batch/{job_id}", response_model=BatchJob)
async def get_batch_job(
    job_id: str,
    token_data: dict = Depends(verify_token)
):
    """Get a specific batch job."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/batch")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.1, 0.3))

    # Check if job exists
    if job_id not in state.batch_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch job not found"
        )

    job_data = state.batch_jobs[job_id]

    # Simulate job progression for demo purposes
    if job_data["status"] == "pending":
        # Move to processing after a short time
        if datetime.utcnow() - datetime.fromisoformat(job_data["created_at"]) > timedelta(seconds=2):
            job_data["status"] = "processing"
            state.batch_jobs[job_id] = job_data
    elif job_data["status"] == "processing":
        # Complete after a bit more time
        if datetime.utcnow() - datetime.fromisoformat(job_data["created_at"]) > timedelta(seconds=5):
            # Randomly decide if job succeeds or fails
            if random.random() < 0.8:  # 80% success rate
                job_data["status"] = "completed"
                job_data["result"] = {
                    "processed_items": len(job_data["items"]),
                    "output": f"Processed {len(job_data['items'])} items successfully"
                }
            else:
                job_data["status"] = "failed"
                job_data["result"] = {
                    "error": "Processing failed due to unexpected condition"
                }
            job_data["updated_at"] = datetime.utcnow().isoformat()
            state.batch_jobs[job_id] = job_data

    return state.batch_jobs[job_id]

@app.get("/api/v1/config")
async def get_config(token_data: dict = Depends(verify_token)):
    """Get configuration."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/config")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.05, 0.2))

    return {
        "features": {
            "authentication": True,
            "rate_limiting": True,
            "batch_processing": True,
            "resource_management": True
        },
        "limits": {
            "rate_limit_per_minute": state.rate_limit_max_requests,
            "batch_size_limit": 1000
        },
        "version": "1.0.0"
    }

@app.put("/api/v1/config")
async def update_config(
    config_update: Dict[str, Any],
    token_data: dict = Depends(verify_token)
):
    """Update configuration."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/config")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.1, 0.3))

    # In a real implementation, this would update actual configuration
    # For now, just acknowledge the update
    return {
        "message": "Configuration updated successfully",
        "updated_fields": list(config_update.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/ingest")
async def ingest_data(
    data: Dict[str, Any],
    token_data: dict = Depends(verify_token)
):
    """Ingest data for processing."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/ingest")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.5, 2.0))  # Ingestion can take time

    # Create ingest ID
    ingest_id = str(uuid.uuid4())

    return {
        "ingest_id": ingest_id,
        "status": "accepted",
        "message": "Data ingested successfully for processing",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/process/{ingest_id}")
async def get_processing_status(
    ingest_id: str,
    token_data: dict = Depends(verify_token)
):
    """Get processing status for ingested data."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/process/{ingest_id}")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # Simulate processing progression
    # In reality, this would check actual processing status
    # For demo, we'll simulate based on time
    # Since we don't store the ingest time, we'll just return a simulated status
    processing_time = random.uniform(1, 10)  # Random processing time 1-10 seconds

    # For demo purposes, we'll say it's done if we've been running long enough
    # In reality, you'd store the start time of each ingest
    if time.time() - state.start_time > processing_time:
        status = "completed"
        result = {
            "processed_records": random.randint(100, 10000),
            "output_location": f"s3://bucket/processed/{ingest_id}/"
        }
    else:
        status = "processing"
        result = None

    return {
        "ingest_id": ingest_id,
        "status": status,
        "progress_percent": random.randint(0, 100) if status == "processing" else 100,
        "result": result,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/results/{ingest_id}")
async def get_results(
    ingest_id: str,
    token_data: dict = Depends(verify_token)
):
    """Get results for ingested data."""
    # Check rate limit
    headers = check_rate_limit("/api/v1/results/{ingest_id}")

    # Check for random errors
    maybe_return_error()

    # Simulate some processing delay
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # In reality, this would fetch actual results
    # For demo, we'll generate some mock results
    return {
        "ingest_id": ingest_id,
        "results": [
            {
                "id": f"result_{i}",
                "value": f"result_value_{i}",
                "processed": True
            }
            for i in range(random.randint(1, 10))
        ],
        "count": random.randint(1, 10),
        "timestamp": datetime.utcnow().isoformat()
    }

# Health check for the app itself (no auth required)
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Mock Infrastructure API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "mock_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )