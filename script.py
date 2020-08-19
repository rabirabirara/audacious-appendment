#! python3

import errno
import os, sys
import argparse
import time
import threading
from enum import Enum

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
        write_thread.start()

        # The connection should be made nearly right away (allow some time).
        # If not made, then exit.
        time.sleep(0.1)
        if not self.write_handle:
            sys.exit("The write handle could not be opened!")

    def writer_handle(self):
        """Opens handle for writing to Audacity."""
        self.write_handle = open(WRITE_NAME, "w")

    def reader_thread(self):
        """Start a thread that reads responses."""
        read_thread = threading.Thread(target=self.reader_handle)
        read_thread.start()

    def reader_handle(self):
        """Opens handle for reading from Audacity.
        Reads responses line by line."""
        read_handle = open(READ_NAME, "r")
        message = ""
        handle_alive = True
        while handle_alive:
            line = read_handle.readline()
            while handle_alive and line != "\n":
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
        while not AudacityInstance.reply_ready.isSet():
            # Block thread until reply is received
            time.sleep(0.1)
        return self.reply

    # TODO: Make all this async, so we can just await the damn thing.
    def do_command(self, command):
        """Perform a single command and print the response."""
        self.write(command)
        reply = self.read()
        print(reply)
        time.sleep(0.5)


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


def initialize_audacity():
    print("Waiting 3 seconds for Audacity to initialize:")
    for i in range(1, 4):
        time.sleep(1.0)
        print(f"Waiting: {i}")
    print("Finished waiting.  Begin command execution.")


def connect():
    if os.path.exists(WRITE_NAME) and os.path.exists(READ_NAME):
        pass
    else:
        start_audacity()

    print("Successfully located Audacity instance.")

    time.sleep(0.5)
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


# Possibility: play 2 seconds, stop, select lef; etc.
def one_sec_back():
    return "CursorShortJumpLeft"

def one_sec_forward():
    return "CursorShortJumpLeft"

def start_secs(secs):
    return f"SelectTime: Start=0 End={secs} RelativeTo=ProjectStart"

def end_secs(secs):
    return f"SelectTime: Start=0 End={secs} RelativeTo=ProjectEnd"

def enable_cursor():
    return "SelAllTracks"

# Needs selection to work.
def start_silence():
    return "NyquistPrompt: Command=\"(defun insertstart (sig) (sum (s-rest 2) (at 1 (cue sig)))) (multichan-expand #'insertstart s)\""


# Needs selection to work.
def end_silence():
    # command = "(defun insertend (sig) (sum (s-rest 2) (at 0 (cue sig)))) (multichan-expand #'insertend s)"
    return "NyquistPrompt: Command=\"(defun insertstart (sig) (sum (s-rest 2) (at 0 ( cue sig)))) (multichan-expand #'insertstart s)\""


def import2(filename):
    return f"Import2: Filename={filename}"


def select_all():
    return "SelectAll"


def select_none():
    return "SelectNone"


# TruncateSilence Independently is actually broken and won't truncate.
def truncate():
    return "TruncateSilence: Threshold=-59 Minimum=0.001 Truncate=0 Independent=True"


def align_ends():
    return "Align_EndToEnd"


def mix_render():
    return "MixAndRender"


def normalize():
    """Amplifies audio to a peak of 0.0db.  Amplify is not available.
    Normalize is a substitute command that achieves the same effect."""
    # You can invert an amplified and normalized clip and hear silence.
    return "Normalize: PeakLevel=0 RemoveDcOffset=False"


def join():
    return "Join"

# ! Export2 is problematic.  It pulls from the last used preferences 
# ! for options like bitrate, quality, etc.
# ! Make sure these are correctly set manually.
def export2(filename):
    return f"Export2: Filename={filename}"

class Silence(Enum):
    none = "none"
    independent = "ind"
    combined = "comb"
    
    def __str__(self):
        return self.value

# TODO: Do valid checking on Silence + int (secs to add).
# def valid_silence(choice):
#     try:
#         choice.startswith(Silence, int)

def valid_filename(filename):
    name, extension = os.path.splitext(filename)
    if extension == '':
        raise argparse.ArgumentTypeError("Output must include an extension!")
    else:
        return filename


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("FILES", nargs="+", type=valid_filename)
    parser.add_argument("-o", "--output", default="audio-join-script-result", help="Determines the output file's name.", metavar="FILENAME", type=valid_filename)
    parser.add_argument("-t", "--truncate", default=False, action='store_true', help="Choose to truncate silence or not.  Truncating is useful for joining classical movements that segue attaca into one another.")
    parser.add_argument("-s", "--silence", type=Silence, choices=list(Silence), help="Choose to add no silence, to add silence to all tracks individually, or to add silence to the combined final track.")
    # ! ArgParse doesn't allow for mutually inclusive arguments.
    # ! Python's stdlib is so crap lol.  Even Rust's clap can do this,
    # ! and it's much newer (when we consider optparse too).
    # This means I can't add a count argument that is required when I
    # have an add silence argument. If I could, I could make the Silence enum
    # more like an Option, and have default = None or specified = one of the 
    # two types in the enum.  Then I could require a number of secs to add.
    # TODO: Add conditional arguments.

    args = parser.parse_args()
    files = args.FILES
    output_name = args.output
    do_truncate = args.truncate
    some_silence = args.silence
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
    initialize_audacity()

    # ! Audacity can only handle a maximum of 16 tracks.
    # ! But there are plenty of situations in which we want to mix more than that!
    # ! We need a way to mix tracks bits at a time. Typically,
    # ! this will come up before the global "___all()" operations.

    def do(command):
        instance.do_command(command)

    def align_all():
        do(select_all())
        do(align_ends())

    def truncate_all():
        do(select_all())
        do(truncate())

    def mix_render_all():
        do(select_all())
        do(mix_render())

    def normalize_all():
        do(select_all())
        do(normalize())

    # def silence_independently():
       # do() 
    
    do(import2(lof_filepath))
    do(enable_cursor())
    
    align_all() 
    if do_truncate:
        truncate_all() 
    # if silence_type.value == "ind":
    #     silence_independently()
    align_all()
    mix_render_all()
    normalize_all()

    # ! Why does generating any nosie not allow you to specify a duration?
    # ! Why does generating noise generate over the whole file?
    # * These questions are answered on the forums.  In short,
    # * there is no actual macro for inserting silence.
    do(select_none())
    do(enable_cursor())
    do(start_secs(2))
    do(start_silence())
    do(end_secs(2))
    do(end_silence())
    do(select_all())
    do(join())

    do(export2(output_name)) 


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        exit()
    except FileNotFoundError:
        print(
            "One of your input files was not found! It may have been an erroneous filename, or an improper path."
        )

