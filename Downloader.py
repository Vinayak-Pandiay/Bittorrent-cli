import time
import threading
import random
import string

from Torrent import Torrent
from Tracker import Tracker
from peer import Peer
from peice import PieceManager

class Downloader:
    """Orchestrates the download process."""
    def __init__(self, torrent_file_path, download_dir):
        self.print_lock = threading.Lock()
        self.torrent = Torrent(torrent_file_path)
        self.peer_id = '-PY0001-' + ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        self.piece_manager = PieceManager(self.torrent, download_dir, self.print_lock)
        self.tracker = Tracker(self.torrent, self.peer_id, self.print_lock)
        self.peers = []
        self.is_running = True
        self.data_lock = threading.Lock()

    def start(self):
        """Starts the download by launching peer and status threads."""
        with self.print_lock:
            print(f"Starting download for: {self.torrent}")
        
        peers_list = self.tracker.get_peers()
        with self.print_lock:
            print(f"Found {len(peers_list)} peers.")
        
        for ip, port in peers_list:
            peer = Peer(ip, port, self.torrent, self.peer_id)
            if peer.connect():
                self.peers.append(peer)
                with self.print_lock:
                    print(f"Connected to peer: {ip}:{port}")
                threading.Thread(target=self.peer_loop, args=(peer,), daemon=True).start()
        
        threading.Thread(target=self.status_loop, daemon=True).start()
        return


    def peer_loop(self, peer):
        while self.is_running and peer.sock:
            try:
                msg = peer.receive_message()
                if msg and msg[0] == 'piece':
                    _, piece_index, block_offset, block_data = msg
                    with self.data_lock:
                        self.piece_manager.receive_block(piece_index, block_offset, block_data)

                if not peer.peer_choking:
                    peer.send_interested()
                    if peer.bitfield:
                        piece_to_download = None
                        with self.data_lock:
                            piece_to_download = self.piece_manager.get_piece_to_download(peer.bitfield)
                        
                        if piece_to_download:
                            block_to_request = piece_to_download.get_block_to_request()
                            if block_to_request:
                                peer.send_request(piece_to_download.index, block_to_request['offset'], block_to_request['length'])
                
                time.sleep(0.01)
            except Exception as e:
                with self.print_lock:
                    print(f"\nError in peer loop for {peer.ip}:{peer.port}: {e}")
                break
        
        peer.close()
        if peer in self.peers:
            self.peers.remove(peer)

    def status_loop(self):
        while self.is_running:
            if self.piece_manager.is_complete():
                with self.print_lock:
                    print("\nDownload complete!")
                self.stop()
                break

            try:
                with self.data_lock:
                    needed_pieces_count = len(self.piece_manager.needed_pieces)
                
                progress = (self.piece_manager.downloaded_size / self.torrent.total_size) * 100 if self.torrent.total_size > 0 else 0
                dl_mb = self.piece_manager.downloaded_size / 1024 / 1024
                total_mb = self.torrent.total_size / 1024 / 1024
                status_line = (f"Progress: {progress:.2f}% | "
                               f"Downloaded: {dl_mb:.2f}/{total_mb:.2f} MB | "
                               f"Peers: {len(self.peers)} | "
                               f"Needed Pieces: {needed_pieces_count}   ")
                with self.print_lock:
                    print(status_line, end='\r')
            except ZeroDivisionError:
                with self.print_lock:
                    print("Calculating status...", end='\r')

            time.sleep(1)

    def stop(self):
        if self.is_running:
            self.is_running = False
            # No need to print here, main will handle final messages
            for peer in self.peers:
                peer.close()
