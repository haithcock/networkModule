import argparse
import json
import os
import socket
import threading

BUF = 64 * 1024  # 64KB chunks


def send_json(sock: socket.socket, obj: dict) -> None:
    data = (json.dumps(obj) + "\n").encode("utf-8")
    sock.sendall(data)


def recv_json_line(sock_file) -> dict:
    line = sock_file.readline()
    if not line:
        raise ConnectionError("Connection closed")
    return json.loads(line)


def safe_shared_path(shared_dir: str, name: str) -> str | None:
    # Only allow plain filenames that exist in shared_dir (prevents ../../etc/passwd)
    if not name or os.path.basename(name) != name:
        return None
    path = os.path.join(shared_dir, name)
    # Ensure it stays inside shared_dir
    shared_real = os.path.realpath(shared_dir)
    path_real = os.path.realpath(path)
    if not path_real.startswith(shared_real + os.sep) and path_real != shared_real:
        return None
    return path


def list_files(shared_dir: str):
    files = []
    for entry in os.listdir(shared_dir):
        p = os.path.join(shared_dir, entry)
        if os.path.isfile(p):
            try:
                files.append({"name": entry, "size": os.path.getsize(p)})
            except OSError:
                # If stat fails, skip
                pass
    files.sort(key=lambda x: x["name"].lower())
    return files


def handle_connection(conn: socket.socket, addr, shared_dir: str):
    try:
        conn_file = conn.makefile("rwb", buffering=0)
        # Read exactly one request, respond, then close (keeps it simple)
        req = recv_json_line(conn_file)

        rtype = req.get("type", "").upper()

        if rtype == "PING":
            send_json(conn, {"type": "PONG"})
            return

        if rtype == "LIST":
            send_json(conn, {"type": "LIST_OK", "files": list_files(shared_dir)})
            return

        if rtype == "INFO":
            name = req.get("name", "")
            path = safe_shared_path(shared_dir, name)
            if not path or not os.path.isfile(path):
                send_json(conn, {"type": "ERROR", "code": "NOT_FOUND", "message": "File not found"})
                return
            try:
                size = os.path.getsize(path)
                send_json(conn, {"type": "INFO_OK", "name": name, "size": size})
            except OSError:
                send_json(conn, {"type": "ERROR", "code": "IO_ERROR", "message": "Could not read file info"})
            return

        if rtype == "GET":
            name = req.get("name", "")
            path = safe_shared_path(shared_dir, name)
            if not path or not os.path.isfile(path):
                send_json(conn, {"type": "ERROR", "code": "NOT_FOUND", "message": "File not found"})
                return
            try:
                size = os.path.getsize(path)
                # Send header first
                send_json(conn, {"type": "GET_OK", "name": name, "size": size})
                # Then send raw bytes
                with open(path, "rb") as f:
                    while True:
                        chunk = f.read(BUF)
                        if not chunk:
                            break
                        conn.sendall(chunk)
            except PermissionError:
                send_json(conn, {"type": "ERROR", "code": "PERMISSION_DENIED", "message": "No permission to read file"})
            except OSError:
                send_json(conn, {"type": "ERROR", "code": "IO_ERROR", "message": "File read failed"})
            return

        send_json(conn, {"type": "ERROR", "code": "BAD_REQUEST", "message": "Unknown request type"})
    except json.JSONDecodeError:
        try:
            send_json(conn, {"type": "ERROR", "code": "BAD_JSON", "message": "Invalid JSON"})
        except Exception:
            pass
    except Exception:
        # Keep server stable; don't crash on unexpected client behavior
        try:
            send_json(conn, {"type": "ERROR", "code": "SERVER_ERROR", "message": "Server error"})
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def server_loop(host: str, port: int, shared_dir: str):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(50)
    print(f"[listen] {host}:{port} sharing: {os.path.abspath(shared_dir)}")

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=handle_connection, args=(conn, addr, shared_dir), daemon=True)
        t.start()


def client_request(ip: str, port: int, req: dict, downloads_dir: str):
    with socket.create_connection((ip, port), timeout=10) as sock:
        sock_file = sock.makefile("rb")
        send_json(sock, req)

        # Read response line
        line = sock_file.readline()
        if not line:
            raise ConnectionError("No response")
        resp = json.loads(line)

        rtype = resp.get("type", "")

        if rtype == "GET_OK":
            name = resp.get("name", "download.bin")
            size = int(resp.get("size", 0))
            os.makedirs(downloads_dir, exist_ok=True)
            out_path = os.path.join(downloads_dir, os.path.basename(name))

            remaining = size
            with open(out_path, "wb") as f:
                while remaining > 0:
                    chunk = sock_file.read(min(BUF, remaining))
                    if not chunk:
                        raise ConnectionError("Disconnected mid-transfer")
                    f.write(chunk)
                    remaining -= len(chunk)

            return {"type": "DOWNLOADED", "path": out_path, "size": size}

        return resp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--shared", default="shared")
    ap.add_argument("--downloads", default="downloads")
    args = ap.parse_args()

    shared_dir = args.shared
    downloads_dir = args.downloads
    os.makedirs(shared_dir, exist_ok=True)
    os.makedirs(downloads_dir, exist_ok=True)

    # Start server thread
    t = threading.Thread(target=server_loop, args=(args.host, args.port, shared_dir), daemon=True)
    t.start()

    print("Commands:")
    print("  connect <ip> <port>")
    print("  ping | list | info <name> | get <name>")
    print("  quit")

    peer = None  # (ip, port)

    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue
        if cmd == "quit":
            break

        parts = cmd.split()
        if parts[0] == "connect" and len(parts) == 3:
            peer = (parts[1], int(parts[2]))
            print(f"[ok] connected target set to {peer[0]}:{peer[1]}")
            continue

        if peer is None:
            print("[error] use: connect <ip> <port>")
            continue

        ip, port = peer

        try:
            if parts[0] == "ping":
                resp = client_request(ip, port, {"type": "PING"}, downloads_dir)
                print(resp)
            elif parts[0] == "list":
                resp = client_request(ip, port, {"type": "LIST"}, downloads_dir)
                if resp.get("type") == "LIST_OK":
                    for f in resp.get("files", []):
                        print(f'{f["name"]} ({f["size"]} bytes)')
                else:
                    print(resp)
            elif parts[0] == "info" and len(parts) == 2:
                resp = client_request(ip, port, {"type": "INFO", "name": parts[1]}, downloads_dir)
                print(resp)
            elif parts[0] == "get" and len(parts) == 2:
                resp = client_request(ip, port, {"type": "GET", "name": parts[1]}, downloads_dir)
                print(resp)
            else:
                print("[error] unknown command")
        except Exception as e:
            print(f"[error] {e}")


if __name__ == "__main__":
    main()
