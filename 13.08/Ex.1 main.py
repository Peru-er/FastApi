
from pydantic import BaseModel, EmailStr, field_validator, ValidationError

class User(BaseModel):
    username: str
    email: EmailStr

    @field_validator('username')
    @classmethod
    def no_spaces(cls, v: str) -> str:
        if ' ' in v:
            raise ValueError('Username must not contain spaces')
        return v


try:
    user = User(username='Nick Wild', email='NickWild.email.com')
except ValidationError as e:
    print(e.json())
