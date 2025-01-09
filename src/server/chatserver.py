import socket
import threading
import json
import time
from database import Database
from collections import defaultdict
import random
import string

class ChatServer:
    def __init__(self, host='127.0.0.1', port=55555, gui_callback=None):
        # Initialize main socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setblocking(False)
        # Initialize polling socket
        self.poll_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.poll_server.setblocking(False)

        self.clientAccess = threading.Lock()
        
        try:
            self.server.bind((host, port))
            self.poll_server.bind((host, port + 1))  # Use port+1 for polling
            
            self.server.listen(5)
            self.poll_server.listen(5)
            
            print(f"Main server initialized on {host}:{port}")
            print(f"Poll server initialized on {host}:{port+1}")
            
            # Initialize other attributes
            self.clients = {}  # {bind_str: {poll_client: (username, client)}}
            self.db = Database()
            self.running = True
            self.gui_callback = gui_callback

            
            
        except Exception as e:
            print(f"Server initialization error: {e}")
            raise e


    def disconnect_user(self, bindString) -> None:
        # calling this function you should already have the lock

        if self.clients[bindString][self.clients[bindString]]: # will be set to None if GameSocket never connected
            self.clients[bindString][self.clients[bindString]].close()
    
        self.clients[bindString].close()
    
        del self.clients[bindString][self.clients[bindString]] # free {bindStr: {poll_client: (username, client)}}
        del self.clients[bindString] # free {bindStr: {poll_client: None}}

    def authenticate_client(self, client):
        """Handle client authentication process"""
        try:
            data = client.recv(1024).decode('utf-8')
            
            if not data or ':' not in data:
                self.log_traffic("Invalid authentication message format")
                return None
                
            command, params_str = data.split(':', 1)
            print(f"Command: {command}, Params: {params_str}")
            
            try:
                params = json.loads(params_str)
            except json.JSONDecodeError:
                self.log_traffic("Invalid JSON in authentication message")
                return None
                
            if command == 'LOGIN':
                if self.db.verify_user(params['username'], params['password']):
                    client.send('AUTH_SUCCESS'.encode('utf-8'))
                    self.log_traffic(f"User logged in: {params['username']}")
                    return params['username']
                else:
                    client.send('AUTH_FAIL'.encode('utf-8'))
                    self.log_traffic(f"Failed login attempt: {params['username']}")
                    
            elif command == 'REGISTER':
                if self.db.create_user(params['username'], params['password']):
                    client.send('REG_SUCCESS'.encode('utf-8'))
                    self.log_traffic(f"New user registered: {params['username']}")
                    return params['username']
                else:
                    client.send('REG_FAIL'.encode('utf-8'))
                    self.log_traffic(f"Failed registration: {params['username']}")
                    
        except Exception as e:
            self.log_traffic(f"Authentication error: {e}")
            try:
                client.send('AUTH_ERROR'.encode('utf-8'))
            except:
                pass
            return None

        return None
    
    def generate_random_string(length=8):
        letters = string.ascii_letters + string.digits
        return ''.join(random.choice(letters) for i in range(length))

    def start(self):
        self.log_traffic("Server started")
        
        # Start polling socket acceptor thread
        poll_thread = threading.Thread(target=self.handle_poll_connections)
        poll_thread.daemon = True
        poll_thread.start()

        # check for clients that were not able to send data quick enough
        check = []

        # Accecpt both kinds of sockets in the main loop, first accept a poll socket
        while self.running:
            
            client, address = self.poll_server.accept()
            if client or address:
                random_string = self.generate_random_string()
                client.send(("AUTH: " + random_string).encode('utf-8'))
                with self.clientAccess:
                    self.clients[random_string] = {client: None}
                    self.log_traffic(f"Poll client connected: {address} with bind string: {random_string}")

            client, address = self.server.accept()
            if client or address:
                data = client.recv(1024).decode('utf-8')
                if ':' in data:
                    command, data = data.split(':', 1)
                    if command == 'AUTH':
                        if data in self.clients:
                            with self.clientAccess:
                                self.clients[data][self.clients[data]] = client   
                                self.log_traffic(f"Client, pollSocket and messageSocket bound: {data}")         
    
            elif client and not data: # connected to server, but was not able to send data quick enough
                check.append(client)

            for client in check: # check for clients that were not able to send data quick enough
                data = self.server.recv(1024).decode('utf-8')
                if ':' in data:
                    command, data = data.split(':', 1)
                    if command == 'AUTH':
                        if data in self.clients:
                            with self.clientAccess:
                                self.clients[data][self.clients[data]] = client
                                self.log_traffic(f"Client, pollSocket and messageSocket bound: {data}")             

            
            time.sleep(0.25) # run 4 times a second


    def handle_poll_connections(self):
        """Handle incoming polling connections"""
        while self.running: #! Might change to True
            check = []
            
            with self.clientAccess:
                for bindString in self.clients.values():
                    bindString.send("POLL: KEEP-ALIVE".encode('utf-8'))
                    bindString.append(bindString)

            time.sleep(1.5)

            with self.clientAccess:
                for bindString in check:
                    bindString.setBlocking(False)
                    data = bindString.recv(1024).decode('utf-8')
                    if data != "ALIVE":
                        self.disconnect_user(bindString)

            time.sleep(1.5)

                

    def stop(self):
        self.running = False
        for username in list(self.client_pairs.keys()):
            self.disconnect_user(username)
        self.server.close()
        self.poll_server.close()
        self.log_traffic("Server stopped")

    def log_traffic(self, message):
        if self.gui_callback:
            self.gui_callback(message)

    def broadcast(self, message, chat_id=None, sender=None):
        message_data = {
            'chat_id': chat_id,
            'username': sender if sender else "Server",
            'content': message if isinstance(message, str) else message.decode('utf-8')
        }
        json_message = json.dumps(message_data).encode('utf-8')
        
        for client in self.clients:
            client.send(json_message)
        
        self.log_traffic(f"Broadcast: {message_data['username']} -> {message_data['content']}")

    def handle_chat_creation(self, client, data):
        try:
            data = json.loads(data)
            chat_id = self.db.create_chat(
                data['creator'],
                data['target'],
                data['is_group']
            )
            client.send(f'CHAT_CREATED:{chat_id}'.encode('utf-8'))
            self.log_traffic(f"Chat created: {data['creator']} with {data['target']}")
        except Exception as e:
            client.send('CHAT_ERROR'.encode('utf-8'))
            self.log_traffic(f"Chat creation error: {e}")

    def handle_get_chats(self, client, username):
        try:
            chats = self.db.get_user_chats(username)
            client.send(json.dumps(chats).encode('utf-8'))
            self.log_traffic(f"Sent chat list to: {username}")
        except Exception as e:
            self.log_traffic(f"Error getting chats: {e}")

    def handle_get_messages(self, client, chat_id):
        try:
            messages = self.db.get_chat_messages(chat_id)
            client.send(json.dumps(messages).encode('utf-8'))
            self.log_traffic(f"Sent message history for chat: {chat_id}")
        except Exception as e:
            self.log_traffic(f"Error getting messages: {e}")

    def handle(self, client):
        while True:
            try:
                message = client.recv(1024).decode('utf-8')
                if not message:
                    raise Exception("Client disconnected")

                if ':' in message:
                    command, data = message.split(':', 1)
                    if command == 'CREATE_CHAT':
                        self.handle_chat_creation(client, data)
                    elif command == 'GET_CHATS':
                        self.handle_get_chats(client, data)
                    elif command == 'GET_MESSAGES':
                        self.handle_get_messages(client, data)
                    elif command == 'MESSAGE':
                        msg_data = json.loads(data)
                        self.db.save_message(
                            msg_data['username'],
                            msg_data['content'],
                            msg_data['chat_id']
                        )
                        self.broadcast(msg_data['content'], 
                                     msg_data['chat_id'], 
                                     msg_data['username'])
                self.log_traffic(f"Handled message: {message[:50]}...")
            except Exception as e:
                if client in self.clients:
                    username = self.clients[client]
                    del self.clients[client]
                    client.close()
                    self.broadcast(f"{username} left the chat!")
                    self.log_traffic(f"Client disconnected: {username}")
                break
