

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

users = []

class UserList(BaseModel):
    names: List[str]

def add_user(name: str):
    if name in users:
        raise HTTPException(status_code=400, detail=f"User '{name}' already exist.")
    users.append(name)

@app.post("/users/")
def create_users(user_list: UserList):
    added = []
    already_exist = []

    for name in user_list.names:
        if name in users:
            already_exist.append(name)
        else:
            users.append(name)
            added.append(name)

    return {
        "added": added,
        "already_exist": already_exist,
        "users_now": users
    }

@app.get("/users/")
def get_users():
    return {"users": users}

@app.delete("/users/{name}/")
def delete_user(name: str):
    if name not in users:
        raise HTTPException(status_code=404, detail="User not fount")
    users.remove(name)
    return {"message": f"User '{name}' delete successes."}


