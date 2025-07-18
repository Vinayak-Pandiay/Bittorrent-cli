# Python BitTorrent Client 🚀<br>
Hey there! Welcome to my simple BitTorrent client, built from the ground up in Python.

This project was a fun dive into the BitTorrent protocol. It's a command-line tool that can download files using .torrent files, and it's built to be as clear and understandable. If you're curious about how BitTorrent works under the hood, [Check out this playlist!](https://www.youtube.com/playlist?list=PLsdq-3Z1EPT1rNeq2GXpnivaWINnOaCd0)

<h2>Features:</h2>
Reads .torrent files: It knows how to parse all the important info from a torrent file, whether it's for a single file or a whole folder.<br>

Talks to Trackers: It can connect to both HTTP and UDP trackers to find other people (peers) sharing the file.<br>

Downloads in Parallel: Uses multi-threading to connect to many peers at once, which is the secret sauce to getting those sweet, fast download speeds.although same can be achived using asyncio.<br>

Clean Code: I've tried to keep the code organized into different files, with each class having a single job. This makes it much easier to follow along and see how everything fits together.<br>
<h2>Basic Run:</h2>
<pre lang=LANG>
python main.py /path/to/your/file.torrent
</pre>

Choose a Download Folder:to specifi a download directory use the -d flag.
<pre lang=LANG>
python main.py /path/to/your/file.torrent -d /path/to/your/downloads
</pre>
<h2>How the Code is Organized</h2>
The client is broken down into a few key files:<br>

main.py: This is where the magic starts! It handles the command-line inputs and kicks off the whole process.<br>

downloader.py: The "brain" of the operation. It gets everything started and keeps track of the download.<br>

torrent.py: This little guy is in charge of reading and understanding the .torrent files.<br>

tracker.py: Its job is to call up the trackers and ask forll list of peers.<br>

peer.py: Handles the one-on-one chat with another peer, requesting data and putting it all together.<br>

piece.py: Manages all the individual pieces of the file, making sure none are missing and that they all pass their hash checks before being saved.<br>

<h2></h2>
While this is fullyfunctional downloader it is not optimized or feature rich as other options out there, but it gets job done! i use this to download slow and huge torrent on cloud then downlad at fast speed from there. for such purposes it's okay and preety fun.
please feel free to improve or tinker with this project!
