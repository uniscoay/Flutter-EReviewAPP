from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, users, employer_reviews, peer_reviews, points, realtime
from .db import init_db

app = FastAPI(title="Performance Review API")

# Initialize database
init_db()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(employer_reviews.router, prefix="/reviews/employer", tags=["Employer Reviews"])
app.include_router(peer_reviews.router, prefix="/reviews/peer", tags=["Peer Reviews"])
app.include_router(points.router, prefix="/points", tags=["Points & Gamification"])
app.include_router(realtime.router, prefix="/realtime", tags=["Real-time Updates"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Performance Review API"} 