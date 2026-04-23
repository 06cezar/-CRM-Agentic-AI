from app.database import SessionLocal
from app import models
from app.models import User, Lead


def seed():
    db = SessionLocal()
    try:
        first_user = db.query(User).filter(User.email == "stefan.salcianu26@gmail.com").first()
        if not first_user:
            first_user = db.query(User).first()
            if first_user:
                print(f"⚠️ Nu am găsit userul specific. Folosesc primul user din DB: {first_user.email}")
            else:
                print("❌ Eroare: Nu am găsit niciun utilizator în baza de date.")
                return

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


def seed_activities():
    db = SessionLocal()
    try:
        first_user = db.query(User).filter(User.email == "stefan.salcianu26@gmail.com").first()
        if not first_user:
            first_user = db.query(User).first()
        if not first_user:
            print("❌ Eroare: Nu am găsit niciun utilizator în baza de date.")
            return

        existing = db.query(models.Activity).filter(models.Activity.user_id == first_user.id).count()
        if existing > 0:
            print(f"✅ Există deja {existing} activități pentru {first_user.email}. Ne oprim.")
            return

        leads = db.query(Lead).filter(Lead.owner_id == first_user.id).all()

        def lead_id(index):
            return leads[index % len(leads)].id if leads else None

        def lead_name(index):
            return leads[index % len(leads)].name if leads else "Unknown"

        dummy_activities = [
            models.Activity(lead_id=lead_id(0), user_id=first_user.id, action_type="lead_created",    description=f"Created new lead: {lead_name(0)}"),
            models.Activity(lead_id=lead_id(1), user_id=first_user.id, action_type="ai_insight",      description=f"Identified decision maker at {lead_name(1)}"),
            models.Activity(lead_id=lead_id(2), user_id=first_user.id, action_type="email_received",  description=f"Received reply from {lead_name(2)}"),
            models.Activity(lead_id=lead_id(3), user_id=first_user.id, action_type="status_change",   description=f"Lead {lead_name(3)} moved to 'warm'"),
            models.Activity(lead_id=lead_id(4), user_id=first_user.id, action_type="ai_insight",      description=f"Detected buying signal from {lead_name(4)}"),
            models.Activity(lead_id=lead_id(0), user_id=first_user.id, action_type="email_received",  description=f"Follow-up email opened by {lead_name(0)}"),
            models.Activity(lead_id=lead_id(1), user_id=first_user.id, action_type="status_change",   description=f"Lead {lead_name(1)} moved to 'hot'"),
            models.Activity(lead_id=lead_id(2), user_id=first_user.id, action_type="lead_created",    description=f"Created new lead: {lead_name(2)}"),
            models.Activity(lead_id=lead_id(3), user_id=first_user.id, action_type="ai_insight",      description=f"Company news alert for {lead_name(3)}"),
            models.Activity(lead_id=lead_id(4), user_id=first_user.id, action_type="email_received",  description=f"Inbound inquiry from {lead_name(4)}"),
        ]

        db.add_all(dummy_activities)
        db.commit()
        print(f"✅ Inserted {len(dummy_activities)} dummy activities for {first_user.email}.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    seed_activities()
