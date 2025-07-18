import argparse
import os
from Downloader import Downloader

def main():
    """Main function to run the BitTorrent client from the command line."""
    parser = argparse.ArgumentParser(description="A simple BitTorrent client.")
    parser.add_argument("torrent_file", help="Path to the .torrent file.")
    parser.add_argument("-d", "--download_dir", default=".", help="Directory to save the downloaded files.")
    args = parser.parse_args()

    torrent_file = args.torrent_file
    download_dir = args.download_dir
    

    if not os.path.exists(torrent_file):
        print(f"Error: Torrent file not found at '{torrent_file}'")
        return

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"Created download directory at '{download_dir}'")

    print("Starting BitTorrent Client...")
    print("Commands: 'q' (quit) or Ctrl+C")
    
    client = Downloader(torrent_file, download_dir)
    try:
        client.start()
        # The main thread will now handle user input and wait for the download to finish
        while client.is_running:
            try:
                cmd = input()
                if cmd.lower() == 'q':
                    print("\nQuitting...")
                    break # Exit the loop, finally will handle shutdown
            except (EOFError, KeyboardInterrupt) as e:
                # This handles Ctrl+D and cases where input stream is closed
                print("\nInput stream closed. Shutting down...")
                break
        

    except KeyboardInterrupt as e:
        # This handles Ctrl+C
        print("\nCtrl+C detected. Shutting down...")
    finally:
        if client.is_running:
            client.stop()
        print("Client has shut down.")

if __name__ == '__main__':
    main()