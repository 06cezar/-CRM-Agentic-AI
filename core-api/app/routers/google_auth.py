from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from app.database import get_db
from app.models import User
from app.google_auth import get_google_auth_url, SCOPES
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/auth/google", tags=["Google Authentication"])
REDIRECT_URI = f"{settings.frontend_url}/api/auth/google/callback"
@router.get("/login")
def google_login(response: Response):
    """
    Frontend-ul apeleaza acest endpoint pentru a primi URL-ul.
    """
    auth_url, code_verifier = get_google_auth_url()
    
    
    response.set_cookie(
        key="code_verifier",
        value=code_verifier,
        httponly=True,
        samesite="lax",
        max_age=300, # 5 minute
        secure=False # Pune True doar daca ai HTTPS
    )
    
    return {"auth_url": auth_url}
    

@router.get("/callback")
def google_callback(
    code: str, 
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
        
):
    """
    Dupa logare, Google face redirect inapoi aici, atasand parametrul ?code=...
    """
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        code_verifier = request.cookies.get("code_verifier")
        print(f"==== PAROLA EXTRASA DIN COOKIE ESTE: {code_verifier} ====")
        flow = Flow.from_client_secrets_file(
            settings.google_secrets_path,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Schimbam codul temporar primit de la Google pe token-uri reale de acces
        flow.fetch_token(code=code, code_verifier=code_verifier)
        credentials = flow.credentials

        # Salvam Refresh Token-ul in Postgres.
        if credentials.refresh_token:
            current_user.google_refresh_token = credentials.refresh_token
            db.commit()

        return {"status": "success", "message": "Contul de Gmail a fost conectat si token-ul a fost salvat."}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Eroare la procesarea callback-ului: {str(e)}")