import argparse
import socket
import time
import threading

BUFFER_SIZE = 65536


def receive_all(sock):
    chunks = []
    while True:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def split_http_response(response):
    marker = b"\r\n\r\n"
    pos = response.find(marker)
    if pos == -1:
        return response, b""
    return response[:pos].decode("iso-8859-1", errors="replace"), response[pos + len(marker):]


def tcp_request(proxy_host, proxy_port, path, show_body=True):
    if not path.startswith("/"):
        path = "/" + path

    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {proxy_host}:{proxy_port}\r\n"
        "Connection: close\r\n"
        "User-Agent: Python-Socket-Client\r\n"
        "\r\n"
    ).encode("iso-8859-1")

    start = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(10)
        s.connect((proxy_host, proxy_port))
        s.sendall(request)
        response = receive_all(s)
        elapsed_ms = (time.time() - start) * 1000

        header, body = split_http_response(response)
        print(f"[TCP] Request ke proxy: GET {path}")
        print(f"[TCP] Response diterima: {len(response)} bytes, waktu={elapsed_ms:.2f} ms")
        print("\n===== HEADER RESPONSE =====")
        print(header)

        if show_body:
            content_type = ""
            for line in header.split("\r\n"):
                if line.lower().startswith("content-type:"):
                    content_type = line.lower()
                    break
            print("\n===== BODY/PREVIEW =====")
            if "text" in content_type or "html" in content_type or "css" in content_type:
                print(body.decode("utf-8", errors="replace"))
            else:
                print(f"Body berupa file biner, ukuran {len(body)} bytes. Tidak ditampilkan di terminal.")
        return elapsed_ms
    finally:
        s.close()


def udp_qos(server_host, server_port, count, interval, timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    rtts = []
    sent = 0
    received = 0
    bytes_received = 0
    test_start = time.time()

    print(f"[UDP] Mengirim {count} paket ke {server_host}:{server_port}")
    for seq in range(1, count + 1):
        timestamp = time.time()
        payload = f"Ping {seq} {timestamp}".encode("utf-8")
        sent += 1
        try:
            sock.sendto(payload, (server_host, server_port))
            data, addr = sock.recvfrom(BUFFER_SIZE)
            recv_time = time.time()
            rtt_ms = (recv_time - timestamp) * 1000
            rtts.append(rtt_ms)
            received += 1
            bytes_received += len(data)
            print(f"Ping {seq}: reply dari {addr[0]}:{addr[1]}, RTT={rtt_ms:.2f} ms, payload={data.decode('utf-8', errors='replace')}")
        except socket.timeout:
            print(f"Ping {seq}: Request timed out")
        time.sleep(interval)

    duration = time.time() - test_start
    lost = sent - received
    packet_loss = (lost / sent) * 100 if sent else 0
    throughput_kbps = (bytes_received * 8 / duration) / 1000 if duration > 0 else 0

    if rtts:
        rtt_min = min(rtts)
        rtt_avg = sum(rtts) / len(rtts)
        rtt_max = max(rtts)
    else:
        rtt_min = rtt_avg = rtt_max = 0

    if len(rtts) > 1:
        diffs = [abs(rtts[i] - rtts[i - 1]) for i in range(1, len(rtts))]
        jitter = sum(diffs) / len(diffs)
    else:
        jitter = 0

    print("\n===== STATISTIK QoS UDP =====")
    print(f"Paket dikirim     : {sent}")
    print(f"Paket diterima    : {received}")
    print(f"Paket hilang      : {lost}")
    print(f"Packet Loss       : {packet_loss:.2f}%")
    print(f"RTT min/avg/max   : {rtt_min:.2f} / {rtt_avg:.2f} / {rtt_max:.2f} ms")
    print(f"Jitter            : {jitter:.2f} ms")
    print(f"Throughput        : {throughput_kbps:.3f} kbps")
    print(f"Durasi pengujian  : {duration:.2f} detik")
    sock.close()


def run_multi(proxy_host, proxy_port, path, clients):
    print(f"[MULTI] Menjalankan {clients} client TCP bersamaan ke path {path}")
    results = []
    lock = threading.Lock()

    def worker(i):
        try:
            elapsed = tcp_request(proxy_host, proxy_port, path, show_body=False)
            with lock:
                results.append(elapsed)
            print(f"[MULTI] Client-{i} selesai {elapsed:.2f} ms")
        except Exception as exc:
            print(f"[MULTI] Client-{i} error: {exc}")

    threads = []
    for i in range(1, clients + 1):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    if results:
        print("\n===== HASIL MULTI-CLIENT =====")
        print(f"Jumlah sukses      : {len(results)}/{clients}")
        print(f"Waktu min/avg/max  : {min(results):.2f} / {sum(results)/len(results):.2f} / {max(results):.2f} ms")


def main():
    parser = argparse.ArgumentParser(description="Client TCP/UDP untuk tugas Client-Proxy-WebServer berbasis socket")
    parser.add_argument("--mode", choices=["tcp", "udp", "multi"], default="tcp", help="Mode client: tcp, udp, atau multi")
    parser.add_argument("--proxy-host", default="127.0.0.1", help="Alamat proxy")
    parser.add_argument("--proxy-port", type=int, default=8080, help="Port proxy")
    parser.add_argument("--server-host", default="127.0.0.1", help="Alamat UDP web server")
    parser.add_argument("--server-port", type=int, default=9000, help="Port UDP web server")
    parser.add_argument("--path", default="/index.html", help="Path file HTTP, contoh: /index.html")
    parser.add_argument("--count", type=int, default=10, help="Jumlah paket UDP")
    parser.add_argument("--interval", type=float, default=0.2, help="Jeda antar paket UDP dalam detik")
    parser.add_argument("--timeout", type=float, default=1.0, help="Timeout UDP per paket dalam detik")
    parser.add_argument("--clients", type=int, default=5, help="Jumlah client untuk mode multi")
    args = parser.parse_args()

    if args.mode == "tcp":
        tcp_request(args.proxy_host, args.proxy_port, args.path)
    elif args.mode == "udp":
        udp_qos(args.server_host, args.server_port, args.count, args.interval, args.timeout)
    elif args.mode == "multi":
        run_multi(args.proxy_host, args.proxy_port, args.path, args.clients)


if __name__ == "__main__":
    main()
