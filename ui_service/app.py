from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel

app = FastAPI(
    title="SAN Autoresponder UI Service",
    description="Simple web interface for automatic review response generation",
    version="1.0.0"
)

# CORS middleware for API requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "https://team5.kubepractice.ru/auth")
PRODUCER_SERVICE_URL = os.getenv("PRODUCER_SERVICE_URL", "https://team5.kubepractice.ru/producer")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "https://team5.kubepractice.ru/ml")

# HTTP client
client = httpx.AsyncClient(timeout=30.0)


class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class ReviewRequest(BaseModel):
    review_text: str


class ReviewResponse(BaseModel):
    review_id: str
    review_text: str
    sentiment: str
    score: float
    reply: str
    author: str
    created_at: str


@app.on_event("startup")
async def startup_event():
    """Initialize the HTTP client."""
    global client
    client = httpx.AsyncClient(timeout=30.0)


@app.on_event("shutdown")
async def shutdown_event():
    """Close the HTTP client."""
    await client.aclose()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def auth_page(request: Request):
    """Serve the authentication page."""
    return templates.TemplateResponse("auth.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serve the registration page."""
    return templates.TemplateResponse("auth.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "ui"}


async def get_token_from_header(request: Request) -> str:
    """Extract JWT token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return auth_header.split(" ")[1]


@app.post("/api/auth/register")
async def register(user: UserCreate):
    """Register a new user."""
    try:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/register/",
            json={"username": user.username, "password": user.password}
        )
        response.raise_for_status()
        return {"message": "User registered successfully"}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Registration failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login")
async def login(user: UserLogin):
    """Authenticate user and return token."""
    try:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/login/",
            json={"username": user.username, "password": user.password}
        )
        response.raise_for_status()
        data = response.json()
        return data
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Authentication failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reviews/submit")
async def submit_review(review: ReviewRequest, token: str = Depends(get_token_from_header)):
    """Submit a review for analysis."""
    try:
        # Log the incoming request for debugging
        print(f"Received review: {review.review_text}")
        
        response = await client.post(
            f"{PRODUCER_SERVICE_URL}/submit-review/",
            params={"token": token},
            json={"review_text": review.review_text}
        )
        response.raise_for_status()
        data = response.json()
        return data
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="Unauthorized")
        raise HTTPException(status_code=e.response.status_code, detail="Failed to submit review")
    except Exception as e:
        print(f"Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reviews/{review_id}")
async def get_review_result(review_id: str, token: str = Depends(get_token_from_header)):
    """Get review analysis result."""
    try:
        response = await client.get(
            f"{ML_SERVICE_URL}/reviews/{review_id}",
            params={"token": token}
        )
        response.raise_for_status()
        data = response.json()
        return data
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Review not found")
        elif e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="Unauthorized")
        raise HTTPException(status_code=e.response.status_code, detail="Failed to get review")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
