"""
Secure credential management for CYT
Never store API keys in plain text files!
"""
import os
import json
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from input_validation import InputValidator

logger = logging.getLogger(__name__)

class SecureCredentialManager:
    """Secure credential storage and retrieval"""
    
    def __init__(self, credentials_dir: str = "./secure_credentials"):
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(exist_ok=True, mode=0o700)  # Restrict directory permissions
        self.key_file = self.credentials_dir / ".encryption_key"
        self.credentials_file = self.credentials_dir / "encrypted_credentials.json"
        
    def _generate_key_from_password(self, password: bytes, salt: bytes) -> bytes:
        """Generate encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password))
    
    def _get_or_create_encryption_key(self) -> Fernet:
        """Get existing encryption key or create new one"""
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, 'rb') as f:
                key_data = json.loads(f.read())
                salt = base64.b64decode(key_data['salt'])
        else:
            # Generate new salt
            salt = os.urandom(16)
            key_data = {'salt': base64.b64encode(salt).decode()}
            
            # Save salt (not the key itself!)
            with open(self.key_file, 'wb') as f:
                f.write(json.dumps(key_data).encode())
            os.chmod(self.key_file, 0o600)  # Restrict file permissions
            
        # Get password from environment or prompt
        password = self._get_master_password()
        key = self._generate_key_from_password(password.encode(), salt)
        return Fernet(key)
    
    def _get_master_password(self) -> str:
        """Get master password from environment variable or prompt user"""
        # Try environment variable first (for CI/CD, etc.)
        password = os.getenv('CYT_MASTER_PASSWORD')
        if password:
            return password
        
        # Check for testing mode
        if os.getenv('CYT_TEST_MODE') == 'true':
            return 'test_password_123'
        
        # Prompt user (for interactive use)
        import getpass
        try:
            password = getpass.getpass("Enter master password for CYT credentials: ")
            if not password:
                raise ValueError("Password cannot be empty")
            return password
        except (KeyboardInterrupt, EOFError):
            # Fallback for non-interactive environments
            print("⚠️  Non-interactive environment detected. Using environment variables.")
            print("Set CYT_MASTER_PASSWORD environment variable or use CYT_TEST_MODE=true for testing")
            raise RuntimeError("Password entry not available in non-interactive mode")
    
    def store_credential(self, service: str, credential_type: str, value: str) -> None:
        """Store encrypted credential with validation"""
        # Validate inputs
        if not all(isinstance(x, str) for x in [service, credential_type, value]):
            raise ValueError("All parameters must be strings")
        
        if not all(x.strip() for x in [service, credential_type, value]):
            raise ValueError("Parameters cannot be empty")
        
        # Sanitize service and credential_type names
        service = InputValidator.sanitize_string(service, max_length=50)
        credential_type = InputValidator.sanitize_string(credential_type, max_length=50)
        
        if len(value) > 10000:  # Reasonable limit for credentials
            raise ValueError("Credential value too long")
        
        try:
            cipher = self._get_or_create_encryption_key()
            
            # Load existing credentials or create new structure
            credentials = {}
            if self.credentials_file.exists():
                with open(self.credentials_file, 'rb') as f:
                    encrypted_data = f.read()
                    if encrypted_data:
                        decrypted_data = cipher.decrypt(encrypted_data)
                        credentials = json.loads(decrypted_data.decode())
            
            # Add new credential
            if service not in credentials:
                credentials[service] = {}
            credentials[service][credential_type] = value
            
            # Encrypt and save
            encrypted_data = cipher.encrypt(json.dumps(credentials).encode())
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
            os.chmod(self.credentials_file, 0o600)  # Restrict file permissions
            
            logger.info(f"Stored credential for {service}:{credential_type}")
            
        except Exception as e:
            logger.error(f"Failed to store credential: {e}")
            raise
    
    def get_credential(self, service: str, credential_type: str) -> Optional[str]:
        """Retrieve decrypted credential"""
        try:
            if not self.credentials_file.exists():
                logger.warning("No credentials file found")
                return None
            
            cipher = self._get_or_create_encryption_key()
            
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
                if not encrypted_data:
                    return None
                
                decrypted_data = cipher.decrypt(encrypted_data)
                credentials = json.loads(decrypted_data.decode())
            
            return credentials.get(service, {}).get(credential_type)
            
        except Exception as e:
            logger.error(f"Failed to retrieve credential: {e}")
            return None
    
    def migrate_from_config(self, config: Dict[str, Any]) -> None:
        """Migrate credentials from insecure config file"""
        print("🔐 Migrating credentials to secure storage...")
        
        # Migrate WiGLE API key
        wigle_config = config.get('api_keys', {}).get('wigle', {})
        if 'encoded_token' in wigle_config:
            encoded_token = wigle_config['encoded_token']
            print("Found WiGLE API token in config file - migrating to secure storage")
            self.store_credential('wigle', 'encoded_token', encoded_token)
            print("✅ WiGLE API token migrated successfully")
        
        # Could add other credentials here (database passwords, etc.)
        
        print("🔐 Credential migration complete!")
        print("⚠️  IMPORTANT: Remove API keys from config.json file!")
    
    def get_wigle_token(self) -> Optional[str]:
        """Convenience method to get WiGLE API token"""
        return self.get_credential('wigle', 'encoded_token')


def secure_config_loader(config_path: str = 'config.json') -> tuple[Any, SecureCredentialManager]:
    """
    Load configuration with secure credential handling
    Automatically migrates insecure credentials to secure storage
    """
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Initialize credential manager
    cred_manager = SecureCredentialManager()
    
    # Check if we need to migrate credentials
    if 'api_keys' in config:
        api_keys = config['api_keys']
        
        # Check for insecure API keys in config
        if any('token' in str(api_keys).lower() or 'key' in str(api_keys).lower() 
               for key in api_keys.values() if isinstance(key, dict)):
            
            logger.warning("Found API keys in config file - initiating secure migration")
            cred_manager.migrate_from_config(config)
            
            # Remove API keys from config (they're now stored securely)
            config.pop('api_keys', None)
            
            # Create sanitized config file
            sanitized_config_path = config_path.replace('.json', '_sanitized.json')
            with open(sanitized_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✅ Created sanitized config file: {sanitized_config_path}")
            print("⚠️  Please replace your config.json with the sanitized version")
    
    return config, cred_manager


def get_environment_credentials() -> Dict[str, str | None]:
    """Get credentials from environment variables (for CI/CD)"""
    return {
        'wigle_token': os.getenv('WIGLE_API_TOKEN'),
        'db_password': os.getenv('CYT_DB_PASSWORD'),
        # Add other environment credentials here
    }