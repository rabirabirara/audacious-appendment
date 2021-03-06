#! python3

import errno
import os, sys
from pathlib import Path, PurePath
import argparse
import time
import threading
from enum import Enum

# Project files:
import envoptions

"""
Sorting of names works with numbers, so Python can sort the filenames passed
into it; no need for work.  Typing in the filenames is the harder part.
"""

# TODO: Split this script into multiple files.

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
# * No, this should be a none problem once incremental appendment is implemented.  Each track should have their silence cut on the ends individually
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

# This code is from the Audacity wiki's "pipeclient.py".
class AudacityInstance:

    reader_pipe_broken = threading.Event()
    reply_ready = threading.Event()

    def __init__(self, config):
        self.write_handle = None
        self.reply = ""
        self.write_path = config.write_path
        self.read_path = config.read_path
        self.eol = config.eol
        # For good measure.  Not sure why this code is here, though - there's only one instance anyway.
        if not self.write_handle:
            self.writer_thread()
        self.reader_thread()

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
        self.write_handle = open(self.write_path, "w")

    def reader_thread(self):
        """Start a thread that reads responses."""
        read_thread = threading.Thread(target=self.reader_handle)
        read_thread.start()

    def reader_handle(self):
        """Opens handle for reading from Audacity.
        Reads responses line by line."""
        read_handle = open(self.read_path, "r")
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
        self.write_handle.write(command + self.eol)
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


def start_audacity(config):
    os.startfile(config.audacity_loc)
    print("Waiting 15 seconds for Audacity to start.")
    start = time.time()
    i = 0
    while not Path.exists(config.write_path) or not Path.exists(config.read_path):
        time.sleep(1.0)
        diff = time.time() - start
        i += 1
        print(f"Waiting for Audacity... {i}")
        if diff > 15.0:
            print("Script aborted. Audacity took too long to open!")
            sys.exit()


# TODO: Add unix compatibility.
def end_audacity():
    print("Script successful. Closing Audacity...")
    time.sleep(2.0)
    os.system("taskkill /f /im audacity.exe /t")


def initialize_audacity():
    print("Waiting 3 seconds for Audacity to initialize:")
    for i in range(1, 4):
        time.sleep(1.0)
        print(f"Waiting: {i}")
    print("Finished waiting.  Begin command execution.")


def connect(config):
    if Path.exists(config.write_path) and Path.exists(config.read_path):
        pass
    else:
        start_audacity(config.audacity_loc)

    print("Successfully located Audacity instance.")
    time.sleep(1.0)
    instance = AudacityInstance(config)
    return instance


def create_lof_string(filepath_list):
    contents = []
    for path in filepath_list:
        contents.append('file "' + str(path) + '"')
    return "\n".join(contents)


def create_lof_file():
    return open("temp.lof", "w+")


def verify_given_lof(filepath):
    with open(filepath, "r") as given_lof:
        content = given_lof.readlines()
    content = [x.strip() for x in content]
    is_empty = lambda s: s == ""
    filter(is_empty, content)
    if len(content) < 2:
        return False
    content = [line.lstrip('file "') for line in content]
    content = [line.rstrip('"') for line in content]
    for line in content:
        path = Path(line)
        if not path.exists():
            return False
    return True


def remove_lof_file(path):
    Path.unlink(path)


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
    return 'NyquistPrompt: Command="(defun insertstart (sig) (sum (s-rest 2) (at 1 (cue sig)))) (multichan-expand #\'insertstart s)"'


# Needs selection to work.
def end_silence():
    return 'NyquistPrompt: Command="(defun insertstart (sig) (sum (s-rest 2) (at 0 ( cue sig)))) (multichan-expand #\'insertstart s)"'


def import2(filename):
    return f'Import2: Filename="{filename}"'


def select_all():
    return "SelectAll"


def select_none():
    return "SelectNone"


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
    if not filename.endswith(".mp3"):
        print("Adding .mp3 extension to your output.")
        filename += ".mp3"
    return f'Export2: Filename="{filename}" NumChannels=2'


class Effect(Enum):
    independent = "i"
    combined = "c"

    def __str__(self):
        return self.value


# TODO: Do valid checking on Silence + int (secs to add).
def valid_silence(choice):
    # A valid choice should be EFfect int.
    lst = choice.split()
    if lst.len() != 2:
        raise argparse.ArgumentTypeError("Must pass in two arguments to --silence!")
    else:
        if isinstance(lst[0], Effect):
            try:
                count = int(lst[1])
                return (lst[0].value, count)
                # TODO* Of course, the next step is to somehow enable varied silence adding for each track... oh boy.
            except ValueError:
                raise ValueError(
                    "Please give a decimal integer for the number of seconds of silence you want to add!"
                )
        else:
            raise argparse.ArgumentTypeError(
                "The first argument to --silence must be one of the options specified.  See --help for details."
            )


def valid_amplify(choice):
    # A valid amplify should be Effect
    if isinstance(choice, Effect):
        return choice
    else:
        raise argparse.ArgumentTypeError(
            "The argument to amplify must be one of the options specified.  See --help for details."
        )


def valid_filename(filename):
    if ext := PurePath(filename).suffix == "":
        raise argparse.ArgumentTypeError("File arguments must include an extension!")
    else:
        return filename


def main():
    parser = argparse.ArgumentParser()
    regular_or_config = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument("FILES", nargs='*', type=valid_filename)
    regular_or_config.add_argument(
        "-o",
        "--output",
        help="Determines the output file's name.",
        metavar="FILENAME.ext",
        type=valid_filename,
    )
    parser.add_argument(
        "-a",
        "--amplify",
        type=valid_amplify,
        action="store",
        help="Amplifies the resulting file to have a peak of 0.0 db.",
    )
    parser.add_argument(
        "-t",
        "--truncate",
        action="store_true",
        help="Choose to truncate silence or not.  Truncating is useful for joining classical movements that segue attaca into one another.",
    )
    # ? Unfortunately, there's no easy way to use choices=list(Silence) and nargs=2 at the same time, with the second
    # ? having a range of i16. Argparse just isn't that smart.
    parser.add_argument(
        "-s",
        "--silence",
        # A valid Silence has 2 arguments - one from the enum ind|comb, one for the number of secs.
        type=valid_silence,
        action="store",
        help="Choose either to add no silence, to add silence to all tracks individually, or to add silence to the combined final track.",
    )
    # TODO: Validate this as a path to go before a basename. Can do so in main, given output filename as tail and argument as head; put together and check if valid abspath.
    parser.add_argument(
        "-p",
        "--path",
        help="Specify a path for your file either here or in output.",
        type=str,
    )
    parser.add_argument(
        "-c",
        "--classical",
        action="store_true",
        help="If the arguments are movements of a classical piece, you can choose to sort the input.",
    )
    regular_or_config.add_argument(
        "--envoptions",
        action="store_true",
        help="Set options such as where to store your music and where your Audacity instance is located."
    )


    # This means I can't add a count argument that is required when I
    # have an add silence argument. If I could, I could make the Silence enum
    # more like an Option, and have default = None or specified = one of the
    # two types in the enum.  Then I could require a number of secs to add.
    # TODO: Add conditional arguments, to work with silence and adding a silence secs count.
    # TODO: Add "individually" option, which will apply an effect to each track individually.  May require sequential file opening.  Useful for amplifying some movements differently from others.
    # Use groups?

    args = parser.parse_args()
    
    if args.envoptions:
        envoptions.set_options()
        return
    
    if config := envoptions.find_options() is None:
        sys.exit("Your options have not yet been set.  Run this script with the flag '--envoptions' to configure it.")

    files = args.FILES
    output_name = args.output
    amplify_type = args.amplify
    do_truncate = args.truncate
    some_silence = args.silence
    path_specified = args.path
    sort_specified = args.classical

    # TODO: Reorganize main, and then pass args object to them. Or, pass just needed args.
    # Parts: import, export, increment, combined, etc.
    # * Here's the plan for implementing incremental read.  You have to write a .lof with over 15 tracks, or have to pass the option "--incremental".
    # * If incremental, commence incremenetal code. If not, commence normal code.  If .lof has over 15 tracks (or FILES has length greater than 15) then use incremental logic.

    # We make the user responsible for specifying file extensions, because of
    # the possibility of two file extensions on a file.
    paths = []
    lof_specified = False
    # If the user specified two or more files, they are valid audio files.  Put them in paths.
    if len(files) > 1:
        # If the user specified -c, we sort the file inputs.
        if sort_specified:
            files = sorted(files)
        for f in files:
            file = Path(f)
            abs_path = file.resolve(strict=True)
            paths.append(abs_path)
            print(abs_path)
        lof_string = create_lof_string(paths)
        with create_lof_file() as lof_file:
            lof_filepath = Path(lof_file.name).resolve(strict=True)
            lof_file.write(lof_string)
    # If the user specified one file, it could be a .lof file.  Check.
    elif files[0].endswith(".lof"):
        lof_specified = True
        # ? What freaking exceptions will this throw???
        given_lof = Path(files[0])
        lof_filepath = given_lof.resolve(strict=True)
        valid = verify_given_lof(lof_filepath)
        if not valid:
            parser.error("Your .lof file had invalid files, or too few of them.")
    # The user submitted either invalid arguments or too few audio files.
    else:
        parser.error(
            "Not enough valid arguments. Either pass in a .lof file with two or greater files in it, or pass in two or more files by the command line."
        )
        # ? This line is not necessary, as you can tell, because parser.error() exits the thread.
        # ? However, pylance gives me an error if I don't use this (or sys.exit())!
        # ? Perhaps parser.error() doesn't properly mark itself as terminating program execution.
        lof_filepath = None

    # ! Don't forget to close the file handle, then delete it. Also, delete file.name.

    instance = connect(config)
    initialize_audacity()

    # ! Audacity can only handle a maximum of 16 tracks.
    # ! But there are plenty of situations in which we want to mix more than that!
    # ! We need a way to mix tracks bits at a time. Typically,
    # ! this will come up before the global "___all()" operations.
    # TODO: figure out mixing two at a time, building incrementally.
    # TODO: Reorganize the main so that incremental operations are separate from global operations.

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
    if amplify_type == "comb":
        normalize_all()

    # ! Why does generating any noise not allow you to specify a duration?
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

    if (output_path := PurePath(output_name)).is_absolute():
        output = output_name
        print(f"Saving to path: {output}")
    else:
        # If the path is not valid, do away with it.
        name_ext = output_path.name
        output = config.default_loc + name_ext
        print(f"Saving to default path: {output}")

    # ! The resulting quality of the output file is lower than the originals.  Egads!
    # ! TODO: Investigate the cause of lower quality output.
    do(export2(output))

    if not lof_specified:
        remove_lof_file(lof_filepath)
    end_audacity()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        exit()
    # except FileNotFoundError:
    #     print(
    #         "One of your input files was not found! It may have been an erroneous filename, or an improper path."
    #     )
