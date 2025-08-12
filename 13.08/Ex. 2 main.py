

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()

tasks = []
next_id = 1

class Task(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., max_length=200)


@app.get('/tasks/')
def get_tasks():
    return tasks

@app.get('/tasks/{task_id}')
def get_task(task_id: int):
    for task in tasks:
        if task['id'] == task_id:
            return task
    raise HTTPException(status_code=404, detail='Task not found')

@app.post('/tasks/', status_code=status.HTTP_201_CREATED)
def create_task(task: Task):
    global next_id
    task_data = {'id': next_id, **task.dict()}
    tasks.append(task_data)
    next_id += 1
    return task_data

@app.put('/tasks/{task_id}')
def update_task(task_id: int, updated_task: Task):
    for task in tasks:
        if task['id'] == task_id:
            task.update(updated_task.dict())
            return task
    raise HTTPException(status_code=404, detail='Task not found')

@app.delete('/tasks/{task_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    for index, task in enumerate(tasks):
        if task['id'] == task_id:
            del tasks[index]
            return
    raise HTTPException(status_code=404, detail='Task not found')

