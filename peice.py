import os
import hashlib
import random

class Piece:
    """Represents a single piece of the torrent."""
    def __init__(self, index, torrent):
        self.index = index
        self.torrent = torrent
        self.length = torrent.piece_length if index < (len(torrent.pieces) // 20 - 1) else torrent.total_size % torrent.piece_length
        if self.length == 0: self.length = torrent.piece_length
        self.hash = torrent.pieces[index*20 : (index+1)*20]
        self.data = None
        self.blocks = []
        self.is_complete = False
        self.is_downloading = False
        self.init_blocks()

    def init_blocks(self):
        """Initializes the blocks for the piece."""
        self.blocks = []
        num_blocks = (self.length + 16383) // 16384
        for i in range(num_blocks):
            offset = i * 16384
            length = min(16384, self.length - offset)
            self.blocks.append({'offset': offset, 'length': length, 'status': 'needed'})

    def add_block(self, offset, data):
        """Adds a block to the piece."""
        self.data[offset:offset+len(data)] = data
        for block in self.blocks:
            if block['offset'] == offset:
                block['status'] = 'downloaded'
                break
        
        if all(b['status'] == 'downloaded' for b in self.blocks):
            self.is_complete = True
            self.is_downloading = False

    def get_block_to_request(self):
        for block in self.blocks:
            if block['status'] == 'needed':
                block['status'] = 'requested'
                return block
        return None

    def is_hash_correct(self):
        return hashlib.sha1(self.data).digest() == self.hash

    def reset(self):
        self.data = None
        self.is_complete = False
        self.is_downloading = False
        self.init_blocks()

class PieceManager:
    def __init__(self, torrent, download_dir, print_lock):
        self.torrent = torrent
        self.download_dir = download_dir
        self.print_lock = print_lock
        self.bitfield = bytearray((len(torrent.pieces) // 20 + 7) // 8)
        self.pieces = [Piece(i, torrent) for i in range(len(torrent.pieces) // 20)]
        self.needed_pieces = list(self.pieces)
        random.shuffle(self.needed_pieces)
        self.completed_pieces = 0
        self.downloaded_size = 0
        self.init_files()

    def init_files(self):
        for file_info in self.torrent.files:
            path = os.path.join(self.download_dir, file_info['path'])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if not os.path.exists(path):
                with open(path, 'wb') as f:
                    f.truncate(file_info['length'])

    def get_piece_to_download(self, peer_bitfield):
        for i, piece in enumerate(self.needed_pieces):
            if not piece.is_downloading: # Check if piece is already being downloaded
                piece_index = piece.index
                if (peer_bitfield[piece_index // 8] >> (7 - piece_index % 8)) & 1:
                    piece.is_downloading = True
                    return self.needed_pieces.pop(i)
        return None

    def receive_block(self, piece_index, block_offset, data):
        piece = self.pieces[piece_index]
        if not piece.is_complete:
            if piece.data is None:
                piece.data = bytearray(piece.length)

            piece.add_block(block_offset, data)
            if piece.is_complete:
                if piece.is_hash_correct():
                    self.write_piece_to_disk(piece)
                    self.completed_pieces += 1
                    self.downloaded_size += piece.length
                    self.bitfield[piece_index // 8] |= (1 << (7 - piece_index % 8))
                    with self.print_lock:
                        print(f"\nPiece {piece_index} completed and verified. ({self.completed_pieces}/{len(self.pieces)})")
                else:
                    with self.print_lock:
                        print(f"\nPiece {piece_index} hash check failed. Redownloading.")
                    piece.reset()
                    self.needed_pieces.insert(0, piece)

    def write_piece_to_disk(self, piece):
        piece_offset = piece.index * self.torrent.piece_length
        current_pos = 0
        for file_info in self.torrent.files:
            file_start = current_pos
            file_end = file_start + file_info['length']
            
            if piece_offset < file_end and (piece_offset + piece.length) > file_start:
                write_start = max(piece_offset, file_start)
                write_end = min(piece_offset + piece.length, file_end)
                
                data_start = write_start - piece_offset
                data_end = write_end - piece_offset
                data_to_write = piece.data[data_start:data_end]
                
                file_pos = write_start - file_start
                path = os.path.join(self.download_dir, file_info['path'])
                with open(path, 'r+b') as f:
                    f.seek(file_pos)
                    f.write(data_to_write)
            
            current_pos = file_end
        
        piece.data = None

    def is_complete(self):
        return self.completed_pieces == len(self.pieces)