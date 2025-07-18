import socket
import struct
import time

class Peer:
    """Represents a peer connection in the swarm."""
    def __init__(self, ip, port, torrent, peer_id):
        self.ip = ip
        self.port = port
        self.torrent = torrent
        self.peer_id = peer_id
        self.sock = None
        self.is_choking = True
        self.is_interested = False
        self.peer_choking = True
        self.peer_interested = False
        self.bitfield = None
        self.buffer = b''
        self.last_message_time = time.time()

    def connect(self):
        """Connects to the peer."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.ip, self.port))
            self.handshake()
            return True
        except Exception:
            self.close()
            return False

    def handshake(self):
        """Performs the BitTorrent handshake."""
        pstr = b'BitTorrent protocol'
        pstrlen = len(pstr)
        handshake_msg = struct.pack('!B19s8x20s20s', pstrlen, pstr, self.torrent.info_hash, self.peer_id.encode('utf-8'))
        self.sock.send(handshake_msg)
        
        response = self.sock.recv(68)
        if len(response) < 68:
            raise Exception("Handshake response too short")
            
        _, _, info_hash, _ = struct.unpack('!B19s8x20s20s', response)
        if info_hash != self.torrent.info_hash:
            raise Exception("Info hash mismatch")

    def send_interested(self):
        """Sends an interested message."""
        if self.sock and not self.is_interested:
            msg = struct.pack('!IB', 1, 2)
            self.sock.send(msg)
            self.is_interested = True

    def send_request(self, piece_index, block_offset, block_length):
        """Sends a request for a block."""
        if self.sock:
            msg = struct.pack('!IBIII', 13, 6, piece_index, block_offset, block_length)
            self.sock.send(msg)

    def receive_message(self):
        """Receives and processes a message from the peer."""
        if not self.sock:
            return None

        try:
            self.sock.settimeout(1)
            data = self.sock.recv(4096)
            if not data:
                self.close()
                return None
            self.buffer += data
            self.last_message_time = time.time()
        except socket.timeout:
            return None
        except Exception:
            self.close()
            return None

        while len(self.buffer) >= 4:
            msg_len = struct.unpack('!I', self.buffer[:4])[0]
            if len(self.buffer) < 4 + msg_len:
                break
            
            packet = self.buffer[4:4+msg_len]
            self.buffer = self.buffer[4+msg_len:]
            
            if msg_len == 0: continue

            msg_id = packet[0]
            payload = packet[1:]
            
            if msg_id == 0: self.peer_choking = True
            elif msg_id == 1: self.peer_choking = False
            elif msg_id == 2: self.peer_interested = True
            elif msg_id == 3: self.peer_interested = False
            elif msg_id == 4:
                piece_index = struct.unpack('!I', payload)[0]
                if self.bitfield:
                    self.bitfield[piece_index // 8] |= (1 << (7 - piece_index % 8))
            elif msg_id == 5: self.bitfield = bytearray(payload)
            elif msg_id == 7:
                piece_index, block_offset = struct.unpack('!II', payload[:8])
                block_data = payload[8:]
                return ('piece', piece_index, block_offset, block_data)
        return None

    def close(self):
        """Closes the connection."""
        if self.sock:
            self.sock.close()
            self.sock = None