"""
Secure ignore list loader - replaces dangerous exec() calls
"""
import json
import pathlib
import re
from typing import List
import logging
from input_validation import InputValidator

logger = logging.getLogger(__name__)

class SecureIgnoreLoader:
    """Secure loader for MAC and SSID ignore lists"""
    
    @staticmethod
    def validate_mac_address(mac: str) -> bool:
        """Validate MAC address format using secure validator"""
        return InputValidator.validate_mac_address(mac)
    
    @staticmethod
    def validate_ssid(ssid: str) -> bool:
        """Validate SSID using secure validator"""
        return InputValidator.validate_ssid(ssid)
    
    @classmethod
    def load_mac_list(cls, file_path: pathlib.Path) -> List[str]:
        """
        Securely load MAC address ignore list
        Supports both JSON and Python list formats
        """
        if not file_path.exists():
            logger.warning(f"MAC ignore list not found: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Try JSON format first
            if content.startswith('[') and content.endswith(']'):
                try:
                    mac_list = json.loads(content)
                    if not isinstance(mac_list, list):
                        raise ValueError("JSON content is not a list")
                except json.JSONDecodeError:
                    # Fall back to Python list parsing
                    mac_list = cls._parse_python_list(content, 'ignore_list')
            else:
                # Parse Python variable assignment
                mac_list = cls._parse_python_list(content, 'ignore_list')
            
            # Validate all MAC addresses
            validated_macs = []
            for mac in mac_list:
                if isinstance(mac, str) and cls.validate_mac_address(mac):
                    validated_macs.append(mac.upper())  # Normalize to uppercase
                else:
                    logger.warning(f"Invalid MAC address skipped: {mac}")
            
            logger.info(f"Loaded {len(validated_macs)} valid MAC addresses")
            return validated_macs
            
        except Exception as e:
            logger.error(f"Error loading MAC list from {file_path}: {e}")
            return []
    
    @classmethod
    def load_ssid_list(cls, file_path: pathlib.Path) -> List[str]:
        """
        Securely load SSID ignore list
        Supports both JSON and Python list formats
        """
        if not file_path.exists():
            logger.warning(f"SSID ignore list not found: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Try JSON format first
            if content.startswith('[') and content.endswith(']'):
                try:
                    ssid_list = json.loads(content)
                    if not isinstance(ssid_list, list):
                        raise ValueError("JSON content is not a list")
                except json.JSONDecodeError:
                    # Fall back to Python list parsing
                    ssid_list = cls._parse_python_list(content, 'non_alert_ssid_list')
            else:
                # Parse Python variable assignment
                ssid_list = cls._parse_python_list(content, 'non_alert_ssid_list')
            
            # Validate all SSIDs
            validated_ssids = []
            for ssid in ssid_list:
                if isinstance(ssid, str) and cls.validate_ssid(ssid):
                    validated_ssids.append(ssid)
                else:
                    logger.warning(f"Invalid SSID skipped: {ssid}")
            
            logger.info(f"Loaded {len(validated_ssids)} valid SSIDs")
            return validated_ssids
            
        except Exception as e:
            logger.error(f"Error loading SSID list from {file_path}: {e}")
            return []
    
    @staticmethod
    def _parse_python_list(content: str, variable_name: str) -> List[str]:
        """
        Safely parse Python list assignment without exec()
        Only handles simple list assignments like: var_name = ['item1', 'item2']
        """
        # Remove comments and extra whitespace
        lines = [line.split('#')[0].strip() for line in content.split('\n')]
        content_clean = ' '.join(lines)
        
        # Look for variable assignment pattern
        pattern = rf'{re.escape(variable_name)}\s*=\s*(\[.*?\])'
        match = re.search(pattern, content_clean, re.DOTALL)
        
        if not match:
            raise ValueError(f"Could not find {variable_name} assignment")
        
        list_str = match.group(1)
        
        # Use json.loads for safe parsing (requires proper JSON format)
        try:
            # Replace single quotes with double quotes for JSON compatibility
            json_str = list_str.replace("'", '"')
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse list as JSON: {e}")
    
    @classmethod
    def save_mac_list(cls, mac_list: List[str], file_path: pathlib.Path) -> None:
        """Save MAC list in secure JSON format"""
        # Validate all MACs before saving
        valid_macs = [mac.upper() for mac in mac_list if cls.validate_mac_address(mac)]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(valid_macs, f, indent=2)
        
        logger.info(f"Saved {len(valid_macs)} MAC addresses to {file_path}")
    
    @classmethod
    def save_ssid_list(cls, ssid_list: List[str], file_path: pathlib.Path) -> None:
        """Save SSID list in secure JSON format"""
        # Validate all SSIDs before saving
        valid_ssids = [ssid for ssid in ssid_list if cls.validate_ssid(ssid)]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(valid_ssids, f, indent=2)
        
        logger.info(f"Saved {len(valid_ssids)} SSIDs to {file_path}")


def load_ignore_lists(config: dict) -> tuple[List[str], List[str]]:
    """
    Convenience function to load both MAC and SSID ignore lists
    Returns: (mac_list, ssid_list)
    """
    loader = SecureIgnoreLoader()
    
    # Load MAC ignore list
    mac_path = pathlib.Path('./ignore_lists') / config['paths']['ignore_lists']['mac']
    mac_list = loader.load_mac_list(mac_path)
    
    # Load SSID ignore list  
    ssid_path = pathlib.Path('./ignore_lists') / config['paths']['ignore_lists']['ssid']
    ssid_list = loader.load_ssid_list(ssid_path)
    
    return mac_list, ssid_list