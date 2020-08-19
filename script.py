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

    # These are global to the class, remember - a form of shared state, even between threads.
    # This is a form of shared mutable state between threads.  The threads communicate
    # using these variables.  The instance variable in question for the second is self._reply.
    # The write and read threads communicate with the threading event object, and when the event object says
    # "ok, it's set/unset", then they know to access the variable.
    # They can be set and unset from anywhere.
    reader_pipe_broken = threading.Event()
    # Unset when sending a command, set when receiving a response.
    reply_ready = threading.Event()

    # In Python every object has a __dict__ attribute, which contains their symbol table.
    # It's because everything in Python is an object.

    def __init__(self):
        self._write_pipe = None
        self._reply = ""
        self._write_thread_start()
        self._read_thread_start()

    def _write_thread_start(self):
        # We open the pipe in a new thread, so that if Audacity isn't running, the program does not freeze/shut down.
        # To use Thread() and create a thread object, we pass a callable object to the constructor.
        # write_thread is now a thread_object.
        # As long as this instance lives, this thread will live, up until the
        # other non-daemon threads close (and the program exits).
        write_thread = threading.Thread(target=self._write_pipe_open)
        # Let's make it a daemon thread.  If there are no daemon threads left, the program doesn't necessarily exit.
        # If all the non-daemon threads are gone, however, the program will exit.
        # Deamon threads are useful for background threads that stay alive only because they serve
        # other more purposeful function in the program; once the program's purpose is served, we don't
        # have to expend the effort to go and manually close them.  This is great for a pipe client, though we don't
        # need them to be daemon necessarily.
        write_thread.daemon = True
        # Now we call the function we passed to the thread.
        write_thread.start()
        # We let some time for the connection to be made (from the thread above).
        time.sleep(0.2)
        if not self._write_pipe:
            sys.exit("Write pipe could not be opened.")

    def _write_pipe_open(self):
        self._write_pipe = open(WRITE_NAME, "w")

    def _read_thread_start(self):
        read_thread = threading.Thread(target=self._reader)
        read_thread.daemon = True
        read_thread.start()

    def _reader(self):
        """Read FIFO in worker thread."""
        read_pipe = open(READ_NAME, "r")
        message = ""
        pipe_ok = True
        while pipe_ok:
            line = read_pipe.readline()
            while pipe_ok and line != "\n":
                message += line
                # No data in pipe indicates Audacity has crashed.
                if line == "":
                    AudacityInstance.reader_pipe_broken = True
                    pipe_ok = False
            # When we receive a \n, we mark to the class that the reply has been set.
            self.reply = message
            AudacityInstance.reply_ready.set()
            message = ""
        read_pipe.close()

    def write(self, command):
        print("Sending command:", command)
        self._write_pipe.write(command + EOL)
        # Check that the read pipe  is still alive
        # We don't want to send commands if we can't receeive responds.
        if AudacityInstance.reader_pipe_broken.isSet():
            sys.exit(
                "The read pipe received an error.  Audacity has probably crashed or ran into an error."
            )
        try:
            self._write_pipe.flush()
            self.reply = ""
            AudacityInstance.reply_ready.clear()
        except IOError as e:
            if e.errno == errno.EPIPE:
                sys.exit("The write pipe received an error.")
            # If the error isn't regular, we need to raise the error to send it to the call stack.
            else:
                raise

    def read(self):
        # If the reply flag is not ready, then there can be no reading done.
        if not AudacityInstance.reply_ready.isSet():
            return ""
        return self.reply

    # def send_command(self, command):
    #     """Send a single command to the file handle."""
    #     print("Send >>>")
    #     print(command)
    #     self.write_pipe.write(command + self.eol)
    #     self.write_pipe.flush()
    #
    # def receive_response(self):
    #     """Receive a response from Audacity."""
    #     print("Receive <<<")
    #     response = ""
    #     line = ""
    #
    #     # Response terminates on \n alone.
    #     while line != "\n":
    #         response += line
    #         line = self.read_pipe.readline()
    #     print(response)

    def do_command(self, command):
        """Perform a single command and print the response."""
        self.write(command)
        print(self.read())


def start_audacity():
    os.startfile("D:/Program Files (x86)/Audacity/audacity.exe")


def wait_for_startup():
    print("Waiting 5 seconds for Audacity to initialize:")
    for i in range(0, 5):
        time.sleep(1.0)
        print("Waiting: {}".format(i))
    print("Finished waiting.  Begin command execution.")


def connect():

    print("Let's wait 30 seconds for Audacity to start:")
    start = time.time()
    while not os.path.exists(WRITE_NAME) or not os.path.exists(READ_NAME):
        time.sleep(1.0)
        end = time.time()
        diff = end - start
        print("Waiting for Audacity... {} seconds left".format(round(30.0 - diff)))
        if diff > 30.0:
            print("Script aborted. Audacity took too long to open!")
            sys.exit()

    print("Successfully located Audacity instance.")
    TOFILE = open(WRITE_NAME, "w")
    FROMFILE = open(READ_NAME, "rt")

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
    return "Import2: Filename={}".format(filename)


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

    lof_string = create_lof_string(paths)
    with create_lof_file() as lof_file:
        lof_filepath = os.path.abspath(lof_file.name)
        lof_file.write(lof_string)
    # ! Don't forget to close the file handle, then delete it. Also, delete file.name.

    start_audacity()
    instance = connect()
    instance.do_command(import2(lof_filepath))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        exit()
    except FileNotFoundError:
        print(
            "One of your input files was not found! It may have been an erroneous filename, or an improper path."
        )
