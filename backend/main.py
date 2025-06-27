

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from services.chat_service import ChatService, chat_service

app = FastAPI()
    #    ChatService.graph_with_mongo = create_tax_graph()
# ─── Import Routers ─────────────────────────────────────────────
from routes.tax_routes import router as tax_router
from controllers import auth_controller, chat_controller

# ─── Services & Settings ────────────────────────────────────────
from config.settings import settings
from services.database_service import db_service

# ─── Optional: LangGraph check ─────────────────────────────────
try:
    from rag_pipeline.main_graph import create_tax_graph
    print("LangGraph 'graph' imported successfully.")
except ImportError as e:
    print(f"Error importing LangGraph: {e}")
    print("Ensure 'rag_pipeline/main_graph.py' defines 'graph'.")

# ─── Initialize FastAPI ────────────────────────────────────────
app = FastAPI(
    title="Unified Tax & Chatbot API",
    description="All-in-one backend with tax deduction summary + chatbot with sessions.",
    version="1.0.0"
)

# ─── CORS Configuration ─────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to frontend URL in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-User-ID"],
)

# ─── Log All Responses (optional, useful for debugging) ────────
# @app.middleware("http")
# async def log_response(request: Request, call_next):
#     response = await call_next(request)
#     body = b""
#     async for chunk in response.body_iterator:
#         body += chunk
#     print(f"Response body: {body.decode()}")
#     return JSONResponse(content=body.decode())

# ─── Startup & Shutdown Events ─────────────────────────────────
@app.on_event("startup")
async def startup_event():
    await chat_service.initialize()
    await db_service.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await db_service.disconnect()

# ─── Health Check Endpoint ─────────────────────────────────────
@app.get('/', summary="Health Check")
async def health_check():
    try:
        await db_service.get_client().admin.command('ping')
        return JSONResponse({
            "status": "Backend running and MongoDB connected!",
            "version": "1.0.0"
        })
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

# ─── Register All Routers ──────────────────────────────────────
app.include_router(tax_router, prefix="/tax", tags=["Tax"])
app.include_router(auth_controller.router, tags=["Authentication"])
app.include_router(chat_controller.router, tags=["Chat Sessions"])
