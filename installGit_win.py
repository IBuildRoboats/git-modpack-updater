import os
import subprocess
import urllib.request
import shutil
import sys

def download_git_installer(download_url, destination):
    print("Downloading Git installer...")
    urllib.request.urlretrieve(download_url, destination)
    print(f"Downloaded Git installer to {destination}")

def install_git(installer_path):
    print("Installing Git silently...")
    try:
        subprocess.run(
            [installer_path, "/VERYSILENT", "/NORESTART", "/NOCANCEL"],
            check=True
        )
        print("Git installation completed.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Git: {e}")
        sys.exit(1)

def is_git_installed():
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

def main():
    if os.name != "nt":
        print("This script is designed for Windows only.")
        return

    if is_git_installed():
        print("Git is already installed.")
        return

    git_installer_url = "https://github.com/git-for-windows/git/releases/download/v2.47.0.windows.2/Git-2.47.0.2-64-bit.exe"  # Update version as needed
    installer_path = os.path.join(os.getcwd(), "GitInstaller.exe")

    # Download the installer
    download_git_installer(git_installer_url, installer_path)

    # Run the installer
    install_git(installer_path)

    # Cleanup the installer file
    print("Cleaning up installer...")
    os.remove(installer_path)

    # Verify Git installation
    if is_git_installed():
        print("Git was installed successfully.")
    else:
        print("Git installation failed.")