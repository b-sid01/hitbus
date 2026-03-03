from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.database import get_connection
from app.utils.hashing import hash_password
from app.utils.tokens import generate_verification_token, token_expiry
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    linkedin_url: str
    country_code: str
    role: str  # "founder", "validator", "both"

@router.post("/register")
def register(data: RegisterRequest):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check email already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Check LinkedIn already exists
        cursor.execute("SELECT user_id FROM users WHERE linkedin_url = %s", (data.linkedin_url,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="LinkedIn profile already linked to another account")

        # Validate role
        if data.role not in ("founder", "validator", "both"):
            raise HTTPException(status_code=400, detail="Invalid role")

        # Create user
        user_id = str(uuid.uuid4())
        hashed = hash_password(data.password)

        cursor.execute("""
            INSERT INTO users (user_id, email, password_hash, display_name, linkedin_url, country_code, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, data.email, hashed, data.display_name, data.linkedin_url, data.country_code, data.role))

        # Create role profiles
        if data.role in ("founder", "both"):
            cursor.execute("""
                INSERT INTO founder_profiles (founder_id, user_id)
                VALUES (%s, %s)
            """, (str(uuid.uuid4()), user_id))

        if data.role in ("validator", "both"):
            cursor.execute("""
                INSERT INTO validator_profiles (validator_id, user_id)
                VALUES (%s, %s)
            """, (str(uuid.uuid4()), user_id))

        # Generate email verification token
        token = generate_verification_token()
        token_id = str(uuid.uuid4())
        expires = token_expiry(hours=24)

        cursor.execute("""
            INSERT INTO email_verification_tokens (token_id, user_id, token, expires_at)
            VALUES (%s, %s, %s, %s)
        """, (token_id, user_id, token, expires))

        conn.commit()

        return {
            "message": "Registration successful. Please verify your email.",
            "user_id": user_id,
            "verification_token": token  # in production this goes via email, not response
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
