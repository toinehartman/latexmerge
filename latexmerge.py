#!/usr/bin/env python3

import argparse
import re
import os
import shutil
import subprocess
import json

from tqdm import *

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def tex_escape(text):
    """
        :param text: a plain text message
        :return: the message escaped to appear correctly in LaTeX
    """
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless',
        '>': r'\textgreater'
    }
    regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key = lambda item: - len(item))))
    return regex.sub(lambda match: conv[match.group()], text)

def args():
    parser = argparse.ArgumentParser(description="Insert values from CSV into LaTeX letter template")

    parser.add_argument("--config", "-c", default="config.json", dest="config", help="the path to the configuration file, holding all column mappings")
    parser.add_argument("--template", "-t", required=True, dest="template", type=str, help="the path to the LaTeX template")
    parser.add_argument("--out", "-o", required=True, dest="output", type=str, help="the path to the output directory")
    parser.add_argument("--data", "-d", required=True, dest="data", type=str, help="the path to the CSV data")
    parser.add_argument("--skip", dest="skip_empty", action="store_true", help="skip empty lines in the data file")

    return parser.parse_args()

def head(path):
    with open(path, 'r') as f:
        return f.readlines()[0]

def tail(path):
    with open(path, 'r') as f:
        return f.readlines()[1:]

def replace(format_str, d):
    result_str = format_str
    for k in d.keys():
        result_str = result_str.replace(k, d[k])
    return result_str

def replace(format_str, header, config, data, escape=True):
    result_str = format_str
    for tag, column in config.items():
        try:
            index = header.index(column)
            if escape:
                result_str = result_str.replace(tag, tex_escape(data[index]))
            else:
                result_str = result_str.replace(tag, data[index])
        except ValueError:
            continue
    return result_str

def ensure_dirs(*dirs):
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)

def remove_dirs(*dirs):
    for d in dirs:
        shutil.rmtree(d)

def load_config(filename):
    with open(filename, 'r') as config_file:
        config_json = config_file.read()
        return json.loads(config_json)

if __name__ == "__main__":
    args = args()

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print("The given configuration file does not exist. Create it, or choose another file!")
        exit(1)

    print("   template file: {}".format(args.template))
    print("      output dir: {}".format(args.output))
    print("       data file: {}".format(args.data))
    print("     config file: {}".format(args.config))
    print("skip empty lines: {}".format(args.skip_empty and "yes" or "no"))
    print("          config: {}".format(config))

    TMP_DIR = os.path.join("temp")
    TEMPLATE_STR = open(args.template, 'r').read()

    ensure_dirs(TMP_DIR, args.output)

    header = head(args.data).split(',')

    print("\n{}Brieven maken van template:{}\n{}\n".format(color.BOLD, color.END, TEMPLATE_STR))

    for line in tqdm(tail(args.data)):
        data = line.split(',')
        if args.skip_empty and re.match(r"^([\s,])+$", line):
            continue

        letter = replace(TEMPLATE_STR, header, config, data)
        identifier = replace(config["_identifier"], header, config, data, escape=False).replace('\n', '').replace('"', '\"').replace("'", "\'")
        # identifier = "_".join([data[k] for k in IDENTIFIERS])

        filename_tex = os.path.abspath(os.path.join(TMP_DIR, ".".join([identifier, "tex"])))
        filename_tmp = os.path.abspath(os.path.join(TMP_DIR, ".".join([identifier, "pdf"])))
        filename_out = os.path.abspath(os.path.join(args.output, ".".join([identifier, "pdf"])))

        # write tex
        with open(filename_tex, 'w') as tex:
            tex.write(letter)

        # compile pdf
        subprocess.call(["pdflatex", filename_tex], cwd=TMP_DIR, stdout=subprocess.DEVNULL)

        # copy pdf to output dir
        subprocess.call(["cp", filename_tmp, filename_out], stdout=subprocess.DEVNULL)

    remove_dirs(TMP_DIR)
