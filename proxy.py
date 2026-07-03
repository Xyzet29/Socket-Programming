from socket import *
import threading
import os
import time
from datetime import datetime

# Konfigurasi Proxy dan Web Server
PROXY_HOST = "YOUR_PROXY_HOST"
PROXY_PORT = 8080

WEB_SERVER_HOST = "YOUR_WEB_SERVER_HOST"
WEB_SERVER_PORT = 8000

BUFFER_SIZE = 65536
CACHE_DIR = "cache"

# Membuat folder cache jika belum ada
os.makedirs(CACHE_DIR, exist_ok=True)

# Lock untuk mencegah konflik akses cache saat multithreading
cache_lock = threading.Lock()


def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [PROXY] {message}", flush=True)


def handle_client(clientSock, addr):
    start_time = time.time()
    thread_name = threading.current_thread().name

    try:
        # Menerima request dari client
        request = clientSock.recv(BUFFER_SIZE)

        if not request:
            return

        request_text = request.decode("iso-8859-1", errors="ignore")

        # Parsing request HTTP
        parts = first_line.split()

        if len(parts) < 3:
            log(f"Request tidak valid dari {addr[0]}:{addr[1]}")
            return

        method = parts[0]
        path = parts[1]

        # Proxy hanya melayani HTTP GET
        if method != "GET":
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Length: 0\r\n"
                "Connection: close\r\n\r\n"
            )
            clientSock.sendall(response.encode())
            return

        if path == "/":
            path = "/index.html"

        cache_file = os.path.join(CACHE_DIR, path.strip("/").replace("/", "_"))
    
        # CACHE HIT
        with cache_lock:
            if os.path.exists(cache_file):

                with open(cache_file, "rb") as f:
                    cached_response = f.read()

                clientSock.sendall(cached_response)

                elapsed = (time.time() - start_time) * 1000

                log(
                    f"Thread={thread_name} "
                    f"{addr[0]}:{addr[1]} "
                    f"GET {path} -> Cache HIT, {elapsed:.2f} ms"
                )

                return

        # CACHE MISS
        log(
            f"Thread={thread_name} "
            f"{addr[0]}:{addr[1]} "
            f"GET {path} -> Cache MISS"
        )

        # Membuka koneksi ke web server
        serverSock.settimeout(5)

        try:
            serverSock.connect((WEB_SERVER_HOST, WEB_SERVER_PORT))

            # Forward request ke web server
            forward_request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {WEB_SERVER_HOST}\r\n"
                "Connection: close\r\n\r\n"
            )

            serverSock.sendall(forward_request.encode())

            # Menerima seluruh response dari web server
            response = b""

            while True:
                data = serverSock.recv(BUFFER_SIZE)

                if not data:
                    break

                response += data

            # Simpan response sukses ke cache
            if response.startswith(b"HTTP/1.1 200") or response.startswith(b"HTTP/1.0 200"):

                with cache_lock:
                    with open(cache_file, "wb") as f:
                        f.write(response)

                log(f"Cache disimpan: {path}")

            # Kirim response ke client
            clientSock.sendall(response)

            elapsed = (time.time() - start_time) * 1000

            log(
                f"Thread={thread_name} "
                f"{addr[0]}:{addr[1]} "
                f"Response selesai, {elapsed:.2f} ms"
            )

        # Web server terlalu lama merespons
        except timeout:
            log(
                f"Thread={thread_name} "
                f"{addr[0]}:{addr[1]} "
                f"-> 504 Gateway Timeout"
            )

            response = (
                "HTTP/1.1 504 Gateway Timeout\r\n"
                "Content-Length: 0\r\n"
                "Connection: close\r\n\r\n"
            )

            clientSock.sendall(response.encode())

        # Gagal terhubung ke web server
        except Exception:
            log(
                f"Thread={thread_name} "
                f"{addr[0]}:{addr[1]} "
                f"-> 502 Bad Gateway"
            )

            response = (
                "HTTP/1.1 502 Bad Gateway\r\n"
                "Content-Length: 0\r\n"
                "Connection: close\r\n\r\n"
            )

            clientSock.sendall(response.encode())

        finally:
            serverSock.close()

    # Menangani error tak terduga pada client
    except Exception as e:
        log(f"Client Error {addr}: {e}")

    finally:
        clientSock.close()


def main():
    # Membuat socket proxy TCP
    proxySock = socket(AF_INET, SOCK_STREAM)
    proxySock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    proxySock.bind((PROXY_HOST, PROXY_PORT))
    proxySock.listen(10)

    log(f"Proxy listening on port {PROXY_PORT}")
    log(f"Forward target web server: {WEB_SERVER_HOST}:{WEB_SERVER_PORT}")

    try:
        while True:
            clientSock, addr = proxySock.accept()

            log(f"Thread baru dibuat untuk client {addr[0]}:{addr[1]}")

            # Setiap client ditangani oleh thread terpisah
            threading.Thread(target=handle_client, args=(clientSock, addr), daemon=True).start()

    except KeyboardInterrupt:
        log("Proxy dihentikan")

    finally:
        proxySock.close()


if __name__ == "__main__":
    main()