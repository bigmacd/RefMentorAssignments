import hashlib
import hmac
import streamlit as st
from typing import Optional, Tuple
from database import RefereeDbCockroach

class AuthManager:
    """Handles user authentication and session management for the Streamlit app"""
    
    def __init__(self):
        self.db = RefereeDbCockroach()
        
        # Initialize session state variables for authentication
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'username' not in st.session_state:
            st.session_state.username = None
        if 'user_role' not in st.session_state:
            st.session_state.user_role = None
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None
    
    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash a password with salt"""
        if salt is None:
            import secrets
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for password hashing
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                          password.encode('utf-8'), 
                                          salt.encode('utf-8'), 
                                          100000)  # 100,000 iterations
        return password_hash.hex(), salt
    
    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """Verify a password against its hash"""
        password_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(password_hash, hashed_password)
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate a user with username and password"""
        user = self.db.get_user_by_username(username)
        if user and self.verify_password(password, user['password_hash'], user['salt']):
            # Set session state
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.user_role = user['role']
            st.session_state.user_id = user['id']
            return True
        return False
    
    def logout(self):
        """Logout the current user"""
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_id = None
        st.rerun()
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)
    
    def get_current_user(self) -> Optional[str]:
        """Get the current authenticated username"""
        return st.session_state.get('username')
    
    def get_user_role(self) -> Optional[str]:
        """Get the current user's role"""
        return st.session_state.get('user_role')
    
    def is_admin(self) -> bool:
        """Check if current user is an admin"""
        return st.session_state.get('user_role') == 'admin'
    
    def create_user(self, username: str, password: str, email: str, role: str = 'user') -> Tuple[bool, str]:
        """Create a new user account"""
        if self.db.user_exists(username):
            return False, "Username already exists"
        
        if self.db.email_exists(email):
            return False, "Email already registered"
        
        password_hash, salt = self.hash_password(password)
        
        try:
            self.db.create_user(username, password_hash, salt, email, role)
            return True, "User created successfully"
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user's password"""
        user = self.db.get_user_by_username(username)
        if not user:
            return False, "User not found"
        
        if not self.verify_password(old_password, user['password_hash'], user['salt']):
            return False, "Current password is incorrect"
        
        new_hash, new_salt = self.hash_password(new_password)
        
        try:
            self.db.update_user_password(username, new_hash, new_salt)
            return True, "Password changed successfully"
        except Exception as e:
            return False, f"Error changing password: {str(e)}"

def show_login_form(auth_manager: AuthManager):
    """Display the login form"""
    st.title("🏆 Referee Mentor System")
    st.markdown("### Please log in to continue")
    
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col_login, col_space = st.columns([1, 1])
            with col_login:
                login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if username and password:
                    if auth_manager.authenticate_user(username, password):
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please enter both username and password")

def show_user_menu(auth_manager: AuthManager):
    """Show user menu in sidebar"""
    with st.sidebar:
        st.markdown(f"**Logged in as:** {auth_manager.get_current_user()}")
        st.markdown(f"**Role:** {auth_manager.get_user_role()}")
        
        if st.button("Logout", use_container_width=True):
            auth_manager.logout()
            
        # Show admin menu if user is admin
        if auth_manager.is_admin():
            st.markdown("---")
            st.markdown("**Admin Functions**")
            if st.button("User Management", use_container_width=True):
                st.session_state.show_user_management = True

def show_user_management(auth_manager: AuthManager):
    """Show user management interface for admins"""
    if not auth_manager.is_admin():
        st.error("Access denied. Admin privileges required.")
        return
    
    st.title("User Management")
    
    tab1, tab2 = st.tabs(["Create User", "Manage Users"])
    
    with tab1:
        st.subheader("Create New User")
        with st.form("create_user_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
            
            create_button = st.form_submit_button("Create User")
            
            if create_button:
                if not all([new_username, new_email, new_password, confirm_password]):
                    st.error("All fields are required")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long")
                else:
                    success, message = auth_manager.create_user(new_username, new_password, new_email, new_role)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    with tab2:
        st.subheader("Current Users")
        users = auth_manager.db.get_all_users()
        if users:
            for user in users:
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.write(user['username'])
                with col2:
                    st.write(user['email'])
                with col3:
                    st.write(user['role'])
                with col4:
                    if st.button("Delete", key=f"delete_{user['id']}"):
                        # Add delete functionality here
                        pass
        else:
            st.write("No users found")

def require_auth(auth_manager: AuthManager):
    """Decorator-like function to require authentication"""
    if not auth_manager.is_authenticated():
        show_login_form(auth_manager)
        st.stop()
    else:
        show_user_menu(auth_manager)