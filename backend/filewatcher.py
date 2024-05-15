
import os
import shutil
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Zip file handler imports
import zipfile

def main(filepath=None):
    """
    using subprocess.run, exec backend/main.py with the file path as arg[1]
    """
    subprocess.run(["python3", "backend/main.py", filepath])

class fileWatcher:

    def __init__(self, inputDirectory=None):
        self.observer = Observer()
        if inputDirectory:
            self.inputDirectory = inputDirectory
        else:
            print("Unable to watch input directory! Please check your configuration")
            os.exit(1)

    def watch(self):
        # main loop
        event_handler = Handler()
        self.observer.schedule(event_handler, self.inputDirectory, recursive=True)
        self.observer.start()
        try:
            while True:
                pass
        except Exception as e:
            print("Failed in main loop, error: ", e)
            self.observer.stop()
        self.observer.join()

class Handler(FileSystemEventHandler):
    """
    Create a class to handle file create events
    This uses the 'on_created' staticmethod in the watchdog package
    """
    @staticmethod
    def on_created(event):
        config_location = None
        file_path = str(event.src_path)
        if event.is_directory:
            if os.path.isdir(file_path):
                for root, dirs, files in os.walk(file_path):
                    if 'config.json' in files:
                            config_location = root
                    if config_location:
                        print("processing config file in dir path", config_location)
                        main(filePath=config_location)
            else:
                print(f"Unable to process files placed in {file_path}")
                exit(1)
        else:
            print("Checking to see if its a zip...", file_path, type(file_path))
            # check to see if the last element in the file_path string is 'zip' and go through tlat flow
            print(file_path.split('.')[-1])
            if file_path.split('.')[-1] == 'zip':
                print("its a zip... extracting")
                basepath = '/var/tmp/extracted/'
                with zipfile.ZipFile(file_path) as zip:
                    zip.extractall(basepath)
                    for root, dirs, files in os.walk(basepath):
                        if 'config.json' in files:
                            config_location = Path(root)
                            print("processing config file in extracted zip path")
                            main(filePath=config_location)
                            break
                    if config_location:
                        print("doing the thing...")
            else:
                # Dont try to process anything
                pass
        pass

    def backupFiles(file_path):
        original_path = os.path.basename(file_path)
        archive_path = Path('/var/tmp/archived')
        if not archive_path.exists():
            archive_path.mkdir()
        if not os.path.join(archive_path, original_path):
            print("Backing up to /var/tmp/archived/")
            shutil.move(file_path, str(archive_path / original_path))
        else:
            print("Already backed up...")

############################################################################
    # Start up Watcher loop
    ############################################################################
    watcher = fileWatcher(inputDirectory=inRootFolder)
    watcher.watch()