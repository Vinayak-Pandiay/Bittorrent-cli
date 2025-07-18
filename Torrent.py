import bencodepy
import hashlib
import os

class Torrent:
    """Represents and parses a .torrent file."""
    def __init__(self, torrent_file_path):
        with open(torrent_file_path, 'rb') as f:
            meta_info = bencodepy.decode(f.read())

        self.info = meta_info[b'info']
        self.info_hash = hashlib.sha1(bencodepy.encode(self.info)).digest()
        self.announce_list = meta_info.get(b'announce-list', [[meta_info[b'announce']]])
        self.piece_length = self.info[b'piece length']
        self.pieces = self.info[b'pieces']
        self.total_size = 0

        if b'files' in self.info:
            # Multi-file torrent
            self.files = []
            for file_info in self.info[b'files']:
                self.files.append({
                    'path': os.path.join(*[p.decode('utf-8') for p in file_info[b'path']]),
                    'length': file_info[b'length']
                })
                self.total_size += file_info[b'length']
        else:
            # Single-file torrent
            self.files = [{
                'path': self.info[b'name'].decode('utf-8'),
                'length': self.info[b'length']
            }]
            self.total_size = self.info[b'length']
