from fastapi import APIRouter, Depends, HTTPException, Request, Response, BackgroundTasks
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from app.database import get_db
from app.models import ConnectedAccount, User
#from app.google_auth import get_google_auth_url, SCOPES
from app.gmail_watch import update_gmail_watch_state, process_gmail_updates
from app.auth import get_current_user
from app.config import settings
from googleapiclient.discovery import build
import base64
import json
from pydantic import BaseModel
from typing import Optional

class WatchToggleRequest(BaseModel):
    account_id: int
    active: bool

router = APIRouter(prefix="/api/gmail", tags=["Gmail Watcher"])
REDIRECT_URI = f"{settings.frontend_url}/api/auth/google/callback"

@router.post("/watch")
def activate_gmail_watch(payload: WatchToggleRequest, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    """
    Endpoint pentru a porni / opri monitorizarea unui cont Gmail conectat.
    Frontend-ul apelează acest endpoint când utilizatorul dă click pe "Start Watch" sau "Stop Watch" în setări.
     - Dacă activează, se pornește monitorizarea și se salvează historyId inițial în DB.
     - Dacă dezactivează, se poate opri monitorizarea (opțional, Google nu are un endpoint dedicat pentru asta, dar putem ignora notificările primite ulterior).
     - Este important să verificăm că contul aparține utilizatorului curent pentru securitate.
    """


    
    
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    
    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.id == payload.account_id,
        ConnectedAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="No connected Google account found for this user")
    
    history_id = update_gmail_watch_state(account,db,  payload.active)
    
    if history_id is None:
        raise HTTPException(status_code=500, detail="Failed to set up Gmail watch")
    
    # Salvează historyId în baza de date pentru a ști de unde să începi când primești notificări
    account.last_history_id = history_id
    db.commit()
    
    return {"message": "Gmail watch set up successfully", "historyId": history_id}


@router.get("/status/{account_id}")
def get_watch_status(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Verifică statusul de monitorizare al unui cont.
    Nu modifică nicio stare, doar returnează valoarea curentă din DB.
    """
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.id == account_id,
        ConnectedAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return {"id": account.id, "is_watching": account.is_watching}


@router.post("/set-status")
def set_watch_status(payload: WatchToggleRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Actualizează statusul de monitorizare în baza de date.
    Creat ca funcție nouă pentru a nu modifica logica existentă de /watch.
    """
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.id == payload.account_id,
        ConnectedAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.is_watching = payload.active
    db.commit()
    
    return {"id": account.id, "is_watching": account.is_watching}

@router.post("/watch/{account_id}")
def restart_watch(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.id == account_id,
        ConnectedAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Contul nu a fost gasit")
    
    success = activate_gmail_account_watch(db, account)
    if not success:
        raise HTTPException(status_code=500, detail="Nu s-a putut reporni monitorizarea")
        
    return {"message": "Monitorizare repornita", "historyId": account.last_history_id}

