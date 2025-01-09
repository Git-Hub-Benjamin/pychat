import json
import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time

host='127.0.0.1'
port=55555
poll_port=55556  # New port for polling connection

class ChatClient:
    def __init__(self):
        # Initialize main connection
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Initialize polling connection
        self.poll_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.connected = False
        self.logged_in = False
        self.username = None
        self.current_chat_id = None
        self.running = True  # Flag to control polling thread

        # Create main window
        self.root = tk.Tk()
        self.root.title("Chat Application")
        self.root.geometry("800x600")

        try:
            # Connect main socket
            self.client.connect((host, port))
            # Connect polling socket
            self.poll_socket.connect((host, poll_port))
            print("Connected to server successfully")
            self.connected = True
            
            # Start polling thread
            self.poll_thread = threading.Thread(target=self.poll_server)
            self.poll_thread.daemon = True
            self.poll_thread.start()
            
            self.show_login()  # Start with login screen
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            print(f"Connection error: {e}")
            messagebox.showerror("Connection Error", "Could not connect to server!")
            if hasattr(self, 'root'):
                self.root.destroy()

    def poll_server(self):
        """Thread function to handle server polling"""
        while self.running:
            try:
                # Try to receive keepalive message
                self.poll_socket.settimeout(2.0)  # Set timeout for receiving
                data = self.poll_socket.recv(1024).decode('utf-8')
                
                if data == "KEEP_ALIVE":
                    # Send acknowledgment
                    self.poll_socket.send("ALIVE".encode('utf-8'))
                elif data == "":
                    # Empty response means server disconnected
                    self.handle_disconnect()
                    break
                    
            except socket.timeout:
                # Timeout is normal, just continue
                pass
            except Exception as e:
                print(f"Polling error: {e}")
                self.handle_disconnect()
                break
                
            time.sleep(1)  # Sleep for performance

    def handle_disconnect(self):
        """Handle server disconnection"""
        self.connected = False
        if self.logged_in:
            # Show error in GUI thread
            self.root.after(0, lambda: messagebox.showerror("Error", "Lost connection to server"))
            self.root.after(0, self.show_login)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.running = False  # Stop polling thread
            try:
                self.client.close()
                self.poll_socket.close()
            except:
                pass
            self.root.quit()
            self.root.destroy()

    def login(self, username, password):
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields")
            return

        try:
            # Try reconnecting if needed
            if not self.connected:
                try:
                    self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.poll_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.client.connect((host, port))
                    self.poll_socket.connect((host, poll_port))
                    self.connected = True
                except Exception as e:
                    messagebox.showerror("Connection Error", "Could not connect to server: " + str(e))
                    return

            login_data = {
                'username': username,
                'password': password
            }
            message = f"LOGIN:{json.dumps(login_data)}"
            self.client.send(message.encode('utf-8'))
            
            response = self.client.recv(1024).decode('utf-8')
            print("Response from server: ", response)
            
            if response == 'AUTH_SUCCESS':
                self.logged_in = True
                self.username = username
                self.show_chat_selection_screen()
            else:
                messagebox.showerror("Error", "Invalid credentials")
        except Exception as e:
            self.connected = False
            messagebox.showerror("Login Error", str(e))

    def show_signup(self):
        self.clear_window()
        
        signup_frame = ttk.Frame(self.root, padding="20")
        signup_frame.pack(expand=True)
        
        ttk.Label(signup_frame, text="Sign Up", font=('Arial', 20, 'bold')).pack(pady=10)
        
        # Username
        ttk.Label(signup_frame, text="Username:", font=('Arial', 12)).pack(pady=(10,0))
        username_entry = ttk.Entry(signup_frame, font=('Arial', 12))
        username_entry.pack(pady=(0,10), padx=20, fill=tk.X)
        
        # Password
        ttk.Label(signup_frame, text="Password:", font=('Arial', 12)).pack(pady=(10,0))
        password_entry = ttk.Entry(signup_frame, show="•", font=('Arial', 12))
        password_entry.pack(pady=(0,10), padx=20, fill=tk.X)
        
        # Buttons
        ttk.Button(signup_frame, text="Sign Up",
                command=lambda: self.register(username_entry.get(), password_entry.get())).pack(pady=10)
        ttk.Button(signup_frame, text="Back to Login", 
                command=self.show_login).pack(pady=5)

    def register(self, username, password):
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields")
            return

        try:
            # Create registration data and send to server
            register_data = {
                'username': username,
                'password': password
            }
            message = f"REGISTER:{json.dumps(register_data)}"
            self.client.send(message.encode('utf-8'))
            
            # Wait for server response
            response = self.client.recv(1024).decode('utf-8')
            print("Response from server: ", response)
            
            if response == 'REG_SUCCESS':
                messagebox.showinfo("Success", "Registration successful!")
                self.show_login()
            elif response == 'REG_FAIL':
                messagebox.showerror("Error", "Username already exists")
            else:
                messagebox.showerror("Error", "Registration failed")
                
        except Exception as e:
            messagebox.showerror("Registration Error: ", str(e))

    def show_chat_selection_screen(self):
        self.clear_window()
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top bar with user info and create chat button
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_frame, text=f"Logged in as: {self.username}", 
                font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(top_frame, text="Create New Chat", 
                command=self.show_create_chat_dialog).pack(side=tk.RIGHT)
        
        # Chat list frame
        list_frame = ttk.LabelFrame(main_frame, text="Your Chats", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Placeholder text for now
        ttk.Label(list_frame, text="No chats yet").pack(pady=20)
        
        # Bottom buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(bottom_frame, text="Logout", 
                command=self.logout).pack(side=tk.RIGHT)

    def clear_window(self):
        """Clears all widgets from the current window"""
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_window()  # Clear existing widgets
        login_frame = ttk.Frame(self.root, padding="20")
        login_frame.pack(expand=True)
        
        ttk.Label(login_frame, text="Login", font=('Arial', 20, 'bold')).pack(pady=10)
        
        # Username
        ttk.Label(login_frame, text="Username:", font=('Arial', 12)).pack(pady=(10,0))
        username_entry = ttk.Entry(login_frame, font=('Arial', 12))
        username_entry.pack(pady=(0,10), padx=20, fill=tk.X)
        
        # Password
        ttk.Label(login_frame, text="Password:", font=('Arial', 12)).pack(pady=(10,0))
        password_entry = ttk.Entry(login_frame, show="•", font=('Arial', 12))
        password_entry.pack(pady=(0,10), padx=20, fill=tk.X)
        
        # Buttons
        ttk.Button(login_frame, text="Login",
                command=lambda: self.login(username_entry.get(), password_entry.get())).pack(pady=10)
        ttk.Button(login_frame, text="Sign Up", 
                command=self.show_signup).pack(pady=5)

    def create_chat_selection_screen(self):
        self.clear_window()
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top bar with user info and create chat button
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_frame, text=f"Logged in as: {self.username}", 
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(top_frame, text="Create New Chat", 
                  command=self.show_create_chat_dialog).pack(side=tk.RIGHT)
        
        # Chat list frame
        list_frame = ttk.LabelFrame(main_frame, text="Your Chats", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create Treeview for chats
        columns = ('chat_name', 'type', 'participants')
        self.chat_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Define headings
        self.chat_tree.heading('chat_name', text='Chat Name')
        self.chat_tree.heading('type', text='Type')
        self.chat_tree.heading('participants', text='Participants')
        
        # Configure column widths
        self.chat_tree.column('chat_name', width=150)
        self.chat_tree.column('type', width=100)
        self.chat_tree.column('participants', width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                command=self.chat_tree.yview)
        self.chat_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.chat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click event
        self.chat_tree.bind('<Double-1>', self.on_chat_selected)
        
        # Bottom buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(bottom_frame, text="Refresh", 
                  command=self.refresh_chats).pack(side=tk.LEFT)
        ttk.Button(bottom_frame, text="Logout", 
                  command=self.logout).pack(side=tk.RIGHT)
        
        # Load chats
        self.refresh_chats()

    def show_create_chat_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Chat")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="Create New Chat", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Chat type selection
        type_frame = ttk.Frame(dialog)
        type_frame.pack(fill=tk.X, padx=20)
        
        chat_type = tk.StringVar(value="private")
        ttk.Radiobutton(type_frame, text="Private Chat", 
                       variable=chat_type, value="private").pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="Group Chat", 
                       variable=chat_type, value="group").pack(side=tk.LEFT)
        
        # Username/Group name entry
        ttk.Label(dialog, text="Username or Group Name:").pack(pady=(10,0))
        name_entry = ttk.Entry(dialog)
        name_entry.pack(padx=20, fill=tk.X)
        
        def create():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter a name")
                return
                
            is_group = chat_type.get() == "group"
            self.create_new_chat(name, is_group)
            dialog.destroy()
        
        ttk.Button(dialog, text="Create", command=create).pack(pady=20)

    def create_new_chat(self, name, is_group):
        data = {
            'target': name,
            'is_group': is_group,
            'creator': self.username
        }
        self.client.send(f'CREATE_CHAT:{json.dumps(data)}'.encode('utf-8'))
        response = self.client.recv(1024).decode('utf-8')
        
        if response.startswith('CHAT_CREATED:'):
            messagebox.showinfo("Success", "Chat created successfully!")
            self.refresh_chats()
        else:
            messagebox.showerror("Error", "Failed to create chat")

    def refresh_chats(self):
        try:
            self.client.send(f'GET_CHATS:{self.username}'.encode('utf-8'))
            response = self.client.recv(1024).decode('utf-8')
            
            try:
                chats = json.loads(response)
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Failed to load chats")
                return
                
            # Clear existing items
            for item in self.chat_tree.get_children():
                self.chat_tree.delete(item)
            
            # Add chats to tree
            for chat in chats:
                chat_type = "Group" if chat['is_group'] else "Private"
                participants = ", ".join(chat['participants'])
                self.chat_tree.insert('', 'end', 
                                    values=(chat['chat_name'], chat_type, participants),
                                    tags=(chat['_id'],))
        except Exception as e:
            print(f"Refresh chats error: {e}")
            messagebox.showerror("Error", "Failed to refresh chats")

    def on_chat_selected(self, event):
        selection = self.chat_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        chat_id = self.chat_tree.item(item, "tags")[0]
        chat_name = self.chat_tree.item(item, "values")[0]
        
        self.current_chat_id = chat_id
        self.show_chat(chat_name)

    def show_chat(self, chat_name):
        self.clear_window()
        
        # Main container with chat name at top
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top bar
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_frame, text=chat_name, 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Back", 
                  command=self.create_chat_selection_screen).pack(side=tk.RIGHT)
        
        # Chat display
        self.chat_text = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD,
            font=('Arial', 11)
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        
        # Input area
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.message_entry = ttk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(input_frame, text="Send", 
                  command=self.send_message).pack(side=tk.RIGHT)
        
        # Load chat history
        self.client.send(f'GET_MESSAGES:{self.current_chat_id}'.encode('utf-8'))
        
        # Bind enter key
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        self.message_entry.focus()

    def send_message(self):
        if not self.current_chat_id:
            return
            
        message = self.message_entry.get().strip()
        if message:
            data = {
                'chat_id': self.current_chat_id,
                'content': message,
                'username': self.username
            }
            self.client.send(f'MESSAGE:{json.dumps(data)}'.encode('utf-8'))
            self.message_entry.delete(0, tk.END)

    def receive_messages(self):
        while True:
            try:
                message = self.client.recv(1024).decode('utf-8')
                if message.startswith('{'):
                    # Handle JSON messages
                    data = json.loads(message)
                    if 'chat_id' in data and data['chat_id'] == self.current_chat_id:
                        self.chat_text.insert(tk.END, 
                                           f"{data['username']}: {data['content']}\n")
                        self.chat_text.see(tk.END)
                else:
                    # Handle system messages
                    self.chat_text.insert(tk.END, f"System: {message}\n")
                    self.chat_text.see(tk.END)
            except Exception as e:
                if self.logged_in:
                    messagebox.showerror("Error", "Lost connection to server")
                    self.root.quit()
                break

    def logout(self):
        self.logged_in = False
        self.username = None
        self.current_chat_id = None
        self.show_login()

if __name__ == "__main__":
    try:
        client = ChatClient()
    except Exception as e:
        print(f"Failed to start client: {e}")