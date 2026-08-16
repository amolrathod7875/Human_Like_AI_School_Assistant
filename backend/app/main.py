import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import AppError, RequestContext
from app.core.logging import configure_logging, get_logger
from app.core.responses import ApiResponse, ErrorDetail

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.SERVICE_NAME, settings.ENVIRONMENT)
    yield
    logger.info("Shutting down %s", settings.SERVICE_NAME)


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
    )

    # CORS is fully configurable via BACKEND_CORS_ORIGINS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_middleware(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        # Honor a client-supplied request id, otherwise generate one.
        request_id = request.headers.get(
            settings.REQUEST_ID_HEADER
        ) or f"req_{uuid.uuid4().hex}"
        RequestContext.set_request_id(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            RequestContext.reset()
        response.headers[settings.REQUEST_ID_HEADER] = request_id
        return response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        logger.error("AppError: %s (%s)", exc.message, exc.code)
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    request_id=RequestContext.get_request_id(),
                ),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="Request validation failed",
                    request_id=RequestContext.get_request_id(),
                ),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="HTTP_ERROR",
                    message=str(exc.detail),
                    request_id=RequestContext.get_request_id(),
                ),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred",
                    request_id=RequestContext.get_request_id(),
                ),
            ).model_dump(mode="json"),
        )


app = create_app()
