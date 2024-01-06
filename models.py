from typing import Any
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.models import Model
from tortoise import fields
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    email = fields.CharField(max_length=50, unique=True)
    password = fields.CharField(max_length=250)
    first_name = fields.CharField(max_length=50, null=True)
    last_name = fields.CharField(max_length=50, null=True)
    joined = fields.DatetimeField(auto_now_add=True)
    
    @classmethod
    async def create(cls: type[Model], using_db: BaseDBAsyncClient | None = None, **kwargs: Any) -> Model:
        kwargs['password'] = pwd_context.hash(kwargs['password'])
        return await super().create(using_db, **kwargs)
    
    def set_password(self, password: str):
        password_hashed = pwd_context.hash(password)
        self.password = password_hashed
    
    def check_password(self, password: str):
        return pwd_context.verify(password, self.password)
    
    class PydanticMeta:
        exclude = ('password',)

class Chat(Model):
    users = fields.ManyToManyField("models.User")
    is_private = fields.BooleanField(default=True)

class Message(Model):
    user = fields.ForeignKeyField("models.User", related_name="user")
    chat = fields.ForeignKeyField("models.Chat", related_name="chat")
    text = fields.TextField()
    utcDate = fields.DatetimeField(auto_now_add=True)