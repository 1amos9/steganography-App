QUICKCRYPTO STEGO SUITE
=======================

A steganography and crypto desktop app in the style of the QuickCrypto interface.
Course: Information Organization and System Security. Individual Work, 40 marks.
Graded core: LSB image steganography, following the Day 3 class slides.


FILES
-----
app.py            The interface. Run this.
stego_engine.py   Image LSB logic. The graded core.
audio_stego.py    Audio WAV LSB logic.
crypto_engine.py  AES crypto, shred, password tools, self decrypting export.
make_assets.py    Draws the logo and icons. Run once if the assets folder is missing.
assets/           Original logo and icon PNGs. Not copied from QuickCrypto.
sample_cover.png  A test image you can hide data in right away.


HOW TO RUN
----------
1. Open a terminal in this folder.
2. Install the libraries once:

   pip install customtkinter pillow numpy cryptography

3. If the assets folder is missing, build it:

   python make_assets.py

4. Start the app:

   python app.py


FULL MENU MAP (matches your screenshots)
----------------------------------------
File      Open Any File, Save Text As File, Print Text, Cancel, Exit
Edit      Copy, Paste, Clear
Encrypt   Encrypt Files, Encrypt Folder, Encrypt Text Window (Ctrl+E)
Decrypt   Decrypt Files, Decrypt Folder, Decrypt Text Window (Ctrl+D)
Shred     Shred Files, Shred Folder, Data Forensics
Hide      Hide Files, Hide Folder, Hide/Read in Image (Ctrl+H),
          Hide/Read Text and File in Sound (WAV)
Privacy   Browser and free space shredding (see Honest Stubs below)
Personalize  Text Font, Colors, Themes, Reset
Tools     Crypto Explorer, System Monitor, Password Safe, Send Email,
          Self Decrypting Message, Generate Password, Password Test, USB
Options   Change Pass Phrase, Crypto Options, Configure, Key File, toggles
Help      Help, Online Help, Support, Credits, About, Updates


WHAT WORKS FOR REAL
-------------------
Steganography (graded core):
  Image: hide text, hide file, hide folder, extract text, extract file,
         show modified pixels, binary compare, compare images, capacity, recover.
  Sound: hide text, hide file, read text, read file, in 16 bit WAV.

Crypto (AES through the cryptography library):
  Encrypt and Decrypt Text, Files, and Folders. Password based.
  Wrong password is rejected, not silently accepted.

Utilities:
  Copy, Paste, Clear, Open File, Save Text As File.
  Shred Files and Shred Folder. Overwrites then deletes, with confirmation.
  Generate Secure Password. Password Strength test.
  Create Self Decrypting Message (exports an HTML file).
  Personalize colors, theme, and font size.


HONEST STUBS (labeled, not faked)
---------------------------------
These touch other apps or the operating system and break across machines, so
each shows a clear on screen note instead of pretending or doing harm:
  Privacy browser shredding, Send Email, Crypto Explorer, System Monitor,
  Data Forensics, Unplug USB, Run On Startup, Minimize To Tray, Online items.
Tell your developer (or me) which of these you want turned real.


SELF DECRYPTING MESSAGE NOTE
----------------------------
The exported HTML decrypts in the browser using the Web Crypto API. The Python
side encrypts with AES-GCM and PBKDF2-SHA256, and the browser side uses the
matching settings. Test it once in your own browser: open the HTML, type the
password, and confirm your message appears. Report any issue and it gets fixed.


WHY PNG AND WAV, NOT JPG OR MP3
-------------------------------
LSB needs lossless storage. PNG, BMP, and WAV keep every bit. JPG and MP3
re-compress and destroy the hidden bits. Save stego output as PNG or WAV.


HOW THE LOGIC MATCHES THE SLIDES
--------------------------------
Text to binary: one byte per character, format(ord(c), '08b').
End marker: 1111111111111110, the 16 bit marker from the slides.
Hide: value = (value & 254) | bit, on each flattened pixel or audio sample.
Extract: read the low bit of each value, stop at the end marker.
Compare and recover: NumPy difference and pixel printout, slides 33, 35, 36.


ON THE LOGO AND ICONS
---------------------
The QuickCrypto company artwork is their property. The logo and icons in the
assets folder are original, drawn with simple shapes in make_assets.py. Edit
that script to change the look.


DEADLINE
--------
Slide 37 reads Saturday 13.06.2026 after class. Your brief said Sunday 14.06.
Confirm the exact date with your lecturer so you do not miss it.
