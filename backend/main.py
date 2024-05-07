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
    
def _generateData(inRootFolder, configuration, entryPointScope, entryPointName, entryPointKey):
    ############################################################################
    # Process the data files
    ############################################################################    
    objects, switches, bitfields, enums = processing.loadFiles(inRootFolder, configuration.scopes)
               
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
    configPath = os.path.join(inRootFolder, utils.DEFAULT_SCOPE, "config.json")
    print(configPath)
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
    zeekTypes, zeekMainFileObject, crossScopeItems, bitfields, enums, objects, switches = _generateData(inRootFolder, configuration, entryPointScope, entryPointName, entryPointKey)

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

    def app(self):
        # main loop
        event_handler = Handler()
        self.observer.schedule(event_handler, self.inputDirectory, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
                print("Main loop, loopin...")
        except Exception as e:
            print("Failed in main loop, error: ", e)
            self.observer.stop()
        self.observer.join()

class Handler(FileSystemEventHandler):

    @staticmethod
    def on_any_event(event):
        if event.event_type == 'created':
            print(f"Event is: {event}")
            print(type(event.src_path))
            print(event.src_path)
            if zipfile.is_zipfile(os.path.join(event.src_path)):
                print("zippy zoo")
            elif os.path.isdir(os.path.join(event.src_path)):
                print("its a directory", os.path.join(event.src_path))
                print("passing along to main func")
                print(os.path.isfile(os.path.join(event.src_path, 'config.json')))
                main(filePath=event.src_path)
            else:
                print("I'm not sure... ", event)

            if event.is_directory:
                print("Directory detected!")
                print(type(event.src_path))
        else:
            print(event.event_type)
        #     main(filePath=event.src_path)

        # elif event.event_type == 'created':
        #     # Take any action here when a file is first created.
        #     print(f"Received created event - %s." % event.src_path)

        # elif event.event_type == 'modified':
        #     # Taken any action here when a file is modified.
        #     print(f"Received modified event - %s." % event.src_path)



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
    watcher.app()