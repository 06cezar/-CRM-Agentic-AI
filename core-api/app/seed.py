from app.database import SessionLocal
from app import models
from app.database import SessionLocal
from app.models import User, Lead  # <--- ASTA LIPSEȘTE!


def seed():
    db = SessionLocal()
    try:
        # 1. Găsim user-ul tău specific după email; dacă nu există, folosim primul user
        first_user = db.query(User).filter(User.email == "stefan.salcianu26@gmail.com").first()
        if not first_user:
            first_user = db.query(User).first()
            if first_user:
                print(f"⚠️ Nu am găsit userul specific. Folosesc primul user din DB: {first_user.email}")
            else:
                print("❌ Eroare: Nu am găsit niciun utilizator în baza de date.")
                return

        # 2. Verificăm dacă ACEL user are deja lead-uri
        user_leads_count = db.query(Lead).filter(Lead.owner_id == first_user.id).count()
        if user_leads_count > 0:
            print(f"✅ Utilizatorul {first_user.email} are deja {user_leads_count} lead-uri. Ne oprim.")
            return

        print(f"⏳ Populam cu lead-uri de test pentru {first_user.email}...")

        sample_leads = [
            models.Lead(
                name="Alice Smith",
                company="ACME Corp",
                email="alice.smith@example.com",
                status="hot",
                intent_score=94.5,
                deal_value=15000.0,
                owner_id=first_user.id,
            ),
            models.Lead(
                name="Bob Johnson",
                company="Beta LLC",
                email="bob.johnson@example.com",
                status="warm",
                intent_score=87.0,
                deal_value=8000.0,
                owner_id=first_user.id,
            ),
            models.Lead(
                name="Clara Martinez",
                company="Gamma Co",
                email="clara.m@example.com",
                status="cool",
                intent_score=73.2,
                deal_value=4200.0,
                owner_id=first_user.id,
            ),
            models.Lead(
                name="Daniel Lee",
                company="Delta Inc",
                email="daniel.lee@example.com",
                status="warm",
                intent_score=65.4,
                deal_value=3000.0,
                owner_id=first_user.id,
            ),
            models.Lead(
                name="Eva Green",
                company="Epsilon Partners",
                email="eva.green@example.com",
                status="hot",
                intent_score=98.1,
                deal_value=22000.0,
                owner_id=first_user.id,
            ),
        ]

        db.add_all(sample_leads)
        db.commit()
        print(f"Inserted {len(sample_leads)} leads for user id {first_user.id}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
