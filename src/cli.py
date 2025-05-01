# lib for parsing cl argument into object that I can pick attribute from
import argparse

def main():
    args = parse_args()
    args.func(args)

def parse_args():
    parser = argparse.ArgumentParser() # parser object

    # We will add sub-parser for handling sub-command
    commands = parser.add_subparsers(dest="command")
    commands.required = True

    # this function take the command string, then return the parser we can modify
    init_parser = commands.add_parser("init") # this one is init parser
    init_parser.set_defaults(func=init) # just set the attribute name "func" to the init function

    return parser.parse_args()

def init(args):
    print("Hello, world")
