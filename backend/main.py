from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from backend.api import routes
except ModuleNotFoundError:
    from api import routes

app = FastAPI()

# Allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)

@app.get("/")
def root():
    return {"message": "Legal Analyzer is live"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
