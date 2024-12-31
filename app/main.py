from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from .api.api import api_router
from .db.database import create_tables
from fastapi.responses import JSONResponse
import logging
import json
import traceback

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # make sure tables are created
    create_tables()
    yield

logger = logging.getLogger("fastapi")

app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    request_info = {
        "url": str(request.url),
        "method": request.method,
        "headers": dict(request.headers),
        "body": body.decode() if body else None,
        "path_params": request.path_params,
        "query_params": dict(request.query_params)
    }

    try:
        # execute the request
        response = await call_next(request)
        
        if response.status_code >= 400:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            logger.error(
                f"Request failed with status {response.status_code}\n"
                f"Request: {json.dumps(request_info, indent=2)}\n"
                f"Response: {response_body.decode()}\n"
            )
            return JSONResponse(
                content=json.loads(response_body),
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        return response

    except Exception as e:
        logger.error(
            f"Request failed with exception\n"
            f"Request: {json.dumps(request_info, indent=2)}\n"
            f"Error: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        raise

# register the API router
app.include_router(api_router, prefix="/api")
