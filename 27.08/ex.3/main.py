
from fastapi import FastAPI, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from db import get_db, Animal, Task
from typing import List
from pydantic import BaseModel
import logging


app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskResponse(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        orm_mode = True

class AnimalResponse(BaseModel):
    id: int
    name: str
    age: int
    adopted: bool
    health_status: str

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


@app.get('/tasks/{task_id}', response_model=TaskResponse)
async def check_task(
        task_id: int = Path(..., gt=0, description="ID of the task you want to check."),
        db: Session = Depends(get_db)
):
    if task_id > 1000:
        logger.error(f"Invalid task_id: {task_id}. Must be <= 1000.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='task_id cannot be greater than 1000.'
        )

    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        logger.error(f"Task with id={task_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Task not found.'
        )

    return task
