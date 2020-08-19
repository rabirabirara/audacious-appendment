#! python3

import errno
import os, sys
import argparse
import time
import threading

"""
Sorting of names works with numbers, so Python can sort the filenames passed
into it; no need for work.  Typing in the filenames is the harder part.
"""

# Open Audacity with Python.D:\Program Files (x86)\Audacity
# Open only if an instance isn't already running.  Do you need to put a delay to
# have the script wait for it to run? Have the script try a few times while
# waiting for Audacity to open.  If too much time passes, close and tell the
# user to try again when Audacity is open.
# Use os.startfile.

# Open the .lof with Import2 from Extra Scriptables II.
# Same as Open... in function, so don't worry.
#
# Select: all.
# Truncating silence for ends of tracks that segue: -58db, 0.01 seconds.

# Or, truncate -56 db, 0.006 seconds.  Air sounds at around -54db, but the
# duration should help.
# -56db and 0.005 seems about right.  Parts of the piece's silences were
# actually cut - try a violin cadenza, for example.
# Actually... -59 still cuts out the same silences in the cadenza, for some
# reason... this sucks.  -59 is the way to go to get a smooth experience.
# Whatever; sorry flamboyant musicians who like putting silences.
# Truncate these tracks independently.  Truncate to 0.

# Select: all.
# Tracks: Align tracks: end-to-end.
# Select: all.
# Tracks: Mix: Mix and render.
# Select: all.
# Effect: Amplify to peak of 0.0db.

# def ToStart: Extra: Scriptables II: Select: Start=0, End=0, RelativeTo=Project
# ToStart
# Generate: Noise. White, 2 seconds, Amplitude=0.0
# def ToEnd: Extra.... Select: Start=1,End=1, RelativeTo=Project
# ToEnd
# Generate: Noise. White, 2 seconds, Amplitude=0.0

# Extra: Scriptables II: Export2
# Filename=argument specified at program start


# btw: always use select at zero crossings in the future.
# Truncate silence with -54db, 0.002 seconds, etc... anything not erased
# should be selected at zero crossings and removed manually.  This gets rid
# of clicks (gaps between tracks) very easily.

# Options: -o for output, -s for sort filenames if possible
# Make a cleaning script afterwards, to delete .lof files


if sys.platform == "win32":
    print("Windows OS detected.")
    WRITE_NAME = "\\\\.\\pipe\\ToSrvPipe"
    READ_NAME = "\\\\.\\pipe\\FromSrvPipe"
    EOL = "\r\n\0"
else:
    print("Unix-like OS detected.")
    WRITE_NAME = "/tmp/audacity_script_pipe.to." + str(os.getuid())
    READ_NAME = "/tmp/audacity_script_pipe.from." + str(os.getuid())
    EOL = "\n"


class AudacityInstance:

    reader_pipe_broken = threading.Event()
    reply_ready = threading.Event()

    # In Python every object has a __dict__ attribute, which contains their symbol table.
    # It's because everything in Python is an object.

    def __init__(self):
        # Define shared mutable state among read and write threads.
        self.write_handle = None
        self.reply = ""
        if not self.write_handle:
            self.writer_thread()
        self.reader_thread()
        # self.write_handle = write_handle
        # self.read_handle = read_handle
        # self.eol = eol
        # self._write_pipe = None
        # self._reply = ""
        # if not self._write_pipe:
        #     self._write_thread_start()
        # self._read_thread_start()

    def writer_thread(self):
        """Start a thread that writes commands."""
        write_thread = threading.Thread(target=self.writer_handle)
        write_thread.daemon = True
        write_thread.start()

        # The connection should be made nearly right away (allow some time).
        # If not made, then exit.
        time.sleep(0.1)
        if not self.write_handle:
            sys.exit("The write handle could not be opened!")

    def writer_handle(self):
        """Opens handle for writing to Audacity."""
        self.write_handle = open(WRITE_NAME, 'w')

    def reader_thread(self):
        """Start a thread that reads responses."""
        read_thread = threading.Thread(target=self.reader_handle)
        read_thread.daemon = True
        read_thread.start()

    def reader_handle(self):
        """Opens handle for reading from Audacity.
        Reads responses line by line."""
        read_handle = open(READ_NAME, 'r')
        message = ""
        handle_alive = True
        while handle_alive:
            line = read_handle.readline()
            while handle_alive and line != '\n':
                message += line
                line = read_handle.readline()
                if line == "":
                    AudacityInstance.reader_pipe_broken.set()
                    handle_alive = False
            self.reply = message
            AudacityInstance.reply_ready.set()
            # We reset the message after each read completes.
            message = ""
        read_handle.close()

    def write(self, command):
        """Send a single command to Audacity."""
        print("Sending command:", command)
        self.write_handle.write(command + EOL)
        # Check that the read handle is still alive.
        if AudacityInstance.reader_pipe_broken.isSet():
            sys.exit("The handle for reading Audacity's responses broke down.")
        try:
            self.write_handle.flush()
            self.reply = ""
            AudacityInstance.reply_ready.clear()
        except IOError as err:
            if err.errno == errno.EPIPE:
                sys.exit("The handle for writing commands to Audacity broke down.")
            else:
                raise

    def read(self):
        """Receive a response from Audacity."""
        # Remember, reader_handle is responsible for setting self.reply 
        # and setting the flag for them to be ready.
        # write() is responsible for clearing the last reply.
        if not AudacityInstance.reply_ready.isSet():
            return ""
        return self.reply

    def do(self, command):
        """Perform a single command and print the response."""
        self.write(command)
        # Allow time for a reply
        time.sleep(0.1)
        self.read()


def start_audacity():
    os.startfile("D:/Program Files (x86)/Audacity/audacity.exe")
    print("Waiting 15 seconds for Audacity to start.")
    start = time.time()
    i = 0
    while not os.path.exists(WRITE_NAME) or not os.path.exists(READ_NAME):
        time.sleep(1.0)
        diff = time.time() - start
        i += 1
        print(f"Waiting for Audacity... {i}")
        if diff > 15.0:
            print("Script aborted. Audacity took too long to open!")
            sys.exit()


def wait_for_startup():
    print("Waiting 5 seconds for Audacity to initialize:")
    for i in range(1, 6):
        time.sleep(1.0)
        print(f"Waiting: {i}")
    print("Finished waiting.  Begin command execution.")


def connect():
    if os.path.exists(WRITE_NAME) and os.path.exists(READ_NAME):
        pass
    else:
        start_audacity()

    print("Successfully located Audacity instance.")

    instance = AudacityInstance()
    return instance


def create_lof_string(filepath_list):
    contents = []
    for path in filepath_list:
        contents.append('file "' + path + '"')
    return "\n".join(contents)


def create_lof_file():
    return open("test.lof", "w+")


def to_start():
    return "CursProjectStart"


def to_end():
    return "CursProjectEnd"


def import2(filename):
    return f"Import2: Filename={filename}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("FILES", nargs="+", type=str)
    parser.add_argument("-o", default="audio-join-script-result")

    args = parser.parse_args()
    files = args.FILES
    output_name = args.o
    paths = []

    # We make the user responsible for specifying file extensions, because of
    # the possibility of two file extensions on a file.
    for file in files:
        paths.append(os.path.abspath(file))
        print(os.path.abspath(file))

    lof_string = create_lof_string(paths)
    with create_lof_file() as lof_file:
        lof_filepath = os.path.abspath(lof_file.name)
        lof_file.write(lof_string)
    # ! Don't forget to close the file handle, then delete it. Also, delete file.name.

    instance = connect()
    wait_for_startup()
    instance.do(import2(lof_filepath))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        exit()
    except FileNotFoundError:
        print(
            "One of your input files was not found! It may have been an erroneous filename, or an improper path."
        )

