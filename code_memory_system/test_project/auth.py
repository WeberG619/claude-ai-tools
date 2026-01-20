"""Authentication module for testing the code memory system."""

import hashlib
from typing import Optional, Dict


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class User:
    """Represents a user in the system."""
    
    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email
        self.is_authenticated = False
        

class AuthManager:
    """Handles user authentication and session management."""
    
    def __init__(self):
        self.users: Dict[str, Dict] = {}
        self.sessions: Dict[str, User] = {}
        
    def register_user(self, username: str, password: str, email: str) -> User:
        """Register a new user in the system."""
        if username in self.users:
            raise ValueError(f"User {username} already exists")
            
        password_hash = self._hash_password(password)
        
        self.users[username] = {
            'password_hash': password_hash,
            'email': email
        }
        
        return User(username, email)
        
    def authenticate_user(self, username: str, password: str) -> str:
        """Authenticate a user and return a session token."""
        if username not in self.users:
            raise AuthenticationError("Invalid username or password")
            
        user_data = self.users[username]
        password_hash = self._hash_password(password)
        
        if password_hash != user_data['password_hash']:
            raise AuthenticationError("Invalid username or password")
            
        # Generate session token
        session_token = self._generate_session_token(username)
        
        # Create user object and store in sessions
        user = User(username, user_data['email'])
        user.is_authenticated = True
        self.sessions[session_token] = user
        
        return session_token
        
    def logout_user(self, session_token: str) -> bool:
        """Logout a user by invalidating their session."""
        if session_token in self.sessions:
            del self.sessions[session_token]
            return True
        return False
        
    def get_user_by_session(self, session_token: str) -> Optional[User]:
        """Get user object from session token."""
        return self.sessions.get(session_token)
        
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
        
    def _generate_session_token(self, username: str) -> str:
        """Generate a unique session token."""
        import time
        data = f"{username}{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()