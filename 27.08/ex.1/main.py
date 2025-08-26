
from fastapi import FastAPI, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from db import get_db, Animal
from typing import List
from pydantic import BaseModel

app = FastAPI()


class AnimalResponse(BaseModel):
    id: int
    name: str
    age: int
    adopted: bool

    class Config:
        orm_mode = True


@app.get("/animals", response_model=List[AnimalResponse])
async def read_animals(
        skip: int = 0,
        limit: int = Query(default=10, ge=1, le=100),
        db: Session = Depends(get_db)
):
    animals = db.query(Animal).offset(skip).limit(limit).all()
    return animals


@app.get("/animals/{animal_id}", response_model=AnimalResponse)
async def read_animal(
        animal_id: int = Path(..., gt=0, description="ID of animal that you want to look."),
        db: Session = Depends(get_db)
):
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if animal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Animal not found.")
    return animal


@app.get("/animals/check_age/{animal_id}")
async def check(
        animal_id: int = Path(..., gt=0, description="ID of animal that you want to look."),
        db: Session = Depends(get_db)
):

    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if animal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Animal not found.')
    if animal.age < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Age cannot be negative.')
    return {"message": "Animal is ready for adoption."}
