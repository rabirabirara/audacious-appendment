from pathlib import Path
import os

class Config:
    def __init__(self, default, audacity, write, read, eol):
        self.default_loc = default
        self.audacity_loc = audacity
        self.write_path = write
        self.read_path = read
        self.eol = eol


def find_os_pipes():
    if os.name == "nt":
        # print("Windows OS detected.")
        write_path = Path("\\\\.\\pipe\\ToSrvPipe")
        read_path = Path("\\\\.\\pipe\\FromSrvPipe")
        eol = "\r\n\0"
    else:
        # print("Unix-like OS detected.")
        write_path = Path("/tmp/audacity_script_pipe.to." + str(os.getuid()))
        read_path = Path("/tmp/audacity_script_pipe.from." + str(os.getuid()))
        eol = "\n"
    return (write_path, read_path, eol)

def find_config():
    if os.name == "nt":
        windows_appdata = Path(os.getenv("APPDATA"))
        config_dir = windows_appdata / "audacious_appendment"
    else:
        if unix_xdg := os.getenv("XDG_CONFIG_HOME") is None:
            unix_home = Path(os.getenv("HOME"))
            config_dir = unix_home / ".config" / "audacious_appendment"
    try:
        Path.mkdir(config_dir, parents=True)
    except FileExistsError:
        pass
    return config_dir / "env.txt"


def find_options():
    (write_path, read_path, eol) = find_os_pipes()
    config = find_config()
    if not config.is_file():
        return None
    else:
        with open(config, "r") as config_file:
            settings = config_file.readlines()
            default_save_loc = settings[0].removeprefix("Default save location: ")
            audacity_loc = settings[1].removeprefix("Audacity executable location: ")
            if not Path.is_dir(default_save_loc) or not (Path.is_file(audacity_loc) and os.access(audacity_loc, os.X_OK)):
                sys.exit("Your options are invalid and need to be reset.  Run this script with the flag '--envoptions' to set them up.")
            else:
            return Config(default_save_loc, audacity_loc, write_path, read_path, eol)


def set_options():
    if input("Would you like this script to search for Audacity automatically? (Y/n) ") == 'n':
        audacity_exe = prompt_for_exe()
    else:
        if found := (exe_location := search_for_exe())[0]:
            audacity_exe = exe_location[1]
            print(f"Audacity located at {audacity_exe}.")
        else:
            print("Audacity could not be found. Reverting to input.")
            audacity_exe = prompt_for_exe()

    default_folder = Path(input("Enter the path of the default directory you would like to save your music to.\n"))
    if not Path.is_dir(default_folder):
        if input("A valid directory was not found there.  Would you like to create one? (Y/n) ") == 'n':
            sys.exit("Without a default location to save files to, the script cannot operate. Terminating.")
        else:
            Path.mkdir(default_folder, parents=True)
    else:
        print(f"Default save location found at {default_folder}.")

    print("Saving your options...")
    with open(find_config(), "w") as config_file:
        default = "Default save location: " + str(default_folder) + "\n"
        config_file.write(default)
        audacity = "Audacity executable location: " + str(audacity_exe) + "\n"
        config_file.write(audacity)
    print("Success. Restart this script to use your new options. Terminating.")


# TODO: Implement a simple search for Audacity that investigates Program Files on windows, and /usr/bin || /usr/local/bin on linux. 
def search_for_exe():
    executable_path = ""
    return (False, executable_path)


def prompt_for_exe():
    audacity_exe = Path(input("Please enter the path to your Audacity executable.\n"))
    if Path.is_file(audacity_exe) and os.access(audacity_exe, os.X_OK):
        print(f"Audacity located at your path {audacity_exe}.")
        return audacity_exe
    else:
        sys.exit("Could not find Audacity at your specified path.  This script needs a valid Audacity executable.  Terminating.")

