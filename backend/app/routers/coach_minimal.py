"""
Minimal Coach API endpoints for testing
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coach", tags=["coach"])

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "coach"}

@router.websocket("/ws")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    Basic WebSocket endpoint for chat functionality
    """
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Send welcome message
        welcome_message = {
            "type": "response",
            "data": {
                "answer": "Hello! I'm your AI coach. I'm ready to help you learn software architecture patterns. However, full functionality requires API keys to be configured.",
                "confidence": 1.0,
                "contextUsed": [],
                "hints": ["Add OPENAI_API_KEY to your .env file for full AI functionality"],
                "suggestedActions": ["Try asking me about software architecture patterns"],
                "needsMoreContext": False,
                "languageAdapted": False
            }
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                message_data = message.get("data", {})
                
                if message_type == "question":
                    # Simple echo response for now
                    question = message_data.get("question", "")
                    
                    response_message = {
                        "type": "response",
                        "data": {
                            "answer": f"I received your question: '{question}'. To provide detailed architectural guidance, please configure your OpenAI API key in the .env file.",
                            "confidence": 0.5,
                            "contextUsed": [],
                            "hints": ["Configure OPENAI_API_KEY for full functionality"],
                            "suggestedActions": ["Add API keys to .env file", "Try the REST API endpoints"],
                            "needsMoreContext": False,
                            "languageAdapted": False
                        }
                    }
                    
                    await websocket.send_text(json.dumps(response_message))
                    
                else:
                    # Unknown message type
                    error_response = {
                        "type": "error",
                        "data": {"message": f"Unknown message type: {message_type}"}
                    }
                    await websocket.send_text(json.dumps(error_response))
                    
            except json.JSONDecodeError:
                error_response = {
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }
                await websocket.send_text(json.dumps(error_response))
                
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                error_response = {
                    "type": "error",
                    "data": {"message": "Internal server error"}
                }
                await websocket.send_text(json.dumps(error_response))
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")