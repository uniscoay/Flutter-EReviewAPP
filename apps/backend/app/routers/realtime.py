from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.orm import Session
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime

from ..db import get_db
from ..models.user import User
from ..models.peer_review import PeerReview

router = APIRouter()

# Connection manager to keep track of active websocket connections
class ConnectionManager:
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Store all connections for broadcasting
        self.all_connections: List[WebSocket] = []
        # Track connected user IDs for statistics
        self.connected_users: Set[str] = set()
    
    async def connect(self, websocket: WebSocket, user_id: str = None):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.all_connections.append(websocket)
        
        if user_id:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
            self.connected_users.add(user_id)
    
    def disconnect(self, websocket: WebSocket, user_id: str = None):
        """Disconnect a WebSocket client"""
        self.all_connections.remove(websocket)
        
        if user_id and user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # If no more connections for this user, remove the user entry
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                self.connected_users.remove(user_id)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client"""
        await websocket.send_text(json.dumps(message))
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients"""
        for connection in self.all_connections:
            await connection.send_text(json.dumps(message))
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast a message to all connections of a specific user"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(json.dumps(message))

# Create a single instance of the connection manager
manager = ConnectionManager()

# Endpoint to get the total like counts from the database
async def get_likes_count(db: Session) -> Dict[str, int]:
    """Get the total likes count for all users"""
    users = db.query(User).filter(User.is_active == True).all()
    result = {}
    
    for user in users:
        like_count = db.query(PeerReview).filter(
            PeerReview.employee_id == user.id,
            PeerReview.liked == True
        ).count()
        result[user.id] = like_count
    
    return result

@router.websocket("/likes")
async def websocket_likes(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time like updates
    """
    # Extract user_id from query parameters if provided
    user_id = websocket.query_params.get("user_id")
    
    # Accept the connection
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial likes count to the client
        likes_count = await get_likes_count(db)
        await manager.send_personal_message(
            {
                "type": "initial_data",
                "data": likes_count,
                "timestamp": datetime.now().isoformat()
            }, 
            websocket
        )
        
        # Keep the connection alive and handle incoming messages
        while True:
            # Wait for any message from the client (can be used for ping/pong)
            data = await websocket.receive_text()
            
            # Simple echo for debugging
            if data == "ping":
                await manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.now().isoformat()}, 
                    websocket
                )
    except WebSocketDisconnect:
        # Clean up on disconnect
        manager.disconnect(websocket, user_id)

# Function to be called when a new like is created
async def broadcast_like_update(employee_id: str, liked: bool):
    """
    Broadcast a like update to all connected clients.
    Call this function when a new like is created or removed.
    """
    await manager.broadcast({
        "type": "like_update",
        "data": {
            "employee_id": employee_id,
            "liked": liked,
            "timestamp": datetime.now().isoformat()
        }
    })

# Background task to periodically update connected clients
@router.on_event("startup")
async def start_periodic_updates():
    """
    Start a background task that periodically updates all connected clients
    with the latest like counts
    """
    async def periodic_update():
        while True:
            try:
                # Wait for 30 seconds between updates
                await asyncio.sleep(30)
                
                # Skip if no connections
                if not manager.all_connections:
                    continue
                
                # Get latest counts and broadcast
                async with next(get_db()) as db:
                    likes_count = await get_likes_count(db)
                    await manager.broadcast({
                        "type": "periodic_update",
                        "data": likes_count,
                        "timestamp": datetime.now().isoformat(),
                        "active_users": len(manager.connected_users)
                    })
            except Exception as e:
                print(f"Error in periodic update: {e}")
    
    # Start the background task
    asyncio.create_task(periodic_update()) 