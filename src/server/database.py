from pymongo import MongoClient
from bson import ObjectId
import bcrypt
from datetime import datetime

class Database:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['chat_app']
        self.users = self.db['users']
        self.messages = self.db['messages']
        self.chats = self.db['chats']
        
        # Create indexes
        self.users.create_index('username', unique=True)
        self.messages.create_index('chat_id')
        self.chats.create_index('participants')

    def create_user(self, username, password):
        try:
            user = {
                'username': username,
                'password': password,
                'created_at': datetime.now()
            }
            self.users.insert_one(user)
            return True
        except:
            return False

    def verify_user(self, username, password):
        user = self.users.find_one({'username': username})
        if user and user['password'] == password:
            return True
        return False

    def get_all_users(self):
        return list(self.users.find({}, {'username': 1, 'created_at': 1}))

    def create_chat(self, creator, participant, is_group=False, chat_name=None):
        chat = {
            'participants': [creator, participant],
            'is_group': is_group,
            'chat_name': chat_name if chat_name else f"{creator}-{participant}",
            'created_at': datetime.now(),
            'created_by': creator
        }
        result = self.chats.insert_one(chat)
        return str(result.inserted_id)

    def get_user_chats(self, username):
        chats = list(self.chats.find({'participants': username}))
        # Convert ObjectId to string for JSON serialization
        for chat in chats:
            chat['_id'] = str(chat['_id'])
        return chats

    def get_chat_messages(self, chat_id, limit=50):
        messages = self.messages.find({'chat_id': chat_id}).sort('timestamp', -1).limit(limit)
        messages_list = list(messages)
        # Convert ObjectId to string for JSON serialization
        for message in messages_list:
            message['_id'] = str(message['_id'])
        return list(reversed(messages_list))

    def save_message(self, username, content, chat_id):
        message = {
            'chat_id': chat_id,
            'username': username,
            'content': content,
            'timestamp': datetime.now()
        }
        self.messages.insert_one(message)


    def user_exists(self, username):
        return self.users.find_one({'username': username}) is not None
    
    def get_all_users(self):
        # Modified to include password field
        return list(self.users.find())

    def delete_all_users(self):
        # Delete all users from the database
        self.users.delete_many({})
        # Optionally, also delete related data
        self.chats.delete_many({})
        self.messages.delete_many({})