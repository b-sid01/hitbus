from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_connection
from app.utils.tokens import decode_access_token
import uuid

router = APIRouter(prefix="/ideas", tags=["Ideas"])

class IdeaSubmitRequest(BaseModel):
    title: str
    problem_statement: str
    target_audience: str
    industry_category: Optional[str] = None
    stage: str = "concept"

def get_current_user(authorization: str):
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_access_token(token)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/submit")
def submit_idea(data: IdeaSubmitRequest, authorization: str = Header(...)):
    user = get_current_user(authorization)

    if user["role"] not in ("founder", "both"):
        raise HTTPException(status_code=403, detail="Only founders can submit ideas")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get founder_id from user_id
        cursor.execute("SELECT founder_id FROM founder_profiles WHERE user_id = %s", (user["sub"],))
        founder = cursor.fetchone()

        if not founder:
            raise HTTPException(status_code=404, detail="Founder profile not found")

        idea_id = str(uuid.uuid4())
        closes_at = datetime.utcnow() + timedelta(days=21)

        cursor.execute("""
            INSERT INTO ideas (idea_id, founder_id, title, problem_statement, target_audience, industry_category, stage, closes_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (idea_id, founder["founder_id"], data.title, data.problem_statement,
              data.target_audience, data.industry_category, data.stage, closes_at))

        # Update founder ideas count
        cursor.execute("UPDATE founder_profiles SET ideas_submitted = ideas_submitted + 1 WHERE founder_id = %s",
                       (founder["founder_id"],))

        conn.commit()

        return {
            "message": "Idea submitted successfully",
            "idea_id": idea_id,
            "closes_at": closes_at,
            "status": "active"
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/list")
def list_ideas(authorization: str = Header(...)):
    get_current_user(authorization)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT idea_id, title, target_audience, industry_category,
                   stage, status, demand_score, validation_count, created_at, closes_at
            FROM ideas
            WHERE status = 'active'
            ORDER BY demand_score DESC
            LIMIT 50
        """)
        ideas = cursor.fetchall()
        return {"ideas": ideas, "count": len(ideas)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/{idea_id}")
def get_idea(idea_id: str, authorization: str = Header(...)):
    get_current_user(authorization)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM ideas WHERE idea_id = %s", (idea_id,))
        idea = cursor.fetchone()

        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")

        return idea

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
