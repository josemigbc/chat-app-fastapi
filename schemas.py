from pydantic import BaseModel, ConfigDict
from datetime import datetime

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    username: str
    email:str
    first_name: str | None
    last_name: str | None

class UserCreation(UserBase):
    """
    Pydantic Model to create a new User
    """
    password: str

class UserLogin(BaseModel):
    """
    Pydantic Model to login a User
    """
    username: str
    password: str

class UserOut(UserBase):
    """
    Pydantic Model to serve an User information.
    """
    id: int
    joined: datetime
    
class MessageBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user: UserOut
    chat_id: int
    text: str

class MessageCreation(MessageBase):
    """
    Pydantic Model to create a new Message
    """
    user: str

class MessageOut(MessageBase):
    """
    Pydantic Model to serve an Message information.
    """
    utcDate: datetime

class ChatBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    users: list[UserOut]
    is_private: bool = True

class ChatCreation(ChatBase):
    """
    Pydantic Model to create a new Chat
    """
    users: list[str]

class ChatList(ChatBase):
    """
    Pydantic Model to serve an Chat information in a list of Chat.
    """
    id: int
    last_message: MessageOut | None = None

class ChatOut(ChatBase):
    """
    Pydantic Model to serve an Chat information.
    """
    id: int
    messages: list[MessageOut]