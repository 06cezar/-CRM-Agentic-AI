from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from app.database import get_db
from app.models import ConnectedAccount, User
from app.google_auth import get_connected_accounts_by_user_id, get_google_auth_url, SCOPES
from app.auth import get_current_user
from app.config import settings
from googleapiclient.discovery import build
import base64
import json

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

    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        code_verifier = request.cookies.get("code_verifier")
        
        flow = Flow.from_client_secrets_file(
            settings.google_secrets_path,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Schimbam codul temporar primit de la Google pe token-uri reale de acces
        flow.fetch_token(code=code, code_verifier=code_verifier)
        credentials = flow.credentials
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        google_email = user_info.get("email")
        if not google_email:
            raise HTTPException(status_code=400, detail="Nu am putut obtine email-ul de Google")
        # Salvam Refresh Token-ul in Postgres.
        account = db.query(ConnectedAccount).filter(
            ConnectedAccount.user_id == current_user.id,
            ConnectedAccount.email == google_email
        ).first()
        
        if not account:
            """Daca nu avem deja un cont conectat cu acest email, cream unul nou."""
            if not credentials.refresh_token:
                # Google trimite refresh_token doar prima data cand user-ul da accept
                # Daca lipseste la o reconectare, inseamna ca trebuie sa revoci accesul din Google Settings
                raise HTTPException(status_code=400, detail="Lipseste Refresh Token. Revoca accesul aplicatiei din setarile Google si incearca iar.")
            account = ConnectedAccount(
                user_id=current_user.id,
                provider="google",
                email=google_email,
                refresh_token=credentials.refresh_token
            )
            db.add(account)
        else:
            # Daca exista deja, actualizam refresh_token-ul daca Google ni l-a trimis din nou
            if credentials.refresh_token:
                account.refresh_token = credentials.refresh_token
        
        db.commit()


        return {
            "status": "success", 
            "message": f"Contul {google_email} a fost conectat cu succes.",
            "google_email": google_email
        }
        
    except Exception as e:
        db.rollback()
        print(f"Eroare Callback: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Eroare la procesarea callback-ului: {str(e)}")
    
@router.get("/get_connected_accounts")
def get_connected_accounts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = get_connected_accounts_by_user_id(current_user.id)
    return [{"id": acc.id, "email": acc.email, "provider": acc.provider, "is_watching": acc.is_watching} for acc in accounts]