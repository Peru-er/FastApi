
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import smtplib
import os
import traceback

app = FastAPI(title='Messaging API with Background Email Sender')
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/first_db"
)

engine = create_engine(DATABASE_URL, connect_args={
    "check_same_thread": False} if DATABASE_URL.startswith('sqlite') else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
Base.metadata.create_all(bind=engine)


class ActionLog(Base):
    __tablename__ = 'action_logs'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(128), nullable=True)
    action_type = Column(String(128), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)


class EmailLog(Base):
    __tablename__ = 'email_logs'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(128), nullable=True)
    to_email = Column(String(256), nullable=False)
    subject = Column(String(256), nullable=True)
    body = Column(Text, nullable=True)
    status = Column(String(64), default='pending')
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

class EmailRequest(BaseModel):
    user_id: str | None = None
    to_email: EmailStr
    subject: str
    body: str


class GenericResponse(BaseModel):
    detail: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_action(db: Session, user_id: str | None, action_type: str, details: str | None = None, success: bool = True):
    entry = ActionLog(user_id=user_id, action_type=action_type, details=details, success=success)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def send_smtp_email(to_email: str, subject: str, body: str) -> None:
    SMTP_HOST = os.environ.get('SMTP_HOST', 'localhost')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 25))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASS = os.environ.get('SMTP_PASS')
    SMTP_FROM = os.environ.get('SMTP_FROM', 'no-reply@example.com')

    message = f"From: {SMTP_FROM}\r\nTo: {to_email}\r\nSubject: {subject}\r\n\r\n{body}"

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
    try:
        server.ehlo()
        if os.environ.get('SMTP_STARTTLS', 'false').lower() in ('1', 'true', 'yes'):
            server.starttls()
            server.ehlo()
        if SMTP_USER and SMTP_PASS:
            server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, [to_email], message.encode('utf-8'))
    finally:
        server.quit()

def background_send_email(email_log_id: int):
    db = SessionLocal()
    try:
        email = db.query(EmailLog).filter(EmailLog.id == email_log_id).first()
        if not email:
            return

        try:
            send_smtp_email(email.to_email, email.subject or '(no subject)', email.body or '')
            email.status = 'sent'
            email.sent_at = datetime.utcnow()
            email.error = None
            db.add(email)
            db.commit()
            log_action(db, email.user_id, 'email_sent', f'Email id={email.id} to={email.to_email}', success=True)
        except Exception as e:
            tb = traceback.format_exc()
            email.status = 'failed'
            email.error = tb
            db.add(email)
            db.commit()
            log_action(db, email.user_id, 'email_send_failed', f'Email id={email.id} '
                                                               f'to={email.to_email} error={str(e)}', success=False)
    finally:
        db.close()


#endpoints

@app.post('/send-email', response_model=GenericResponse, status_code=202)
def send_email_endpoint(payload: EmailRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email_log = EmailLog(user_id=payload.user_id, to_email=str(payload.to_email),
                         subject=payload.subject, body=payload.body, status='pending')
    db.add(email_log)
    db.commit()
    db.refresh(email_log)
    log_action(db, payload.user_id, 'email_send_requested', f'Email id={email_log.id} '
                                                            f'to={payload.to_email}', success=True)
    background_tasks.add_task(background_send_email, email_log.id)

    return {'detail': 'Request to send a letter accepted.'}


@app.get('/email-logs')
def list_email_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(EmailLog).order_by(EmailLog.created_at.desc()).limit(limit).all()
    return [{
        'id': l.id,
        'user_id': l.user_id,
        'to_email': l.to_email,
        'subject': l.subject,
        'status': l.status,
        'error': (l.error[:500] + '...') if l.error and len(l.error) > 500 else l.error,
        'created_at': l.created_at.isoformat(),
        'sent_at': l.sent_at.isoformat() if l.sent_at else None
    } for l in logs]


@app.get('/actions')
def list_actions(limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(ActionLog).order_by(ActionLog.timestamp.desc()).limit(limit).all()
    return [{
        'id': a.id,
        'user_id': a.user_id,
        'action_type': a.action_type,
        'details': a.details,
        'success': a.success,
        'timestamp': a.timestamp.isoformat()
    } for a in logs]


@app.get('/health')
def health():
    return {'status': 'ok'}
