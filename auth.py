import hashlib
import hmac
import secrets
import streamlit as st
import time

from datetime import datetime, timedelta
from typing import Optional, Tuple
from database import RefereeDbCockroach
from sendemail import GmailAPIEmail

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
        if 'show_forgot_password' not in st.session_state:
            st.session_state.show_forgot_password = False
        if 'show_reset_password' not in st.session_state:
            st.session_state.show_reset_password = False
        if 'reset_token' not in st.session_state:
            st.session_state.reset_token = None


    def hashPassword(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash a password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)

        # Use PBKDF2 for password hashing
        password_hash = hashlib.pbkdf2_hmac('sha256',
                                          password.encode('utf-8'),
                                          salt.encode('utf-8'),
                                          100000)  # 100,000 iterations
        return password_hash.hex(), salt


    def verifyPassword(self, password: str, hashed_password: str, salt: str) -> bool:
        """Verify a password against its hash"""
        password_hash, _ = self.hashPassword(password, salt)
        return hmac.compare_digest(password_hash, hashed_password)


    def authenticateUser(self, username: str, password: str) -> bool:
        """Authenticate a user with username and password"""
        user = self.db.getUserByUsername(username)
        if user and self.verifyPassword(password, user['password_hash'], user['salt']):
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


    def isAuthenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)


    def getCurrentUser(self) -> Optional[str]:
        """Get the current authenticated username"""
        return st.session_state.get('username')


    def getUserRole(self) -> Optional[str]:
        """Get the current user's role"""
        return st.session_state.get('user_role')


    def isAdmin(self) -> bool:
        """Check if current user is an admin"""
        return st.session_state.get('user_role') == 'admin'


    def createUser(self, username: str, password: str, email: str, role: str = 'user') -> Tuple[bool, str]:
        """Create a new user account"""
        if self.db.userExists(username):
            return False, "Username already exists"

        if self.db.emailExists(email):
            return False, "Email already registered"

        password_hash, salt = self.hashPassword(password)

        try:
            self.db.createUser(username, password_hash, salt, email, role)
            return True, "User created successfully"
        except Exception as e:
            return False, f"Error creating user: {str(e)}"


    def changePassword(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user's password"""
        user = self.db.getUserByUsername(username)
        if not user:
            return False, "User not found"

        if not self.verifyPassword(old_password, user['password_hash'], user['salt']):
            return False, "Current password is incorrect"

        new_hash, new_salt = self.hashPassword(new_password)

        try:
            self.db.updateUserPassword(username, new_hash, new_salt)
            return True, "Password changed successfully"
        except Exception as e:
            return False, f"Error changing password: {str(e)}"


    def generateResetToken(self) -> str:
        """Generate a secure password reset token"""
        return secrets.token_urlsafe(32)


    def requestPasswordReset(self, email: str) -> Tuple[bool, str]:
        """Request a password reset for the given email"""
        user = self.db.getUserByEmail(email)
        if not user:
            # Don't reveal whether the email exists or not for security
            return True, "If the email exists in our system, a password reset link will be sent."

        try:
            # Generate reset token
            token = self.generateResetToken()
            expires_at = datetime.now() + timedelta(hours=1)  # Token expires in 1 hour

            # Store the token in database
            self.db.createPasswordResetToken(user['id'], token, expires_at)

            # In a real implementation, you would send an email here
            # For now, we'll show the token in the UI (not recommended for production)
            st.session_state.reset_token = token

            return True, f"Password reset requested. Your check your email for the reset link."
        except Exception as e:
            return False, f"Error requesting password reset: {str(e)}"


    def resetPasswordWithToken(self, token: str, new_password: str, current_email: str) -> Tuple[bool, str]:
        """Reset password using a valid token"""
        token_data = self.db.getPasswordResetToken(token, current_email)
        if not token_data:
            return False, "Invalid or expired reset token"

        try:
            # Hash the new password
            new_hash, new_salt = self.hashPassword(new_password)

            # Update the user's password
            self.db.updateUserPassword(token_data['username'], new_hash, new_salt)

            # Mark the token as used
            self.db.usePasswordResetToken(token)

            # Clean up expired tokens
            self.db.cleanupExpiredTokens()

            return True, "Password reset successfully"
        except Exception as e:
            return False, f"Error resetting password: {str(e)}"


# The following functions handle the Streamlit UI components related to authentication
def showLoginForm(authManager: AuthManager):
    """Display the login form"""
    st.title("🏆 Referee Mentor System")
    st.markdown("### Please log in to continue")

    with st.form("login_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")

            col_login, col_space = st.columns([1, 1])
            with col_login:
                login_button = st.form_submit_button("Login", use_container_width=True)

            if login_button:
                if username and password:
                    if authManager.authenticateUser(username, password):
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                        time.sleep(3)
                        authManager.logout()
                else:
                    st.error("Please enter both username and password")

    # Add forgot password link outside the form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Forgot Password?", use_container_width=True, type="secondary"):
            st.session_state.show_forgot_password = True
            st.rerun()


def showUserMenu(auth_manager: AuthManager):
    """Show user menu in sidebar"""
    with st.sidebar:
        st.markdown(f"**Logged in as:** {auth_manager.getCurrentUser()}")
        st.markdown(f"**Role:** {auth_manager.getUserRole()}")

        if st.button("Logout", use_container_width=True):
            auth_manager.logout()

        # Show admin menu if user is admin
        if auth_manager.isAdmin():
            st.markdown("---")
            st.markdown("**Admin Functions**")
            if st.button("User Management", use_container_width=True):
                st.session_state.show_user_management = True


def showUserManagement(auth_manager: AuthManager):
    """Show user management interface for admins"""
    if not auth_manager.isAdmin():
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
                    success, message = auth_manager.createUser(new_username, new_password, new_email, new_role)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

    with tab2:
        st.subheader("Current Users")
        users = auth_manager.db.getAllUsers()
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


def showForgotPasswordForm(auth_manager: AuthManager):
    """Display the forgot password form"""
    st.title("🏆 Referee Mentor System")
    st.markdown("### Reset Your Password")

    with st.form("forgot_password_form"):
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("Enter your email address and we'll send you a password reset link.")
            email = st.text_input("Email Address", placeholder="Enter your email address")

            col_submit, col_cancel = st.columns([1, 1])
            with col_submit:
                submit_button = st.form_submit_button("Send Reset Link", use_container_width=True)
            with col_cancel:
                cancel_button = st.form_submit_button("Cancel", use_container_width=True)

            if submit_button:
                if email:
                    # if success, let the user know to check their email
                    success, message = auth_manager.requestPasswordReset(email)
                    if success:
                        st.success(message)
                        st.session_state.show_reset_password = True
                        st.session_state.show_forgot_password = False
                        if st.session_state.reset_token:

                            emailClient = GmailAPIEmail()
                            emailClient.send(
                                email,
                                "Referee Mentor System Password Reset",
                                f"Use the following token to reset your password: {st.session_state.reset_token}"
                            )

                            st.session_state.current_email = email
                            time.sleep(3)
                            st.rerun()
                        else:
                            time.sleep(3)
                            st.rerun()
                    else:
                        st.error(message)
                        st.rerun()
                else:
                    st.error("Please enter your email address")

            if cancel_button:
                st.session_state.show_forgot_password = False
                st.rerun()


def showResetPasswordForm(auth_manager: AuthManager):
    """Display the reset password form"""
    st.title("🏆 Referee Mentor System")
    st.markdown("### Enter New Password")

    gohome = False

    with st.sidebar:
        if st.button("Home", use_container_width=True):
            gohome = True

    if gohome:
        st.session_state.show_reset_password = False
        st.session_state.show_forgot_password = False
        st.session_state.reset_token = None
        st.rerun()

    with st.form("reset_password_form"):
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            token = st.session_state.reset_token
            current_email = st.session_state.get('current_email', '')
            token = st.text_input("Reset Token", placeholder="Enter your reset token")
            # use password-validator here
            new_password = st.text_input("New Password", type="password", placeholder="Enter your new password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your new password")

            col_submit, col_cancel = st.columns([1, 1])
            with col_submit:
                submit_button = st.form_submit_button("Reset Password", use_container_width=True)
            with col_cancel:
                cancel_button = st.form_submit_button("Cancel", use_container_width=True)

            if submit_button:
                if not all([token, new_password, confirm_password]):
                    st.error("All fields are required")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long")
                else:
                    success, message = auth_manager.resetPasswordWithToken(token, new_password, current_email)
                    if success:
                        st.success(message)
                        st.info("You can now log in with your new password.")
                        # Clear the session states and go back to login
                        st.session_state.show_reset_password = False
                        st.session_state.show_forgot_password = False
                        st.session_state.reset_token = None
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(message)

            if cancel_button:
                st.session_state.show_reset_password = False
                st.session_state.show_forgot_password = False
                st.session_state.reset_token = None
                st.rerun()


def requireAuth(auth_manager: AuthManager):
    """Decorator-like function to require authentication"""
    if not auth_manager.isAuthenticated():
        # Check if we should show forgot password or reset password forms
        if st.session_state.get('show_reset_password', False):
            showResetPasswordForm(auth_manager)
            st.stop()
        elif st.session_state.get('show_forgot_password', False):
            showForgotPasswordForm(auth_manager)
            st.stop()
        else:
            showLoginForm(auth_manager)
            st.stop()
    else:
        showUserMenu(auth_manager)
