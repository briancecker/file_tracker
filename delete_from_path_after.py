#!/usr/bin/python3

import functools
import json
import os
import shutil
import time
from glob import glob
from optparse import OptionParser

TIME_MAP = {
    "S": {"name": "seconds", "num_seconds": 1},
    "M": {"name": "minutes", "num_seconds": 60},
    "H": {"name": "hours", "num_seconds": 60 * 60},
    "D": {"name": "days", "num_seconds": 60 * 60 * 24},
    "W": {"name": "weeks", "num_seconds": 60 * 60 * 24 * 7},
    "Y": {"name": "years", "num_seconds": 60 * 60 * 24 * 7 * 52},
}

debug = False
config_path = os.path.join(os.path.expanduser("~"), ".file_watcher")
file_list = os.path.join(config_path, "file_list.json")


def time_from_opt(option, opt, value, parser, time_type=None):
    assert (time_type in TIME_MAP)
    setattr(parser.values, option.dest, TIME_MAP[time_type]["num_seconds"] * value)


def get_opts():
    parser = OptionParser(usage="usage: %prog [options] path1 path2 ...",
                          epilog="DEFAULT ACTION: Add new files to watched list")
    tf = functools.partial(time_from_opt)
    for time_type, time_data in TIME_MAP.items():
        parser.add_option("-{0}".format(time_type), type="int", action="callback",
                          callback=functools.partial(tf, time_type=time_type),
                          help="time in {0}".format(time_data["name"]))

    parser.add_option("-v", action="count", dest="verbosity", help="be verbose")
    parser.add_option("-f", action="store_true", dest="force", help="force recursive directory deletes")
    parser.add_option("-l", action="store_true", dest="list", help="list a watched file")
    parser.add_option("--unlist", action="store_true", dest="unlist", help="unlist a watched file")
    parser.add_option("--delete", action="store_true", dest="delete", help="run deletion on watched files")

    options, args = parser.parse_args()
    options = vars(options)

    return options, args


def print_debug(*args, **kwargs):
    global debug
    if debug:
        print(*args, **kwargs)


def get_matched_files(args):
    return [os.path.abspath(file) for pattern in args for file in glob(pattern)]


def get_printable_time(time_in_seconds):
    return "printable time"


def add_file_to_config(config, name, time_in_seconds):
    config["files"][name] = time_in_seconds


def list_files(config):
    assert("files" in config)

    files = list(config["files"].items())
    if len(files) == 0:
        print("There are no tracked files")
    else:
        files.sort(key=lambda tup: tup[1])
        print("Tracked files:")
        for tup in files:
            print("\t{0}: {1}".format(get_printable_time(tup[1]), tup[0]))


def unlist_files(config, args, verbosity):
    for path in get_matched_files(args):
        if path in config["files"]:
            if verbosity:
                print("Untracking file: {0}".format(path))
            config["files"].pop(path)
        else:
            print("path not tracked, so we cannot untrack it: {0}".format(path))


def add_files(args, config, time_ago_to_delete, force, verbosity):
    print_debug("adding files")
    for file in get_matched_files(args):
        if time_ago_to_delete == 0 and not force:
            print("cowardly refusing to track file for deletion without time, "
                  "use -f to force add the file with 0 deletion time")
        else:
            if verbosity:
                print("Tracking file: {0}".format(file))
            add_file_to_config(config, file, time_ago_to_delete)


def delete_files(options, config):
    now = time.time()

    for path, time_in_seconds in config["files"].items():
        print_debug("tracked file: {0}".format(path))
        if os.path.exists(path):
            # This really should exist, but just in case
            time_created_ago = now - os.path.getmtime(path)
            if time_created_ago > time_in_seconds:
                removed = False
                if os.path.isfile(path):
                    print_debug("is a file")
                    os.remove(path)
                    removed = True
                elif os.path.isdir(path):
                    print_debug("is a dir")
                    choice = None
                    while choice != "y" and choice != "n":
                        if options["force"]:
                            choice = 'y'
                        else:
                            print("remove directory recursively [y/n]: {0}".format(path))
                            choice = input().lower()

                        if choice == "y":
                            shutil.rmtree(path)
                            removed = True

                if options["verbosity"] and removed:
                    print("removed {0}".format(path))


def main():
    global debug
    options, args = get_opts()

    if options["verbosity"] is not None and options["verbosity"] >= 3:
        print("Debug set to true")
        debug = True

    time_ago_to_delete = sum(options[time_type] for time_type in TIME_MAP if options[time_type] is not None)

    config = read_config()

    if options["list"]:
        print_debug("doing file listing")
        list_files(config)
    elif options["unlist"]:
        print_debug("unlisting")
        unlist_files(config, args, options["verbosity"])
    elif options["delete"]:
        delete_files(options, config)
    else:
        # add files to watched list
        add_files(args, config, time_ago_to_delete, options["force"], options["verbosity"])

    write_config(config)


def setup_config():
    if not os.path.exists(config_path):
        print_debug("making config directory")
        os.makedirs(config_path)
    if not os.path.exists(file_list):
        print_debug("making config file")
        write_config({"files": dict()})


def read_config():
    with open(file_list, 'r') as fh:
        return json.load(fh)


def write_config(config):
    with open(file_list, 'w') as fh:
        json.dump(config, fh)


if __name__ == "__main__":
    setup_config()
    main()
