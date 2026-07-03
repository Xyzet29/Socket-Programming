import os
import socket
import threading
import mimetypes
from datetime import datetime
from urllib.parse import unquote

HOST = "YOUR_HOST"
HTTP_PORT = 8000
UDP_PORT = 9000
WEB_ROOT = "HTML"
BUFFER_SIZE = 65536


def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [WEB] {message}", flush=True)


def safe_path(url_path):
    path = url_path.split("?", 1)[0]
    path = unquote(path)
    if path == "/":
        path = "/index.html"
    path = path.lstrip("/")
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or os.path.isabs(normalized):
        return None
    return os.path.join(WEB_ROOT, normalized)


def read_file_bytes(filepath):
    with open(filepath, "rb") as f:
        return f.read()


def build_response(status_code, reason, body, content_type="text/html; charset=utf-8"):
    header = (
        f"HTTP/1.1 {status_code} {reason}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "Server: Python-Socket-WebServer\r\n"
        "\r\n"
    )
    return header.encode("iso-8859-1") + body


def error_response(status_code, reason):
    status_file = os.path.join(WEB_ROOT, "status", f"{status_code}.html")
    try:
        body = read_file_bytes(status_file)
    except Exception:
        body = f"<html><body><h1>{status_code} {reason}</h1></body></html>".encode("utf-8")
    return build_response(status_code, reason, body)


def parse_request(data):
    try:
        text = data.decode("iso-8859-1", errors="replace")
        first_line = text.split("\r\n", 1)[0]
        parts = first_line.split()
        if len(parts) < 3:
            return None, None, None
        return parts[0], parts[1], parts[2]
    except Exception:
        return None, None, None


def handle_http_client(conn, addr):
    client_ip, client_port = addr
    thread_name = threading.current_thread().name
    try:
        conn.settimeout(5)
        request = conn.recv(BUFFER_SIZE)
        if not request:
            return

        method, path, version = parse_request(request)
        log(f"Thread={thread_name} request dari {client_ip}:{client_port} -> {method} {path}")

        if method != "GET" or path is None:
            response = build_response(400, "Bad Request", b"<html><body><h1>400 Bad Request</h1></body></html>")
            conn.sendall(response)
            return

        filepath = safe_path(path)
        if filepath is None:
            response = error_response(404, "Not Found")
            conn.sendall(response)
            log(f"404 path tidak aman dari {client_ip}: {path}")
            return

        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            response = error_response(404, "Not Found")
            conn.sendall(response)
            log(f"404 Not Found: {path} dari {client_ip}")
            return

        try:
            body = read_file_bytes(filepath)
            content_type, _ = mimetypes.guess_type(filepath)
            if content_type is None:
                content_type = "application/octet-stream"
            response = build_response(200, "OK", body, content_type)
            conn.sendall(response)
            log(f"200 OK: {path} ({len(body)} bytes) untuk {client_ip}")
        except Exception as exc:
            response = error_response(500, "Internal Server Error")
            conn.sendall(response)
            log(f"500 Internal Server Error untuk {path}: {exc}")
    except socket.timeout:
        log(f"Timeout koneksi HTTP dari {client_ip}:{client_port}")
    except Exception as exc:
        log(f"Error HTTP dari {client_ip}:{client_port}: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
        log(f"Thread={thread_name} selesai untuk {client_ip}:{client_port}")


def run_http_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, HTTP_PORT))
    server.listen(50)
    log(f"HTTP server running on port {HTTP_PORT}")
    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_http_client, args=(conn, addr), daemon=True)
        t.start()
        log(f"Thread baru dibuat untuk HTTP client {addr[0]}:{addr[1]}")


def run_udp_echo_server():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind((HOST, UDP_PORT))
    log(f"UDP echo server running on port {UDP_PORT}")
    while True:
        try:
            data, addr = udp.recvfrom(BUFFER_SIZE)
            udp.sendto(data, addr)
            log(f"UDP echo ke {addr[0]}:{addr[1]} payload={data.decode('utf-8', errors='replace')}")
        except Exception as exc:
            log(f"Error UDP: {exc}")


def main():
    if not os.path.isdir(WEB_ROOT):
        raise SystemExit(f"Folder {WEB_ROOT}/ tidak ditemukan. Ekstrak HTML for TESTING.zip dahulu.")
    threading.Thread(target=run_udp_echo_server, daemon=True).start()
    run_http_server()


if __name__ == "__main__":
    main()
