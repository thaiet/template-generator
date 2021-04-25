#!/usr/bin/env python3
#
# Generates a bash template for scripting.


import os
import sys
import re
import argparse
from datetime import date
from string import ascii_lowercase


def main():
  args = parse_arguments()
  content = ""

  descriptions = get_script_descriptions(args)

  content += add_headers(args, descriptions)
  content += add_useful_vars(args)
  content += add_safety(args)
  content += add_cleanup_function(args)

  flags_data = get_flags_data(args)
  content += add_flags_data(args, flags_data, descriptions)
  content += add_flags_functions(args)

  content += add_colors_function(args)
  content += call_functions(args)
  content += "\n# SCRIPT STARTS HERE\n"

  create_script(content)


# Ask user for script name and create script
def create_script(content):
  script_name = sanitize_input("Script name (don't add extension): ",
                               lambda x: (x + ".sh"))
  if os.path.exists(script_name):
    f = open(script_name, "w")
  else:
    f = open(script_name, "x")
  f.write(content)
  f.close()


def get_script_descriptions(args):
  """ Queries user for descriptions for the script
  """
  descriptions = {"long": "TODO <LONG_DESCRIPTION>",
                  "short": "TODO <SHORT_DESCRIPTION>"}
  add_descriptions = input_bool("Add in script description [True/False]: ")
  if not add_descriptions:
    return descriptions

  descriptions["short"] = sanitize_input("Short description: ") 
  descriptions["long"] = sanitize_input("Long description: ") 
  return descriptions
  

def add_headers(args, descriptions):
  """ Adds header to script for documentation.
  """
  
  prefix = "# "
  skip_line = prefix + "\n"

  header = "#!/usr/bin/env bash\n#\n"
  header += prefix 
  header += descriptions["short"] + "\n" + skip_line

  formatted_long_description = \
    split_string_length(descriptions["long"], 79 - len(prefix), prefix) 
  header += prefix + formatted_long_description

  header += prefix + "\n"

  today = date.today()
  header += prefix + "Date Created: " + today.strftime("%m/%d/%Y")
  header += """
# 
# Author(s): """ + input("Author: ") + "\n\n\n"

  return header


def add_useful_vars(args):
  """ Adds in some useful variables for any bash script.
  """
  useful_vars = """\
# Exit codes
sucess_code=0
replicate_flag_code=1
invalid_argument_code=2
missing_argument_code=3
no_mandatory_flag_code=4

script_name=${0##*/}
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

"""
  return useful_vars


def add_safety(args):
  """ Adds line to prevent runaway (disabled by default since most people
  do not expect these options turned on).

  Also adds in cleanup.
  """
  
  safety_lines = ""
  if args.strict:
    safety_lines += "set -Eeuo pipefail \n" 

  if args.cleanup: 
    safety_lines += "trap cleanup SIGINT SIGTERM ERR EXIT \n\n"

  return safety_lines


def add_colors_function(args):
  """ Adds in color function for nice printing.
  """

  if args.no_color: 
    return ""

  color_function = """\
setup_colors() {
  if  [[ -t 2 ]] && [[ -z "${NO_COLOR-}" ]] && [[ "${TERM-}" != "dumb" ]]; then
    NOFORMAT='\\033[0m' RED='\\033[0;31m' GREEN='\\033[0;32m' ORANGE='\\033[0;33m' BLUE='\\033[0;34m' PURPLE='\\033[0;35m' CYAN='\\033[0;36m' YELLOW='\\033[1;33m'
  else
    NOFORMAT='' RED='' GREEN='' ORANGE='' BLUE='' PURPLE='' CYAN='' YELLOW=''
  fi
} \n\n"""
  
  return color_function


def add_cleanup_function(args):
  """ Adds in cleanup function that was setup in the add_safety function.
  """
  if not args.cleanup:
    return ""

  cleanup_function = """ \
cleanup() {
  trap - SIGINT SIGTERM ERR EXIT
  # TODO: Script cleanup here
} \n\n"""

  return cleanup_function


def get_flags_data(args):
  """ Get flag data from user.
  """
  flag_data = []
  
  prompt = """ \
Argument Builder Commands:
Dynamically creates flags for bash scripts. Note that you can skip this and call this script later on for adding additional 
flags.
  A - Add Argument
  X - Exit Builder

Command: """

  # Add in help option
  help_data = {"short":"h",
               "takes_value":False,
               "mandatory":False,
               "description": "Show this help message and exit."}
  flag_data.append(help_data)

  while (True):
    exit = sanitize_input(prompt, 
                            lambda x: ({"a":False,"x":True}[x.lower()]))
    if exit:
      break
    flag_data.append(get_individual_flag_data(args))
    print("Flag added...")
  
  return flag_data


def get_individual_flag_data(args):
  data = {}

  data['short'] = sanitize_input("Short hand (a-z): ", check_lowercase_alpha)
  data['varname'] = sanitize_input("Variable Name: ", check_uppercase_underscored)
  data['takes_value'] = input_bool("Should flag take value? ")
  data['mandatory'] = input_bool("Mandatory Variable? ")
  data['description'] = sanitize_input("Help description: ")
  return data


def add_flags_data(args, flags_data, descriptions):
  flag_var_strings = ""
  parameter_string = "getopts_parameter_string=\":" # Default getopts param
  mandatory_string = "mandatory_flags=\""
  usage_help_string = "Usage: $script_name"
  full_optional_help_string = "optional arguments:\n"
  full_required_help_string = "required arguments:\n"

  for flag_data in flags_data:
    variable = "flag_" + flag_data['short'] + "_string"
    if flag_data['short'] != "h":
      flag_var_strings += variable + "=\"-" + flag_data['short'] + " " + flag_data['varname'] + "\"\n"

    parameter_string += flag_data['short'] 
    if flag_data['takes_value']:
      parameter_string += ":"
    if flag_data['mandatory']:
      usage_help_string += " $" + variable
      mandatory_string += flag_data['short']
      full_required_help_string += "$" + variable + """
                             """ + split_string_length(flag_data["description"], 50)
    else:
      if flag_data['short'] == "h":
        usage_help_string += " [-h]"
        full_optional_help_string += "-h"
      else:
        usage_help_string += " [$" + variable + "]"
        full_optional_help_string += "$" + variable
      full_optional_help_string += """
                             """ + split_string_length(flag_data["description"], 50)

  parameter_string += "\""
  mandatory_string += "\""
  flag_string = """\
# Flag strings
""" + flag_var_strings + "\n" 
  flag_string += parameter_string + "\n"
  flag_string += mandatory_string + "\n"

  usage_string = "usage_help=$(cat <<EOF\n" + split_string_length(usage_help_string, 80) + "EOF\n)\n"
    
  full_help_string = "full_help=$(cat <<EOF\n" + split_string_length(descriptions["long"], 120)
  full_help_string += "\n" + full_optional_help_string + "\n" + full_required_help_string + """
EOF
)\n"""

  return flag_string + "\n" + usage_string + "\n" + full_help_string + "\n"


def add_flags_functions(args):
  flag_functions = """\
# Checks to see if manadatory flag is present and if not, show usage help and
# throw error exit code.
# Args:
#      $1 - Flag counter
#      $2 - Flag (e.g. -m)
function check_mandatory_flag() {
  if [[ $1 -eq 0 ]]; then
    echo $2" flag is required"
    echo "$usage_help"
    exit $no_mandatory_flag_code
  fi
}

# Loops through all manadatory flags to see if specified
function check_all_mandatory_flags() {
  for char in {a..z} {0..9}
  do
    if [[ $mandatory_flags =~ $char ]]; then
      eval 'check_mandatory_flag $flag_'$char' $flag_'$char'_string'
    fi
  done
}

# Intialize all getopts flag counters equal to 0
function initialize_flag_counters() {
  for char in {a..z} {0..9}
  do
    if [[ $getopts_parameter_string =~ $char ]]; then
      eval 'flag_'$char'=0'
    fi
  done
}

# Sum up all the flag counters
function sum_exp6_flags() {
  SUM_EXP6=0
  for char in {a..z} {0..9}
  do
    if [[ $getopts_parameter_string =~ $char ]]; then
      eval 'SUM_EXP6=$((SUM_EXP6+flag_'$char'**6))'
    fi
  done
}

# Add the flag counters and assign variable based on flag string
# Args:
#     $1 - option char (e.g. a, b, c, etc.)
#     $2 - value assignment (e.g ${OPTARG})
function add_assign_getopts() {
  eval 'var_name=${flag_'$1'_string#*[[:blank:]]}'
  eval $var_name'='$2
  eval 'flag_'$1'=$((flag_'$1'+1))'
}

initialize_flag_counters
while getopts $getopts_parameter_string option
do
  case "${option}" in

    h )
    echo "$usage_help"
    echo ""
    echo "$full_help"
    exit $sucess_code;;

    : )
    echo "Invalid option: -$OPTARG requires an argument" 1>&2
    echo $usage_help
    exit $missing_argument_code;;

    * )
    # Assign and add flag counter for parameter, if
    # in getopts_parameter_string
    if [[ $getopts_parameter_string =~ ${option} ]]; then
      add_assign_getopts "${option}" ${OPTARG}
    fi
    # The following line is a trick used to see if any of the flags have been
    # defined twice. By exponentiating all flag counters by 6, unless there are
    # more short arguments defined, a summed counter value of all flags should
    # only be 36 as there are only 36 alpha-numeral characters. We chose the
    # lowest number to exponentiate by to prevent accidental overloading.
    sum_exp6_flags
    if [[ $SUM_EXP6 -gt 36 ]]; then
      current_flag_index=$(($OPTIND-2))
      echo "Replicate flag: ${!current_flag_index} has already been"\
      "specified"
      echo "$usage_help"
      exit $replicate_flag_code
    fi;;&

    \? )
    echo Not a valid option
    echo $usage_help
    exit $invalid_argument_code;;
  esac
done
\n"""
  return flag_functions


def call_functions(args):
  functions = "check_all_mandatory_flags\nsetup_colors\n"
  return functions

def check_lowercase_alpha(letter):
  """ Make sure that letter given is a part of the set of lowercase letters.

  If not, a KeyError is thrown.
  """
  if letter in ascii_lowercase:
    return letter
  raise KeyError
  

def check_uppercase_underscored(varname):
  """ Make sure that variable name given is a valid one.

  We force that all variable names be uppercase for clarity sake.
  """
  # Check for variable name contains only underscores and letters
  if re.match("[^_|^a-z|^A-Z]", varname):
    raise KeyError
    return

  if varname.upper() != varname:
    print("Variable name: " + varname + """ should be in all caps, forcing uppercase. 
          If you would like to disable this feature see help.""")

  return varname.upper()


def parse_arguments():
  parser = argparse.ArgumentParser(description='Generates a bash boilerplate.')
  parser.add_argument('-s', '--strict', action='store_true',
                      help="""Adds in strict requieements for bash scripting, 
                      prevent continuation of script due to pipefail. Note that
                      this behavior is known to be inconsistent and is not 
                      recommended.""")

  parser.add_argument('-n', '--no_color', action='store_true',
                      help="""Color function for nicer printing, turned on
                      by default. Use this flag to remove function. Function
                      can also be just left in the script and the call to the
                      function removed.""")
  
  parser.add_argument('-c', '--cleanup', action='store_true',
                      help="""Adds in cleanup function for script cleanup. If
                      you don't need to add in any cleanup for your script,
                      this is unnecessary.""")

  parser.add_argument('-a', '--amend_parameters', action='store_true',
                      help="""Rather than creating a new script, using this
                      flag, will amend a script. Note that this will not amend
                      the document's comment header.""")

  parser.add_argument('-u', '--variable_lowercase', action='store_true',
                      help="""As a way to enforce clearer programming in bash all
                      command line variables are automatically created as uppercase, since
                      they should essentially be constants. If this flag is used, variable
                      names will be created as is.""")

  return parser.parse_args()


def input_bool(prompt):
  return sanitize_input(prompt, 
    lambda x: ({"true":True, "false":False,
                "t":True, "f":False,
                "yes":True, "no":False,
                "y":True, "n":False}[x.lower()]))


def sanitize_input(prompt, filter_func=lambda x:x, error_msg="Invalid Input."):
  while (True):
    try:
      return filter_func(input(prompt))
    except KeyError:
      print(error_msg)
    except KeyboardInterrupt:
      sys.exit("\nExiting")


def split_string_length(string, max_length, prefix=""):
  words = string.split(" ")
  sentence_length = 0
  split_string = ""

  for word in words:
    if sentence_length + len(word) > max_length:
      split_string += "\n" + prefix + word + " "
      sentence_length = 0
    else:
      split_string += word + " "

    sentence_length += len(word) + 1 # Include the space

  return split_string + "\n"


if __name__ == "__main__":
  main()
