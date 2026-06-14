STEGOSHELL
data hidden, data secured
==========================

A steganography and crypto desktop app. The graded core is LSB image
steganography, following the Day 3 class slides for the hiding logic.


FILES
-----
app.py            The interface. Run this one.
stego_engine.py   Image LSB logic. This is the graded core.
audio_stego.py    Audio WAV LSB logic.
crypto_engine.py  AES crypto, shred, password tools, self decrypting export.
make_assets.py    Draws the logo and icons. Run it once if assets is missing.
assets/           My logo and icon PNGs. I drew these, they are not copied.
sample_cover.png  A test image you can hide data in straight away.


HOW TO RUN
----------
1. Open a terminal in this folder.
2. Install the libraries once:

   python -m pip install customtkinter pillow numpy cryptography

3. If the assets folder is missing, build it:

   python make_assets.py

4. Start the app:

   python app.py

Note: my folder path has spaces in it, so I use "python -m pip" instead of the
full pip path. That avoids the path error on Windows.


WHAT THE APP DOES
-----------------
When you start it, a boot screen runs first. It loads the engines, runs a self
test, and then opens the main window. After that you get an info box, then the
main window.

The main window has the common actions on the left and a console on the right
that prints the result of every action. The bar at the bottom opens the bigger
tools, including the steganography workspace.


WHAT WORKS FOR REAL
-------------------
Steganography (the graded core):
  Image: hide text, hide file, hide folder, extract text, extract file,
         show modified pixels, binary compare, compare images, capacity,
         recover cover, side by side view, run self test.
  Sound: hide text, hide file, read text, read file, in 16 bit WAV.

Crypto (AES through the cryptography library):
  Encrypt and decrypt text, files, and folders, with a password.
  A wrong password is rejected, not accepted in silence.

Combined:
  Encrypt then hide, and extract then decrypt. The message is encrypted with
  AES first, then hidden. Anyone who pulls the data out sees only ciphertext.

Utilities:
  Copy, paste, clear, open file, save text as file.
  Shred files and shred folder. It overwrites then deletes, with a confirm box.
  Generate a secure password. Test a password strength.
  Create a self decrypting message, which exports an HTML file.
  Change colours, theme, and font size.


THE DEMO SCREENS
----------------
Some menu items are marked (demo). These touch other apps or the operating
system and break across machines, so I left them as labelled demo screens
instead of faking them or doing harm. They are:
  Privacy browser shredding, Send Email, Crypto Explorer, System Monitor,
  Data Forensics, Unplug USB, Run On Startup, Minimize To Tray.
I marked them clearly so it is honest about what is real and what is not. The
graded steganography features are all real and tested.


SELF DECRYPTING MESSAGE
-----------------------
The exported HTML decrypts in the browser with the Web Crypto API. The Python
side encrypts with AES-GCM and PBKDF2-SHA256, and the browser side uses the
matching settings. I tested it once in my own browser: open the HTML, type the
password, and the message shows.


WHY PNG AND WAV, NOT JPG OR MP3
-------------------------------
LSB needs lossless storage. PNG, BMP, and WAV keep every bit. JPG and MP3
re-compress and throw the hidden bits away. So I save stego output as PNG or
WAV.


HOW THE LOGIC MATCHES THE SLIDES
--------------------------------
Text to binary: one byte per character, format(ord(c), '08b').
End marker: 1111111111111110, the 16 bit marker from the slides.
Hide: value = (value & 254) | bit, on each flattened pixel or audio sample.
Extract: read the low bit of each value, stop at the end marker.
Compare and recover: NumPy difference and a pixel printout, slides 33, 35, 36.


THE LOGO AND ICONS
------------------
I drew the logo and icons myself in make_assets.py, using simple shapes. They
are not copied from any other app. Edit that script to change the look.
