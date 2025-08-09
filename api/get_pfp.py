import asyncio
import httpx
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from twikit.guest import GuestClient

# This is the main entry point for the Vercel serverless function
class handler(BaseHTTPRequestHandler):

    async def get_pfp_url(self, username: str):
        """
        Fetches a user's high-resolution profile picture URL using their username.
        This is a modified version of your original script.
        """
        print(f"Attempting to fetch PFP URL for: {username}")
        
        try:
            client = GuestClient()
            print("Activating guest client...")
            await client.activate()
        except Exception as e:
            print(f"Error: Could not activate the guest client. {e}")
            return None, f"Could not activate the guest client: {e}"

        try:
            print(f"Fetching data for '{username}'...")
            user = await client.get_user_by_screen_name(username)

            # Get the high-resolution profile picture URL by removing '_normal'
            pfp_url = (user.profile_image_url or '').replace('_normal', '')
            display_name = getattr(user, 'name', '') or ''
            screen_name = getattr(user, 'screen_name', '') or username
            print(f"Found PFP URL: {pfp_url} | name: {display_name} | handle: @{screen_name}")
            return {"pfp_url": pfp_url, "name": display_name, "handle": f"@{screen_name}"}, None
        except Exception as e:
            print(f"❌ An error occurred. The user '{username}' may not exist or their profile is protected. Error: {e}")
            return None, f"User '{username}' not found or profile is protected."

    def do_GET(self):
        # Parse the URL and query parameters
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        username = query_params.get('username', [None])[0]

        if not username:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Username parameter is missing'}).encode('utf-8'))
            return

        # Accept both username and full Twitter URL
        if username and 'twitter.com' in username:
            try:
                url = username if username.startswith('http') else f'https://{username}'
                from urllib.parse import urlparse
                path = urlparse(url).path
                parts = [p for p in path.split('/') if p]
                if parts:
                    candidate = parts[0]
                    reserved = ['home','explore','notifications','messages','search','settings','compose','login','signup','i','hashtag','logout','tos','privacy','about','intent','share','download']
                    import re
                    if re.match(r'^[A-Za-z0-9_]{1,15}$', candidate) and candidate.lower() not in reserved:
                        username = candidate
                    else:
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': 'Invalid Twitter username in URL'}).encode('utf-8'))
                        return
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'No username found in Twitter URL'}).encode('utf-8'))
                    return
            except Exception as e:
                print(f"Error parsing Twitter URL: {e}")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Invalid Twitter URL'}).encode('utf-8'))
                return

        # Run the asynchronous function to get the profile data
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                # If already running (rare in this context), create a new loop
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result, error = new_loop.run_until_complete(self.get_pfp_url(username))
                new_loop.close()
                asyncio.set_event_loop(loop)
            else:
                result, error = asyncio.get_event_loop().run_until_complete(self.get_pfp_url(username))
        except Exception as e:
            print(f"Error running async function: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'Internal server error: {e}'}).encode('utf-8'))
            return

        if error:
            self.send_response(404) # Not Found or other error
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': error}).encode('utf-8'))
            return
        
        # If successful, send the data back
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        # Add CORS header to allow requests from your front-end, especially during local development
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()
        
        self.wfile.write(json.dumps(result).encode('utf-8'))
        return