# Socket Programming: Client - Proxy - Web Server

Implementasi sederhana **Client → Proxy Server → Web Server** menggunakan **Python Socket Programming**. Proyek ini mendukung komunikasi **HTTP (TCP)** dengan mekanisme **proxy caching** serta pengujian **UDP QoS**.

## Features

- HTTP Web Server (Multithread)
- HTTP Proxy Server dengan Cache (HIT/MISS)
- HTTP Client
- Multi-client TCP Testing
- UDP QoS Testing (RTT, Packet Loss, Jitter, Throughput)
- Error Handling (400, 404, 500, 502, 504)

## Project Structure

```text
.
├── client.py
├── proxy.py
├── webserver.py
├── HTML/
└── cache/
```

## Default Ports

| Service | Port |
|---------|------|
| HTTP Web Server | 8000 |
| HTTP Proxy | 8080 |
| UDP Server | 9000 |

## Configuration

Sesuaikan alamat host pada masing-masing file sebelum dijalankan.

```python
# webserver.py
HOST = "YOUR_HOST"

# proxy.py
PROXY_HOST = "YOUR_PROXY_HOST"
WEB_SERVER_HOST = "YOUR_WEB_SERVER_HOST"
```

## Running

Jalankan pada 3 terminal berbeda.

**Web Server**

```bash
python webserver.py
```

**Proxy Server**

```bash
python proxy.py
```

**Client**

```bash
python client.py
```

## Client Usage

### HTTP Request

```bash
python client.py --mode tcp
python client.py --mode tcp --path /index.html
```

### Multi Client

```bash
python client.py --mode multi
```

### UDP QoS

```bash
python client.py --mode udp
python client.py --mode udp --count 20
```

## Architecture

```text
Client
   │
   ▼
Proxy Server
   │
   ├── Cache HIT ─────────► Client
   │
   └── Cache MISS
           │
           ▼
      Web Server
           │
           ▼
        Response
```

## Troubleshooting

- Jalankan program dengan urutan:
  1. `webserver.py`
  2. `proxy.py`
  3. `client.py`
- Pastikan folder `HTML/` tersedia.
- Request pertama akan menghasilkan **Cache MISS**, sedangkan request berikutnya akan menjadi **Cache HIT**.