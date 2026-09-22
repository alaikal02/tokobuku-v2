#!/usr/bin/env python3
"""
DARUSSHOLAH - TOKOBUKU-V2 BACKEND SERVER
Serves static frontend files and provides REST API for books CRUD & cover image uploads.
"""

import os
import sys
import json
import time
import re
import base64
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKS_FILE = os.path.join(BASE_DIR, "books.json")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOADS_DIR, exist_ok=True)

def load_books():
    if not os.path.exists(BOOKS_FILE):
        return []
    try:
        with open(BOOKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading books: {e}")
        return []

def save_books(books):
    with open(BOOKS_FILE, "w", encoding="utf-8") as f:
        json.dump(books, f, indent=2, ensure_ascii=False)

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

class TokobukuHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def _send_json(self, data, status_code=200):
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/books":
            books = load_books()
            self._send_json(books)
            return

        # Fallback to standard static file serving
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if path == "/api/books":
            try:
                book_data = json.loads(body.decode("utf-8"))
                books = load_books()
                
                # Check if updating existing book
                book_id = book_data.get("id")
                if not book_id:
                    book_id = slugify(book_data.get("title", f"buku-{int(time.time())}"))
                    book_data["id"] = book_id

                existing_idx = None
                for idx, b in enumerate(books):
                    if b.get("id") == book_id or (b.get("altId") and b.get("altId") == book_id):
                        existing_idx = idx
                        break

                if existing_idx is not None:
                    # Update existing
                    merged = {**books[existing_idx], **book_data}
                    books[existing_idx] = merged
                    saved_book = merged
                else:
                    # Insert new
                    books.append(book_data)
                    saved_book = book_data

                save_books(books)
                self._send_json({"success": True, "book": saved_book})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status_code=400)
            return

        if path == "/api/upload":
            try:
                content_type = self.headers.get("Content-Type", "")
                
                # Handle base64 JSON payload
                if "application/json" in content_type:
                    payload = json.loads(body.decode("utf-8"))
                    filename = payload.get("filename", f"cover_{int(time.time())}.jpg")
                    data_str = payload.get("data", "")
                    
                    if "," in data_str:
                        _, b64data = data_str.split(",", 1)
                    else:
                        b64data = data_str
                    
                    file_bytes = base64.b64decode(b64data)
                    clean_name = f"{int(time.time())}_{slugify(os.path.splitext(filename)[0])}{os.path.splitext(filename)[1]}"
                    target_path = os.path.join(UPLOADS_DIR, clean_name)
                    
                    with open(target_path, "wb") as f:
                        f.write(file_bytes)
                    
                    file_url = f"/uploads/{clean_name}"
                    self._send_json({"success": True, "url": file_url, "filename": clean_name})
                    return

                # Handle raw multipart / binary
                clean_name = f"upload_{int(time.time())}.jpg"
                target_path = os.path.join(UPLOADS_DIR, clean_name)
                with open(target_path, "wb") as f:
                    f.write(body)
                
                self._send_json({"success": True, "url": f"/uploads/{clean_name}", "filename": clean_name})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status_code=400)
            return

        self._send_json({"error": "Not Found"}, status_code=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/books/"):
            target_id = path.replace("/api/books/", "").strip()
            books = load_books()
            new_books = [b for b in books if b.get("id") != target_id and b.get("altId") != target_id]
            
            if len(new_books) == len(books):
                self._send_json({"success": False, "message": "Book not found"}, status_code=404)
                return
            
            save_books(new_books)
            self._send_json({"success": True, "deletedId": target_id})
            return

        self._send_json({"error": "Not Found"}, status_code=404)

def run():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, TokobukuHandler)
    print(f"Server backend & static aktif di http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
