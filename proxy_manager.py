import random
import logging
import asyncio
import time
from typing import Optional, Dict, List, Tuple
from config import PROXYLIST, WITHDRAWAL_LOG_CHAT_ID
from telethon import TelegramClient
import socks
import aiohttp
import socket

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_proxy_index = 0
        self.failed_proxies = set()
        self.proxy_health_status = {}  # Track proxy health and performance
        self.last_health_check = {}
        self.notification_bot = None
        self.load_proxies()
    
    def set_notification_bot(self, bot):
        """Set the bot instance for sending notifications"""
        self.notification_bot = bot
    
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
                        self.proxy_health_status[f"{ip}:{port}"] = {
                            'status': 'unknown',
                            'last_check': 0,
                            'response_time': 0,
                            'success_count': 0,
                            'failure_count': 0,
                            'bandwidth_warning_sent': False
                        }
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
    
    async def check_proxy_health(self, proxy_config: dict) -> dict:
        """Check if a proxy is working properly and measure performance"""
        proxy_key = f"{proxy_config['addr']}:{proxy_config['port']}"
        
        try:
            start_time = time.time()
            
            # Test proxy by making a simple HTTP request through it
            connector = aiohttp.connector.ProxyConnector.from_url(
                f"socks5://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['addr']}:{proxy_config['port']}"
            )
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get('http://httpbin.org/ip') as response:
                    if response.status == 200:
                        response_time = time.time() - start_time
                        
                        # Update health status
                        self.proxy_health_status[proxy_key].update({
                            'status': 'healthy',
                            'last_check': time.time(),
                            'response_time': response_time,
                            'success_count': self.proxy_health_status[proxy_key]['success_count'] + 1
                        })
                        
                        # Check for slow response (potential bandwidth issue)
                        if response_time > 5.0:  # 5 seconds threshold
                            await self.send_bandwidth_warning(proxy_config, response_time)
                        
                        return {
                            'status': 'healthy',
                            'response_time': response_time,
                            'working': True
                        }
        
        except Exception as e:
            # Mark proxy as failed
            self.proxy_health_status[proxy_key].update({
                'status': 'failed',
                'last_check': time.time(),
                'failure_count': self.proxy_health_status[proxy_key]['failure_count'] + 1
            })
            
            await self.send_proxy_failure_notification(proxy_config, str(e))
            
            return {
                'status': 'failed',
                'error': str(e),
                'working': False
            }
    
    async def send_proxy_failure_notification(self, proxy_config: dict, error_msg: str):
        """Send notification when proxy fails"""
        if not self.notification_bot:
            return
        
        try:
            proxy_key = f"{proxy_config['addr']}:{proxy_config['port']}"
            failure_count = self.proxy_health_status[proxy_key]['failure_count']
            
            message = f"""
🚨 **PROXY FAILURE ALERT** 🚨

📡 **Proxy**: {proxy_config['addr']}:{proxy_config['port']}
👤 **Username**: {proxy_config['username']}
❌ **Status**: Not Working
📝 **Error**: {error_msg}
🔢 **Failure Count**: {failure_count}
⏰ **Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}

⚠️ **Action**: Switching to direct connection for OTP verification
🔄 **Fallback**: Normal verification process activated
            """
            
            await self.notification_bot.send_message(
                WITHDRAWAL_LOG_CHAT_ID,
                message,
                parse_mode='markdown'
            )
            
        except Exception as e:
            print(f"❌ Failed to send proxy failure notification: {e}")
    
    async def send_bandwidth_warning(self, proxy_config: dict, response_time: float):
        """Send notification when proxy has bandwidth issues"""
        if not self.notification_bot:
            return
        
        proxy_key = f"{proxy_config['addr']}:{proxy_config['port']}"
        
        # Only send warning once per session to avoid spam
        if self.proxy_health_status[proxy_key]['bandwidth_warning_sent']:
            return
        
        try:
            message = f"""
⚠️ **PROXY BANDWIDTH WARNING** ⚠️

📡 **Proxy**: {proxy_config['addr']}:{proxy_config['port']}
👤 **Username**: {proxy_config['username']}
🐌 **Response Time**: {response_time:.2f} seconds
📊 **Status**: Slow Performance Detected
⏰ **Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}

💡 **Recommendation**: Check proxy bandwidth or consider using backup proxy
🔄 **Current Action**: Continuing with current proxy but monitoring performance
            """
            
            await self.notification_bot.send_message(
                WITHDRAWAL_LOG_CHAT_ID,
                message,
                parse_mode='markdown'
            )
            
            # Mark warning as sent
            self.proxy_health_status[proxy_key]['bandwidth_warning_sent'] = True
            
        except Exception as e:
            print(f"❌ Failed to send bandwidth warning: {e}")
    
    async def get_working_proxy(self) -> Optional[dict]:
        """Get a working proxy with health check and fallback"""
        if not self.proxies:
            return None
        
        # Try current proxy first
        current_proxy = self.proxies[self.current_proxy_index]
        proxy_key = f"{current_proxy['addr']}:{current_proxy['port']}"
        
        # Quick health check if not checked recently (within 5 minutes)
        last_check = self.proxy_health_status[proxy_key]['last_check']
        if time.time() - last_check > 300:  # 5 minutes
            health_result = await self.check_proxy_health(current_proxy)
            if health_result['working']:
                return current_proxy
        elif self.proxy_health_status[proxy_key]['status'] == 'healthy':
            return current_proxy
        
        # If current proxy failed, try others
        for i, proxy in enumerate(self.proxies):
            if i != self.current_proxy_index:
                proxy_key = f"{proxy['addr']}:{proxy['port']}"
                health_result = await self.check_proxy_health(proxy)
                if health_result['working']:
                    self.current_proxy_index = i
                    return proxy
        
        # All proxies failed
        await self.send_all_proxies_failed_notification()
        return None
    
    async def send_all_proxies_failed_notification(self):
        """Send notification when all proxies have failed"""
        if not self.notification_bot:
            return
        
        try:
            message = f"""
🔴 **CRITICAL: ALL PROXIES FAILED** 🔴

❌ **Status**: All configured proxies are not working
📊 **Total Proxies**: {len(self.proxies)}
🔄 **Fallback**: Using direct connection for OTP verification
⏰ **Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}

⚠️ **IMMEDIATE ACTION REQUIRED**:
• Check proxy provider status
• Verify proxy credentials
• Consider adding backup proxies
• Monitor OTP delivery rates

📝 **Proxy Status Summary**:
            """
            
            for proxy in self.proxies:
                proxy_key = f"{proxy['addr']}:{proxy['port']}"
                status = self.proxy_health_status[proxy_key]
                message += f"\n• {proxy_key}: {status['status']} (Failures: {status['failure_count']})"
            
            await self.notification_bot.send_message(
                WITHDRAWAL_LOG_CHAT_ID,
                message,
                parse_mode='markdown'
            )
            
        except Exception as e:
            print(f"❌ Failed to send all proxies failed notification: {e}")

    def get_next_proxy(self) -> Optional[dict]:
        """Get the next proxy in rotation (synchronous version)"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy
    
    def mark_proxy_failed(self, proxy_config: dict):
        """Mark a proxy as failed"""
        proxy_key = f"{proxy_config['addr']}:{proxy_config['port']}"
        self.failed_proxies.add(proxy_key)
        
        if proxy_key in self.proxy_health_status:
            self.proxy_health_status[proxy_key]['status'] = 'failed'
            self.proxy_health_status[proxy_key]['failure_count'] += 1
        
        print(f"❌ Marked proxy as failed: {proxy_key}")
    
    def reset_failed_proxies(self):
        """Reset the failed proxies list"""
        self.failed_proxies.clear()
        
        # Reset health status for all proxies
        for proxy_key in self.proxy_health_status:
            self.proxy_health_status[proxy_key].update({
                'status': 'unknown',
                'failure_count': 0,
                'bandwidth_warning_sent': False
            })
        
        print("🔄 Reset all failed proxies")
    
    def get_proxy_stats(self) -> str:
        """Get detailed proxy statistics"""
        if not self.proxies:
            return "❌ No proxies configured"
        
        stats = f"📊 **Proxy Statistics**\n\n"
        stats += f"🌐 **Total Proxies**: {len(self.proxies)}\n"
        stats += f"❌ **Failed Proxies**: {len(self.failed_proxies)}\n"
        stats += f"✅ **Working Proxies**: {len(self.proxies) - len(self.failed_proxies)}\n"
        stats += f"🔄 **Current Index**: {self.current_proxy_index}\n\n"
        
        stats += "**Individual Proxy Status**:\n"
        for i, proxy in enumerate(self.proxies):
            proxy_key = f"{proxy['addr']}:{proxy['port']}"
            health = self.proxy_health_status.get(proxy_key, {})
            
            status_emoji = "✅" if health.get('status') == 'healthy' else "❌" if health.get('status') == 'failed' else "❓"
            current_marker = " 👈 *Current*" if i == self.current_proxy_index else ""
            
            stats += f"{status_emoji} `{proxy_key}` (User: {proxy['username']}){current_marker}\n"
            
            if health:
                stats += f"   • Status: {health.get('status', 'unknown')}\n"
                stats += f"   • Success: {health.get('success_count', 0)} | Failures: {health.get('failure_count', 0)}\n"
                if health.get('response_time'):
                    stats += f"   • Response Time: {health.get('response_time', 0):.2f}s\n"
                if health.get('last_check'):
                    last_check = time.strftime('%H:%M:%S', time.localtime(health['last_check']))
                    stats += f"   • Last Check: {last_check}\n"
            stats += "\n"
        
        return stats

# Global proxy manager instance
proxy_manager = ProxyManager()