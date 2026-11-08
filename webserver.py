# -*- coding: utf-8 -*-
"""
PomBiss Web Interface (v6.2 - Gradient Title & Vibrant Colors)
"""

import os
import json
import threading
import socket
import time

try:
    from urllib import quote
except:
    from urllib.parse import quote

PORT = 8776
SERVICES_PATH = "/media/hdd/PomBiss_services.json"

_running = False
_server_socket = None

def log_debug(msg):
    try:
        with open("/tmp/PomBiss_Web.log", "a") as f:
            f.write("[WebServer] %s\n" % msg)
    except:
        pass

def get_receiver_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def generate_html():
    ip = get_receiver_ip()
    try:
        if os.path.exists(SERVICES_PATH):
            with open(SERVICES_PATH, "r") as f:
                services = json.load(f)
        else:
            services = {}
    except:
        services = {}

    html = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>PomBiss Web Panel</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background-color: #0f172a; color: #fff; font-family: 'Outfit', -apple-system, Arial, sans-serif; margin: 0; padding: 20px; }
            .container { max-width: 850px; margin: 0 auto; }
            
            /* Header & Branding Section */
            .header-box { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 25px; margin-bottom: 20px; text-align: center; }
            
            /* NEW GRADIENT TITLE */
            .header-box .brand { 
                font-size: 32px; 
                font-weight: 900; 
                letter-spacing: 1.5px;
                background: linear-gradient(90deg, #00e676, #0066ff, #ec4899); 
                -webkit-background-clip: text; 
                -webkit-text-fill-color: transparent; 
                text-shadow: 0 0 15px rgba(0, 230, 118, 0.2);
                margin-bottom: 8px; 
            }
            
            .header-box .dev { color: #8b5cf6; font-size: 14px; margin-bottom: 15px; }
            .header-box .url-box { background: #000; color: #fbbf24; padding: 10px 15px; border-radius: 8px; font-family: monospace; font-size: 15px; display: inline-block; border: 1px dashed #fbbf24; }
            .header-box .channel { color: #3b82f6; text-decoration: none; font-weight: bold; }
            .header-box .channel:hover { text-decoration: underline; }

            .card { background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 20px; margin-bottom: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
            .title { color: #10b981; font-size: 18px; font-weight: bold; margin-bottom: 8px; }
            .info { color: #94a3b8; font-size: 14px; margin-bottom: 15px; }
            
            .btn-group { display: flex; gap: 8px; flex-wrap: wrap; }
            .btn { flex: 1; text-align: center; padding: 10px; border-radius: 8px; font-weight: bold; text-decoration: none; font-size: 13px; transition: 0.2s; min-width: 100px; cursor: pointer; border: none; display: flex; align-items: center; justify-content: center;}
            
            /* Vibrant Colors */
            .btn-m3u { background: #0066ff; color: #fff; } /* Vibrant Blue */
            .btn-m3u:hover { background: #0052cc; }
            
            .btn-copy { background: #ff0033; color: #fff; } /* Vibrant Red */
            .btn-copy:hover { background: #cc0029; }
            
            .btn-vlc-ios { background: #ff8800; color: #000; } /* Vibrant Orange */
            .btn-vlc-ios:hover { background: #cc6d00; }
            
            .btn-apple { background: #ffffff; color: #000; } /* Pure White */
            .btn-apple:hover { background: #e5e5e5; }
            
            .btn-vlc-universal { background: #00e676; color: #000; } /* Neon Green */
            .btn-vlc-universal:hover { background: #00b85e; }
            
            .no-feeds { text-align: center; color: #ef4444; margin-top: 50px; font-size: 18px; }
        </style>
    </head>
    <body>
    <div class="container">
        
        <!-- HEADER / BRANDING -->
        <div class="header-box">
            <div class="brand">PomBiss Panel</div>
            <div class="dev">Developed by @Shr776</div>
            <div style="margin-bottom: 10px; font-size: 13px; color: #94a3b8;">
                Join our Telegram Channel:<br>
                <a href="https://t.me/VuSolo" class="channel" target="_blank">https://t.me/VuSolo</a>
            </div>
            <div class="url-box">
                Web Access: http://%s:8776
            </div>
        </div>

        <h2 style="text-align: center; margin-bottom: 20px; color: #94a3b8; font-size: 16px;">Live Feeds & M3U Exporter</h2>
    """ % ip
    
    if not services:
        html += "<div class='card no-feeds'>No feeds found. Scan some feeds on receiver!</div>"
    else:
        for key, data in services.items():
            ref = data.get("service_ref", "")
            if not ref: continue
            name = data.get("display_name", "").strip() or data.get("feed_id", "").strip() or data.get("name", key)
            sat = data.get("sat", "")
            freq = data.get("freq", "")
            pol = data.get("pol", "")
            sr = data.get("sr", "")
            
            m3u_url = "/m3u?id=%s" % quote(key)
            hls_url = "/hls?id=%s" % quote(key)
            raw_stream = "http://%s:8001/%s" % (ip, quote(str(ref), safe=''))
            vlc_url = "vlc://http://%s:8001/%s" % (ip, quote(str(ref), safe=''))
            vlc_ios = "vlc-x-callback://x-callback-url/stream?url=http://%s:8001/%s" % (ip, quote(str(ref), safe=''))
            
            html += """
            <div class="card">
                <div class="title">%s</div>
                <div class="info">Sat: %s | Freq: %s %s %s</div>
                <div class="btn-group">
                    <a href="%s" class="btn btn-m3u" download="%s.m3u">Download M3U</a>
                    <button onclick="copyLink('%s')" class="btn btn-copy">Copy Stream Link</button>
                    <a href="%s" class="btn btn-vlc-ios">VLC for iOS</a>
                    <a href="%s" class="btn btn-apple" target="_blank">Apple TV (HLS)</a>
                    <a href="%s" class="btn btn-vlc-universal">VLC Universal</a>
                </div>
            </div>
            """ % (name, sat, freq, pol, sr, m3u_url, quote(name), raw_stream, vlc_ios, hls_url, vlc_url)
            
    html += """
    </div>
    <script>
    function copyLink(url) {
        var tempInput = document.createElement("input");
        tempInput.value = url;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand("copy");
        document.body.removeChild(tempInput);
        alert("Stream link copied to clipboard!");
    }
    </script>
    </body></html>
    """
    return html

def generate_m3u(feed_id):
    ip = get_receiver_ip()
    try:
        with open(SERVICES_PATH, "r") as f:
            services = json.load(f)
        if feed_id in services:
            data = services[feed_id]
            ref = data.get("service_ref", "")
            name = data.get("display_name", "").strip() or data.get("feed_id", "").strip() or data.get("name", feed_id)
            stream = "http://%s:8001/%s" % (ip, quote(str(ref), safe=''))
            return "#EXTM3U\n#EXTINF:-1 group-title=\"PomBiss\",%s\n#EXTVLCOPT:http-reconnect=true\n#EXTVLCOPT:network-caching=1000\n%s\n" % (name, stream)
    except:
        pass
    return "#EXTM3U\n"

def generate_hls(feed_id):
    ip = get_receiver_ip()
    try:
        with open(SERVICES_PATH, "r") as f:
            services = json.load(f)
        if feed_id in services:
            data = services[feed_id]
            ref = data.get("service_ref", "")
            stream = "http://%s:8001/%s" % (ip, quote(str(ref), safe=''))
            return "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1000000\n%s\n" % stream
    except:
        pass
    return "#EXTM3U\n"

def _handle(conn):
    try:
        request = conn.recv(4096).decode('utf-8', 'ignore')
        
        if "GET /hls?" in request:
            try:
                feed_id = request.split("GET /hls?id=")[1].split(" ")[0]
                try:
                    from urllib import unquote
                except:
                    from urllib.parse import unquote
                feed_id = unquote(feed_id)
            except:
                feed_id = ""
            content = generate_hls(feed_id)
            headers = "HTTP/1.1 200 OK\r\nContent-Type: application/vnd.apple.mpegurl\r\nConnection: close\r\nContent-Length: %d\r\n\r\n" % len(content.encode('utf-8'))
            conn.sendall(headers.encode('utf-8') + content.encode('utf-8'))
            
        elif "GET /m3u?" in request:
            try:
                feed_id = request.split("GET /m3u?id=")[1].split(" ")[0]
                try:
                    from urllib import unquote
                except:
                    from urllib.parse import unquote
                feed_id = unquote(feed_id)
            except:
                feed_id = ""
            content = generate_m3u(feed_id)
            headers = "HTTP/1.1 200 OK\r\nContent-Type: audio/x-mpegurl\r\nContent-Disposition: inline; filename=\"play.m3u\"\r\nConnection: close\r\nContent-Length: %d\r\n\r\n" % len(content.encode('utf-8'))
            conn.sendall(headers.encode('utf-8') + content.encode('utf-8'))
            
        else:
            content = generate_html()
            headers = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\nContent-Length: %d\r\n\r\n" % len(content.encode('utf-8'))
            conn.sendall(headers.encode('utf-8') + content.encode('utf-8'))
    except Exception as e:
        log_debug("Handle error: %s" % str(e))
    finally:
        conn.close()

def _server_loop():
    global _running, _server_socket
    try:
        _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _server_socket.bind(('0.0.0.0', PORT))
        _server_socket.listen(10)
        log_debug("Socket server started on port %d" % PORT)
        
        while _running:
            try:
                conn, addr = _server_socket.accept()
                threading.Thread(target=_handle, args=(conn,)).start()
            except:
                pass
    except Exception as e:
        log_debug("Server loop error: %s" % str(e))

def start_server():
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_server_loop)
    _thread.daemon = True
    _thread.start()