import ctypes
import random
import stat
import string
import subprocess
import sys
import os
import git
import shutil
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QFileDialog, \
    QHBoxLayout, QMessageBox
import shutil



# Build with pyinstaller --onefile --icon=app.ico Updater.py

class GitCloneThread(QThread):
    """Thread to handle the Git clone operation so it doesn't block the UI."""
    success_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, git_url, minecraft_folder):
        super().__init__()
        self.git_url = git_url
        self.minecraft_folder = minecraft_folder

    def run(self):
        """Run the Git clone operation in the background."""
        try:
            mods_folder = os.path.join(self.minecraft_folder, 'mods')
            os.makedirs(mods_folder)

            print(f"Cloning repository from {self.git_url} to {mods_folder}")
            git.Repo.clone_from(self.git_url, mods_folder)

            self.success_signal.emit(f"Repository cloned successfully to {self.minecraft_folder}")
        except git.exc.GitCommandError as e:
            self.error_signal.emit(f"Error cloning repository: {e}")
        except Exception as e:
            self.error_signal.emit(f"Unexpected error: {e}")


class MinecraftModApp(QWidget):
    def __init__(self):
        super().__init__()
        self.mods_path = None
        self.git_url = None
        self.config_file = os.path.expanduser('./config.txt')  # Path to config file

        # Ensure the config file exists
        self.ensure_config_file_exists()

        self.init_ui()

    def ensure_config_file_exists(self):
        # Check if the config file exists
        if not os.path.exists(self.config_file):
            # If it doesn't exist, create it and optionally initialize it
            os.makedirs(os.path.dirname(self.config_file),
                        exist_ok=True)  # Create the .minecraft directory if it doesn't exist
            with open(self.config_file, 'w') as f:
                f.write("")  # You can initialize the file with an empty string or some default content
            print(f"Configuration file created at: {self.config_file}")

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    self.mods_path = lines[0].strip()
                    self.git_url = lines[1].strip()
                    self.init_main_screen()
                else:
                    self.initSetupScreen()

    def init_ui(self):
        self.setWindowTitle("Mod Updater")
        self.setGeometry(300, 300, 400, 200)

        self.layout = QVBoxLayout()

        self.setLayout(self.layout)

    def initSetupScreen(self):
        self.path_label = QLabel("Select .minecraft Folder:")
        self.layout.addWidget(self.path_label)

        self.path_input = QLineEdit(self)
        self.layout.addWidget(self.path_input)

        self.select_button = QPushButton("Select .minecraft Folder", self)
        self.select_button.clicked.connect(self.select_minecraft_folder)
        self.layout.addWidget(self.select_button)

        self.git_label = QLabel("Enter Git Repository URL:")
        self.layout.addWidget(self.git_label)

        self.git_input = QLineEdit(self)
        self.layout.addWidget(self.git_input)

        self.continue_button = QPushButton("Continue", self)
        self.continue_button.clicked.connect(self.continue_setup)
        self.layout.addWidget(self.continue_button)

        self.reset_button = QPushButton("Reset", self)
        self.reset_button.clicked.connect(self.reset_setup)
        self.layout.addWidget(self.reset_button)

    def select_minecraft_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Minecraft Folder", os.path.expanduser('~/AppData/Roaming/.minecraft'))
        if folder:
            self.path_input.setText(folder)

    def clear_layout(self):
        """Clear all widgets from the layout."""
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def remove_read_only_attribute(self, directory):
        # Loop through all the files in the given directory (including subdirectories)
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)

                # Get the current file permissions
                file_permissions = os.stat(file_path).st_mode

                # Remove the read-only (write-protected) attribute by adding write permissions
                os.chmod(file_path, file_permissions | stat.S_IWUSR)
                print(f"Updated permissions for: {file_path}")

    def confirm_delete_folder(self):
        """Show a confirmation dialog to delete the existing mods folder."""
        reply = QMessageBox.question(self, 'Delete Folder',
                                     "Are you sure you want to delete the existing mods folder?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_mods_folder()
        else:
            print("The existing mods folder will not be deleted.")
            self.select_minecraft_folder()

    def delete_mods_folder(self):
        """Delete the mods folder if the user confirms."""
        mods_folder = os.path.join(self.path_input.text(), "mods")

        try:
            # Attempt to delete the directory and its contents
            print(f"Deleting {mods_folder}")
            try:
                self.remove_read_only_attribute(os.path.expanduser("~/AppData/Roaming/.minecraft/mods/.git/objects/pack"))
            except:
                pass
            shutil.rmtree(mods_folder)
            print("Deleted successfully")
            self.clone_repository()
        except PermissionError as e:
            self.show_error(
                f"Permission error while deleting {mods_folder}. Please ensure Minecraft is closed and try again.")
        except Exception as e:
            self.show_error(f"Unexpected error while deleting folder: {e}")

    def continue_setup(self):
        """Set up the Minecraft mod by cloning the repository."""
        minecraft_folder = self.path_input.text()
        git_url = self.git_input.text()

        if minecraft_folder and git_url:
            self.mods_path = minecraft_folder
            self.git_url = git_url

            # Check if the mods folder exists, ask the user if they want to delete it
            mods_folder = os.path.join(minecraft_folder, 'mods')
            if os.path.exists(mods_folder):
                self.confirm_delete_folder()  # Ask the user for confirmation before deletion
            else:
                # Proceed with cloning if the mods folder doesn't exist
                self.clone_repository()
        else:
            print("Both fields are required.")
            self.show_error("Please provide both the Minecraft path and Git URL.")

    def clone_repository(self):
        """Start the cloning process."""
        self.clone_thread = GitCloneThread(self.git_url, self.mods_path)
        self.clone_thread.success_signal.connect(self.clone_success)
        self.clone_thread.error_signal.connect(self.clone_error)

        self.clone_thread.start()  # Start the cloning in the background

    def clone_success(self, message):
        print(message)
        self.show_message("Success", message)
        self.save_config()  # Save the config after a successful clone
        self.init_main_screen()

    def clone_error(self, message):
        print(message)
        self.show_error(message)

    def save_config(self):
        with open(self.config_file, 'w') as f:
            f.write(f"{self.mods_path}\n{self.git_url}")

    def init_main_screen(self):
        """Initialize the main screen after the cloning operation."""
        self.clear_layout()

        self.update_button = QPushButton("Update Mods", self)
        self.update_button.clicked.connect(self.update_mods)
        self.layout.addWidget(self.update_button)

        self.reset_button = QPushButton("Reset", self)
        self.reset_button.clicked.connect(self.reset_setup)
        self.layout.addWidget(self.reset_button)

        self.setLayout(self.layout)

    def update_mods(self):
        """Update the mods by pulling the latest changes from the Git repository."""
        if self.mods_path and self.git_url:
            mods_folder = os.path.join(self.mods_path, 'mods')
            try:
                repo = git.Repo(mods_folder)
                repo.git.checkout('--', '.')
                repo.remotes.origin.pull()
                print("Repository updated successfully.")
            except git.exc.GitCommandError as e:
                print(f"Error updating the repository: {e}")

    def reset_setup(self):
        """Reset the setup and return to the initial screen."""
        self.mods_path = None
        self.git_url = None
        self.clear_layout()
        self.initSetupScreen()

    def show_error(self, message):
        """Show an error message to the user."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec()

    def show_message(self, title, message):
        """Show a message to the user."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(message)
        msg.setWindowTitle(title)
        msg.exec()

def main():
    app = QApplication(sys.argv)
    window = MinecraftModApp()

    # Load saved configuration if exists
    window.load_config()

    window.show()
    sys.exit(app.exec())

