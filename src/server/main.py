from fastapi import FastAPI
import uvicorn
from src.server.api.router import router as main_router

main_app = FastAPI()

main_app.include_router(main_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(main_app, host="0.0.0.0")
