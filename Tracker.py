import socket
import struct
import random
import requests
import bencodepy
from urllib.parse import urlparse

class Tracker:
    """Handles communication with a tracker."""
    def __init__(self, torrent, peer_id, print_lock):
        self.torrent = torrent
        self.peer_id = peer_id
        self.print_lock = print_lock

    def get_peers(self):
        """Gets a list of peers from the tracker."""
        peers = set()
        for tier in self.torrent.announce_list:
            for announce_url in tier:
                try:
                    url = announce_url.decode('utf-8')
                    if url.startswith('udp'):
                        new_peers = self.get_peers_udp(url)
                    else:
                        new_peers = self.get_peers_http(url)
                    
                    peers.update(new_peers)
                    if peers:
                        return list(peers) # Return as soon as we get some peers
                except Exception as e:
                    with self.print_lock:
                        print(f"\nError getting peers from {announce_url.decode('utf-8')}: {e}")
        return list(peers)

    def get_peers_http(self, announce_url):
        """Gets peers from an HTTP tracker."""
        params = {
            'info_hash': self.torrent.info_hash,
            'peer_id': self.peer_id,
            'port': 6881,
            'uploaded': 0,
            'downloaded': 0,
            'left': self.torrent.total_size,
            'compact': 1,
            'event': 'started'
        }
        
        try:
            response = requests.get(announce_url, params=params, timeout=10)
            response.raise_for_status()
            tracker_response = bencodepy.decode(response.content)
            
            peers = []
            if isinstance(tracker_response[b'peers'], bytes):
                for i in range(0, len(tracker_response[b'peers']), 6):
                    ip = socket.inet_ntoa(tracker_response[b'peers'][i:i+4])
                    port = struct.unpack('!H', tracker_response[b'peers'][i+4:i+6])[0]
                    peers.append((ip, port))
            else:
                for peer_info in tracker_response[b'peers']:
                    peers.append((peer_info[b'ip'].decode('utf-8'), peer_info[b'port']))
            return peers
        except requests.RequestException as e:
            with self.print_lock:
                print(f"\nHTTP tracker request failed: {e}")
            return []

    def get_peers_udp(self, announce_url):
        """Gets peers from a UDP tracker."""
        parsed_url = urlparse(announce_url)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(8)

        try:
            conn_id = 0x41727101980
            transaction_id = random.randint(0, 2**32 - 1)
            
            packet = struct.pack('!QII', conn_id, 0, transaction_id)
            sock.sendto(packet, (parsed_url.hostname, parsed_url.port))
            
            res, _ = sock.recvfrom(16)
            action, res_transaction_id, conn_id = struct.unpack('!IIQ', res)
            
            if action != 0 or transaction_id != res_transaction_id:
                raise Exception("UDP tracker connection failed")

            transaction_id = random.randint(0, 2**32 - 1)
            packet = struct.pack('!QII20s20sQQQIIIIH',
                                 conn_id, 1, transaction_id,
                                 self.torrent.info_hash, self.peer_id.encode('utf-8'),
                                 0, self.torrent.total_size, 0,
                                 2, 0, random.randint(0, 2**32-1), -1, 6881)
            sock.sendto(packet, (parsed_url.hostname, parsed_url.port))
            
            res, _ = sock.recvfrom(2048)
            action, res_transaction_id = struct.unpack('!II', res[:8])
            
            if action != 1 or transaction_id != res_transaction_id:
                raise Exception("UDP tracker announce failed")
            
            peers = []
            for i in range(20, len(res), 6):
                ip, port = struct.unpack('!IH', res[i:i+6])
                peers.append((socket.inet_ntoa(struct.pack('!I', ip)), port))

            return peers
        except Exception as e:
            with self.print_lock:
                print(f"\nUDP tracker error: {e}")
            return []
        finally:
            sock.close()
