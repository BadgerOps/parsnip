# Copyright 2024, Battelle Energy Alliance, LLC, ALL RIGHTS RESERVED

import os
import time
import argparse

import utils
import json_processing as processing
import graphing

import generation_utils
import config

# Graph Theory Imports
import networkx as nx

# File Watcher Imports
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Zip file handler imports
import zipfile

def _updateUtilValues(configuration):
    utils.PROTOCOL_NAME = configuration.protocol
    utils.USES_LAYER_2 = configuration.usesLayer2
    utils.customFieldTypes = configuration.customFieldTypes
    
def _parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputRootDirectory", type=str, help="Path to folder with '{0}' folder".format(utils.DEFAULT_SCOPE))
    parser.add_argument("outputRootDirectory", type=str, help="Root output directory")

    args = parser.parse_args()

    return (args.inputRootDirectory, args.outputRootDirectory)
    
def _generateData(filePath, configuration, entryPointScope, entryPointName, entryPointKey):
    print("The root folder is ", inRootFolder)
    print("The file path is: ", filePath)
    ############################################################################
    # Process the data files
    ############################################################################    
    objects, switches, bitfields, enums = processing.loadFiles(filePath, configuration.scopes)
               
    ############################################################################
    # Use some Graph Theory to our advantage
    ############################################################################                       
    generation_utils.createAndUseGraphInformation(configuration, objects, switches, bitfields, enums, entryPointScope, entryPointName, entryPointKey)
        
    ############################################################################
    # Work with the loaded data
    ############################################################################
    zeekTypes, zeekMainFileObject = processing.createZeekObjects(configuration.scopes, configuration.customFieldTypes, bitfields, objects, switches)
    
    # Determine import requirements
    # currentScope -> dependentScope[] -> ["enum"/"object"/"custom"] -> referenceType[]
    crossScopeItems = generation_utils.determineInterScopeDependencies(configuration, bitfields, objects, switches)
    
    return (zeekTypes, zeekMainFileObject, crossScopeItems, bitfields, enums, objects, switches)
    
def determineEntryPointInformation(configuration):
    entryPointParts = configuration.entryPoint.split(".")
    if 2 != len(entryPointParts):
        return (False, "", "", "")

    entryPointScope = entryPointParts[0]
    entryPointName = entryPointParts[1]
    entryPointKey = graphing.normalizedKey3(utils.normalizedScope(entryPointScope, "object"), "object", entryPointName)
    
    return (True, entryPointScope, entryPointName, entryPointKey)

def main(filePath=None):
    ############################################################################
    # Load the configuration file
    ############################################################################
    inRootFolder = filePath
    configPath = os.path.join(inRootFolder, "config.json")
    #configPath = os.path.join(filePath, "config.json")
    loadSuccessful, configuration = config.loadConfig(configPath)
    if not loadSuccessful:
        print(configPath + " is a required file")
        exit(1)
        
    _updateUtilValues(configuration)
    
    entryPointParsingSuccessful, entryPointScope, entryPointName, entryPointKey = determineEntryPointInformation(configuration)
    
    if not entryPointParsingSuccessful:
        print("EntryPoint must have scope and object name")
        exit(2)
    
    print(entryPointScope + " ---> " + entryPointName)

    ############################################################################
    # Load and work with data
    ############################################################################
    zeekTypes, zeekMainFileObject, crossScopeItems, bitfields, enums, objects, switches = _generateData(filePath, configuration, entryPointScope, entryPointName, entryPointKey)

    ############################################################################
    # Generate output
    ############################################################################
    generation_utils.writeParserFiles(configuration, outRootFolder,
                                      zeekTypes, zeekMainFileObject,
                                      crossScopeItems,
                                      bitfields, enums,
                                      objects, switches,
                                      entryPointScope, entryPointName)

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



if __name__ == "__main__":

    ############################################################################
    # Parse Command Line Arguments
    ############################################################################
    inRootFolder, outRootFolder = _parseArgs()
    print(f"Folders! check em: {inRootFolder}, {outRootFolder}")

    ############################################################################
    # Start up Watcher loop
    ############################################################################
    watcher = fileWatcher(inputDirectory=inRootFolder)
    watcher.watch()