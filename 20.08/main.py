
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from db import get_db, Participant

app = FastAPI()


class ParticipantCreate(BaseModel):
    name: str
    email: EmailStr
    event: str
    age: int

    @field_validator('name')
    def no_digits_in_name(cls, v):
        if any(ch.isdigit() for ch in v):
            raise ValueError('Name must not contain digits')
        return v

    @field_validator('age')
    def check_age(cls, v):
        if not (12 <= v <= 120):
            raise ValueError('Age must be between 12 and 120')
        return v

class ParticipantResponse(BaseModel):
    id: int
    name: str
    email: str
    event: str
    age: int

    class Config:
        from_attributes = True


@app.post('/participants/', response_model=ParticipantResponse, status_code=201)
def create_participant(participant: ParticipantCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(Participant).where(Participant.email == participant.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=422, detail='Email already exists')

    new_participant = Participant(**participant.model_dump())
    db.add(new_participant)
    db.commit()
    db.refresh(new_participant)
    return new_participant

@app.get('/participants/event/{event_name}', response_model=list[ParticipantResponse])
def get_participants(event_name: str, db: Session = Depends(get_db)):
    participants = db.execute(select(Participant).where(Participant.event == event_name)).scalars().all()
    return participants
