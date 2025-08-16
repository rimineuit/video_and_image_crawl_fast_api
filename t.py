import socket

ip = "27.79.213.13"
ports = [16000]

def check_port(ip, port, timeout=3):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        return True
    except:
        return False
    finally:
        sock.close()

for port in ports:
    if check_port(ip, port):
        print(f"✅ Port {port} mở trên {ip}")
    else:
        print(f"❌ Port {port} đóng hoặc không phản hồi")
