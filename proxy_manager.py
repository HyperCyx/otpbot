import random
import logging
from typing import Optional, Dict, List, Tuple
from config import PROXYLIST
from telethon import TelegramClient
import socks

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_proxy_index = 0
        self.failed_proxies = set()
        self.load_proxies()
    
    def load_proxies(self):
        """Load and parse proxy list from configuration"""
        try:
            if not PROXYLIST.strip():
                print("⚠️ No proxy list configured. OTP will be sent without proxy.")
                return
            
            proxy_strings = [p.strip() for p in PROXYLIST.split(',') if p.strip()]
            
            for proxy_string in proxy_strings:
                try:
                    parts = proxy_string.split(':')
                    if len(parts) == 4:
                        ip, port, username, password = parts
                        proxy_config = {
                            'proxy_type': socks.SOCKS5,
                            'addr': ip.strip(),
                            'port': int(port.strip()),
                            'username': username.strip(),
                            'password': password.strip(),
                            'rdns': True
                        }
                        self.proxies.append(proxy_config)
                        print(f"✅ Loaded proxy: {ip}:{port}")
                    else:
                        print(f"❌ Invalid proxy format: {proxy_string}")
                except Exception as e:
                    print(f"❌ Error parsing proxy {proxy_string}: {e}")
            
            if self.proxies:
                print(f"🌐 Loaded {len(self.proxies)} proxies for OTP sending")
                # Randomize the starting proxy
                self.current_proxy_index = random.randint(0, len(self.proxies) - 1)
            else:
                print("⚠️ No valid proxies loaded. OTP will be sent without proxy.")
                
        except Exception as e:
            print(f"❌ Error loading proxy configuration: {e}")
    
    def get_next_proxy(self) -> Optional[Dict]:
        """Get the next proxy in rotation"""
        if not self.proxies:
            return None
        
        # Try to find a working proxy
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_proxy_index]
            proxy_id = f"{proxy['addr']}:{proxy['port']}"
            
            # Move to next proxy for next call
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            
            # Skip failed proxies
            if proxy_id in self.failed_proxies:
                attempts += 1
                continue
            
            return proxy
        
        # If all proxies failed, reset failed list and try again
        if self.failed_proxies:
            print("🔄 All proxies failed, resetting failed list")
            self.failed_proxies.clear()
            return self.get_next_proxy()
        
        return None
    
    def mark_proxy_failed(self, proxy: Dict):
        """Mark a proxy as failed"""
        if proxy:
            proxy_id = f"{proxy['addr']}:{proxy['port']}"
            self.failed_proxies.add(proxy_id)
            print(f"❌ Marked proxy as failed: {proxy_id}")
    
    def get_proxy_for_telethon(self) -> Optional[Tuple]:
        """Get proxy configuration in Telethon format"""
        proxy = self.get_next_proxy()
        if not proxy:
            return None
        
        # Return tuple format for Telethon: (proxy_type, addr, port, rdns, username, password)
        return (
            proxy['proxy_type'],
            proxy['addr'],
            proxy['port'],
            proxy['rdns'],
            proxy['username'],
            proxy['password']
        )
    
    def test_proxy(self, proxy: Dict) -> bool:
        """Test if a proxy is working"""
        try:
            # Basic connectivity test could be implemented here
            # For now, we'll rely on Telethon's connection attempts
            return True
        except Exception as e:
            print(f"❌ Proxy test failed for {proxy['addr']}:{proxy['port']}: {e}")
            return False
    
    def get_proxy_stats(self) -> Dict:
        """Get proxy statistics"""
        total_proxies = len(self.proxies)
        failed_proxies = len(self.failed_proxies)
        working_proxies = total_proxies - failed_proxies
        
        return {
            'total': total_proxies,
            'working': working_proxies,
            'failed': failed_proxies,
            'current_index': self.current_proxy_index
        }
    
    def reset_failed_proxies(self):
        """Reset the failed proxy list"""
        self.failed_proxies.clear()
        print("🔄 Reset failed proxy list")
    
    def get_current_proxy_info(self) -> str:
        """Get current proxy information for logging"""
        if not self.proxies:
            return "No proxy configured"
        
        proxy = self.proxies[self.current_proxy_index]
        return f"{proxy['addr']}:{proxy['port']}"

# Global proxy manager instance
proxy_manager = ProxyManager()

def get_proxy_for_client():
    """Get proxy configuration for Telethon client"""
    return proxy_manager.get_proxy_for_telethon()

def mark_current_proxy_failed(proxy_tuple):
    """Mark current proxy as failed"""
    if proxy_tuple:
        proxy_dict = {
            'addr': proxy_tuple[1],
            'port': proxy_tuple[2],
            'username': proxy_tuple[4],
            'password': proxy_tuple[5]
        }
        proxy_manager.mark_proxy_failed(proxy_dict)

def get_proxy_stats():
    """Get proxy statistics"""
    return proxy_manager.get_proxy_stats()

def reset_failed_proxies():
    """Reset failed proxy list"""
    proxy_manager.reset_failed_proxies()

def reload_proxies():
    """Reload proxy configuration"""
    proxy_manager.load_proxies()
    return len(proxy_manager.proxies)