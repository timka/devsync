import sublime
import sublime_plugin
import subprocess

DEBUG_MODE = False

def debug(*args, **kw):
    if DEBUG_MODE:
        return print(*args, **kw)

class DevSyncCommand(sublime_plugin.EventListener):
    def on_post_save(self, view):
        settings = sublime.load_settings('DevSync.sublime-settings')
        debug("settings: {}".format(settings))
        pathMaps = settings.get('pathMapping')
        globals()['DEBUG_MODE'] = settings.get('debugMode')


        debug("==== Starting DevSync Debugging Ouput ====")

        # Get the current file path and determine if it is in
        # the user's pathMapping array
        view = sublime.active_window().active_view()
        localPath = view.file_name() or ''
        debug('localPath: {}'.format(localPath))

        foundMap = None
        for pathMap in pathMaps:
            
            if (pathMap["source"] in localPath):
                debug('Found sync mapping.')
                foundMap = True
                # replace the src path with dest path
                destPath = localPath.replace(pathMap["source"], pathMap["destination"])

                # determine the path (without file name) of the destination
                lastFolderIndex = destPath.rfind("/")
                if (lastFolderIndex == -1):
                    lastFolderIndex = destPath.rfind("\\")
                destFolder = destPath[0:lastFolderIndex]

                osVariant = pathMap["destOS"]
                mkdir = " mkdir "
                if (osVariant == 'linux'):
                    mkdir = mkdir + "-p "
                    destPath = destPath.replace('\\', '/')

                if (pathMap["type"] == 'remote'):
                    hostString = pathMap["username"] + "@" + pathMap["serverAddress"]

                    if (debug):
                        print("Creating Folders: " + settings.get('sshBinary') + " " + hostString + " \"" + mkdir + destFolder + " && exit\"")

                    # attempt to create directories in case they do not exist already
                    command = settings.get('sshBinary') + " " + hostString + " \"" + mkdir + destFolder + " && exit\""
                    try:
                        subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
                    except subprocess.CalledProcessError as e:
                        sublime.error_message(str(e.output.decode("utf-8")))

                    # cygwin executables cannot use windows paths. if the cygwinPath variable is set use that instead
                    if ("cygwinSourcePath" in pathMap and pathMap["cygwinSourcePath"] != "null"):
                        localPath = localPath.replace(pathMap["source"], pathMap["cygwinSourcePath"])
                        localPath = localPath.replace('\\', '/')

                    # Sync file across
                    command = settings.get('scpBinary') + " -Cr " + localPath + " " + hostString + ":" + destPath
                    if (debug):
                        print("Executing scp command: " + command)

                    try:
                        subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
                    except subprocess.CalledProcessError as e:
                        sublime.error_message(str(e.output.decode("utf-8")))

                elif (pathMap["type"] == 'local'):
                    # attempt to create directories in case they do not exist already
                    try:
                        subprocess.check_output(mkdir + destFolder, stderr=subprocess.STDOUT, shell=True)
                    except subprocess.CalledProcessError as e:
                        pass

                    copyCmd = 'cp'
                    if (osVariant == 'windows'):
                        copyCmd = 'copy';


                    debug("Executing copy command: " + copyCmd + " " + localPath + " " + destPath)

                    # copy the file
                    try:
                        subprocess.check_output(copyCmd + " " + localPath + " " + destPath, stderr=subprocess.STDOUT, shell=True)
                    except subprocess.CalledProcessError as e:
                        sublime.error_message(str(e.output.decode("utf-8")))
        if (foundMap is None):
            debug("No source configured for this file.")

        debug("==== Done DevSync Debugging Ouput ====")


class devSyncCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings('DevSync.sublime-settings')
        pathMaps = settings.get('pathMapping')
        globals()['DEBUG_MODE'] = settings.get('debugMode')


        debug("==== Starting DevSync Debugging Ouput ====")

        # Get the current file path and determine if it is in
        # the user's pathMapping array
        view = sublime.active_window().active_view()
        localPath = view.file_name() or ''
        debug('localPath: {}'.format(localPath))

        foundMap = None
        for pathMap in pathMaps:
            if (pathMap["source"] in localPath):
                source = pathMap["source"]
                debug('Found sync mapping.')
                foundMap = True

                # get the name of the project / the base folder
                index = source.rfind("\\")
                if (index == -1):
                    index = source.rfind("/")

                folderName = source[index:len(source)]
                folderName = folderName.strip("\\")
                folderName = folderName.strip("/")

                # execute the bash script (if necessary)
                if ("bashScript" in pathMap and pathMap["bashScript"] != "null"):
                    command = settings.get('bashBinary') + " \"" + pathMap["bashScript"] + " " + folderName + "\""
                    # If running under a linux environment we cannot have the foldername inside the quotes
                    if (settings.get('bashBinary') == 'sh'):
                        command = settings.get('bashBinary') + " \"" + pathMap["bashScript"] + "\"" + " " + folderName


                    debug("Executing Bash Script: " + command)
                    try:
                        subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
                    except subprocess.CalledProcessError as e:
                        sublime.error_message(str(e.output.decode("utf-8")))

                if (pathMap["type"] == 'remote'):
                    hostString = pathMap["username"] + "@" + pathMap["serverAddress"]

                    source = pathMap["source"]

                    # cygwin executables cannot use windows paths. if the cygwinPath variable is set use that instead
                    if ("cygwinSourcePath" in pathMap and pathMap["cygwinSourcePath"] != "null"):
                        source = pathMap["cygwinSourcePath"]

                    exclude = "";
                    if (settings.get('rsyncExcludes')):
                        exclude = " --exclude-from=" + settings.get('rsyncExcludes');
                    
                    command = settings.get('rsyncBinary')
                    command += exclude
                    command += " -avz -e "
                    command += settings.get('sshBinary')
                    command += " " + source + "/. "
                    command += hostString + ":"
                    command += pathMap["destination"]

                    debug("Executing Rsync command: " + command)

                    try:
                        subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
                    except subprocess.CalledProcessError as e:
                        sublime.error_message(str(e.output.decode("utf-8")))

                elif (pathMap["type"] == 'local'):
                    source = pathMap["source"]

                    # cygwin executables cannot use windows paths. if the cygwinPath variable is set use that instead
                    if ("cygwinSourcePath" in pathMap and pathMap["cygwinSourcePath"] != "null"):
                        source = pathMap["cygwinSourcePath"]

                    copyCmd = 'cp -rfT'
                    if (pathMap["destOS"] == 'windows'):
                        copyCmd = 'xcopy /E /Y';

                    # copy over the project directory and files. Delete the original directory first.
                    try:
                        debug("Executing copy command: " + copyCmd + " " + source + " " + pathMap["destination"])

                        subprocess.check_output(copyCmd + " " + source + " " + pathMap["destination"], stderr=subprocess.STDOUT, shell=True)
                    except subprocess.CalledProcessError as e:
                        sublime.error_message(str(e.output.decode("utf-8")))

        if (foundMap is None):
            debug("No source configured for this file.")

        debug("==== Done DevSync Debugging Ouput ====")
