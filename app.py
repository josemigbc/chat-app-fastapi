from typing import Annotated


from fastapi import (Depends, FastAPI, Response, WebSocket,
                     WebSocketDisconnect, WebSocketException)
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise
from tortoise.exceptions import DoesNotExist
from db_config import TORTOISE_ORM

from auth import JWTBearer, create_jwt, verify_jwt
from models import User, Chat, Message
from schemas import UserCreation, UserLogin, UserOut, MessageCreation, MessageOut, ChatCreation, ChatList, ChatOut

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5500', 'http://localhost:3000'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# HTTP
# User


@app.post('/user', status_code=201, response_model=UserOut)
async def create_user(user_data: UserCreation):
    user = await User.create(**user_data.model_dump())
    return UserOut.model_validate(user)


@app.get('/user', response_model=UserOut)
async def get_user_by_id(user: Annotated[User, Depends(JWTBearer())]):
    return UserOut.model_validate(user)

@app.get('/user-list')
async def get_users(user: Annotated[User, Depends(JWTBearer())]):
    users_obj = await User.exclude(id=user.id)
    users = [UserOut.model_validate(user) for user in users_obj]
    return users


@app.post('/login')
async def login(credentials: UserLogin, response: Response) -> dict:
    user = await User.get(username=credentials.username)
    if user.check_password(credentials.password):
        token = create_jwt(user.username)
        return token
    response.status_code = 403
    return {"details": "User or password incorrect"}

# Messages


@app.get('/chats')
async def get_chats(user: Annotated[User, Depends(JWTBearer())]):
    chats = await Chat.filter(users=user)
    chats_list = []
    for chat in chats:
        users = [UserOut.model_validate(user) async for user in chat.users]
        
        last_message_obj = await Message.filter(chat=chat).order_by("-utcDate").first()
        
        last_message = MessageOut(
            user = UserOut.model_validate(await last_message_obj.user),
            chat_id = (await last_message_obj.chat).pk,
            text = last_message_obj.text,
            utcDate = last_message_obj.utcDate
        ) if last_message_obj else None
        
        chat_out = ChatList(
            id = chat.pk, 
            users = users,
            is_private = chat.is_private,
            last_message = last_message
        )
        chats_list.append(chat_out)
    
    return chats_list

@app.get('/chats/{chat_id}')
async def get_chat_by_id(chat_id: int, user: Annotated[User, Depends(JWTBearer())], response: Response):
    chat = await Chat.get_or_none(id=chat_id, users=user)
    if not chat:
        response.status_code = 404
        return
    users = [UserOut.model_validate(user_obj) async for user_obj in chat.users]
    messages = []
    for msg in await Message.filter(chat__id=chat_id):
        messages.append(MessageOut(
            user = UserOut.model_validate(await msg.user),
            chat_id = (await msg.chat).pk,
            text = msg.text,
            utcDate = msg.utcDate
        ))
        
    return ChatOut(
        id = chat.pk,
        users = users,
        is_private = chat.is_private,
        messages = messages,
    )

@app.post('/chats')
async def create_chat(chat: ChatCreation, user: Annotated[User, Depends(JWTBearer())], response: Response):
    if not user.username in chat.users:
        response.status_code = 403
        return
    
    chat_user1 = set(await Chat.filter(users__username=chat.users[0]))
    chat_user2 = set(await Chat.filter(users__username=chat.users[1]))
    chat_obj = None
    if chat_user1 and chat_user2:
        chats_intersection = chat_user1.intersection(chat_user2)
        chat_obj = min(chats_intersection, key=lambda x: x.pk) if chats_intersection else None

    if not chat_obj:
        chat_obj = await Chat.create(is_private=chat.is_private)
        for username in chat.users:
            user = await User.filter(username=username).first()
            await chat_obj.users.add(user)
    
    users = [UserOut.model_validate(user_obj) async for user_obj in chat_obj.users]
    messages = []
    for msg in await Message.filter(chat__id=chat_obj.pk):
        messages.append(MessageOut(
            user = UserOut.model_validate(await msg.user),
            chat_id = (await msg.chat).pk,
            text = msg.text,
            utcDate = msg.utcDate
        ))
        
    return ChatOut(
        id = chat_obj.pk,
        users = users,
        is_private = chat_obj.is_private,
        messages = messages,
    )


@app.post("/message")
async def create_message(message_data: MessageCreation):
    user = await User.get(username=message_data.user)
    chat = await Chat.get(id=message_data.chat_id)
    message = await Message.create(user=user, chat=chat, text=message_data.text)
    return MessageOut.model_validate(message)

# WebSockets

class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    async def add_user(self, websocket: WebSocket, user: User):
        self.active_connections[user.username] = websocket

    async def on_message(self, websocket: WebSocket, data: dict[str, str], user: User):

        try:
            chat = await Chat.get(id=data["chat_id"])
            message_obj = await Message.create(user=user, chat=chat, text=data["text"])
            
            user_to = await chat.users.all().exclude(id=user.id).first()
            conn = self.active_connections[user_to.username]
            await conn.send_text(MessageOut.model_validate(message_obj).model_dump_json())
            await websocket.send_json({"type": 'message', "response": "OK"})
        
        except DoesNotExist:
            await websocket.send_json({"type": 'message', "response": "User or chat does not exist"})
        
        except KeyError:
            await websocket.send_json({"type": 'message', "response": "Other user is not online."})

    def remove_connection(self, user):
        self.active_connections.pop(user.username, None)


ws_manager = WebSocketManager()


@app.websocket('/')
async def send_message(websocket: WebSocket, token: str):
    user = await verify_jwt(token)
    if not user:
        raise WebSocketException(code=1008)
    await websocket.accept()
    await ws_manager.add_user(websocket, user)
    try:
        while True:
            data = await websocket.receive_json()
            print(ws_manager.active_connections)
            if data["type"] == 'message':
                await ws_manager.on_message(websocket, data, user)

    except WebSocketDisconnect:
        ws_manager.remove_connection(user)

register_tortoise(app, config=TORTOISE_ORM,
                  generate_schemas=True, add_exception_handlers=True)
