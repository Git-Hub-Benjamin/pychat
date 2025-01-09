import json
from bson import ObjectId
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import threading
from chatserver import ChatServer


class ServerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chat Server Monitor")
        self.root.geometry("800x600")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Traffic Monitor Tab
        self.traffic_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.traffic_frame, text='Traffic Monitor')
        
        self.traffic_log = scrolledtext.ScrolledText(self.traffic_frame, wrap=tk.WORD)
        self.traffic_log.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Users Tab
        self.users_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.users_frame, text='Users')
        
        # Users treeview
        columns = ('username', 'password', 'created_at')
        self.users_tree = ttk.Treeview(self.users_frame, columns=columns, show='headings')
        self.users_tree.heading('username', text='Username')
        self.users_tree.heading('password', text='Password Hash')
        self.users_tree.heading('created_at', text='Created At')
        
        # Configure column widths
        self.users_tree.column('username', width=150)
        self.users_tree.column('password', width=300)  # Wider for hash
        self.users_tree.column('created_at', width=150)
        
        # Add scrollbar to users tree
        users_scroll = ttk.Scrollbar(self.users_frame, orient='vertical', 
                                   command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=users_scroll.set)
        
        self.users_tree.pack(side='left', fill='both', expand=True)
        users_scroll.pack(side='right', fill='y')
        
        # Control Panel
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.pack(fill='x', padx=5, pady=5)
        
        self.refresh_btn = ttk.Button(self.control_frame, text="Refresh Users", 
                                    command=self.refresh_users)
        self.refresh_btn.pack(side='left', padx=5)
        
        self.delete_all_btn = ttk.Button(self.control_frame, text="Delete All Users",
                                       command=self.delete_all_users)
        self.delete_all_btn.pack(side='left', padx=5)
        
        self.server_status = ttk.Label(self.control_frame, text="Server Status: Starting...")
        self.server_status.pack(side='right', padx=5)
        
        # Start server
        self.server = ChatServer(gui_callback=self.log_traffic)
        self.server_thread = threading.Thread(target=self.server.start)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        self.server_status.config(text="Server Status: Running")
        
        # Set up periodic refresh
        self.root.after(5000, self.refresh_users)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def delete_all_users(self):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete ALL users?"):
            try:
                self.server.db.delete_all_users()
                messagebox.showinfo("Success", "All users have been deleted")
                self.refresh_users()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete users: {e}")

    def refresh_users(self):
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
            
        users = self.server.db.get_all_users()
        for user in users:
            created_at = user['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            # Show password hash in the middle column
            self.users_tree.insert('', 'end', values=(
                user['username'],
                user['password'],
                created_at
            ))
        
        # Schedule next refresh
        self.root.after(5000, self.refresh_users)

    def log_traffic(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.traffic_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.traffic_log.see(tk.END)
        
        # Schedule next refresh
        self.root.after(5000, self.refresh_users)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to close the server?"):
            self.server.stop()
            self.root.destroy()

if __name__ == "__main__":
    ServerGUI()