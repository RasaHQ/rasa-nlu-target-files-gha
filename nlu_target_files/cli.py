import argparse
import logging
import os

from nlu_target_files import constants
from nlu_target_files.target_files import (
    enforce_nlu_target_files,
    infer_nlu_target_files,
)

logger = logging.getLogger(__file__)


def log_inference_warning(
    nlu_data_path,
    nlu_target_files_config,
):
    logger.warning(
        f"""
        Bootstrapping NLU target files config based on files in {nlu_data_path}.

        N.B. Manually review the the output in {nlu_target_files_config} before enforcing it!

        If an intent/synonym/etc. is found in multiple files, the last file it appears in will be taken as the target file.
        Because of how training data is loaded by Rasa, inference of target files can have unexpected results.
        E.g. synonyms in both the short (inline) and long formats have equal status in loaded training data. 
        This means a file can be found to contain a synonym even when it has no explicit "synonym:" section.
        """
    )


def log_enforcement_info(nlu_target_files_config, nlu_data_path):
    logger.warning(
        "\n"
        f"Redistributing data in directory {os.path.abspath(nlu_data_path)} into target files according to config in {os.path.abspath(nlu_target_files_config)}."
    )

    logger.warning(
        "\n"
        f"Note that synonyms, regexes & lookups will be sorted alphabetically."
        "\nTherefore you may see a large diff the first time you run this command.\n"
    )

def enforce(args):
    enforce_nlu_target_files(nlu_target_files_config=args.nlu_target_files_config)


def infer(args):
    try:
        assert os.path.isdir(args.nlu_data_path)
    except AssertionError:
        logger.error(f"ERROR: Directory {args.nlu_data_path} does not exist")
        raise
    infer_nlu_target_files(
        nlu_data_path=args.nlu_data_path,
        nlu_target_files_config=args.nlu_target_files_config,
        default_nlu_target_file=args.default_nlu_target_file,
    )


def add_infer_subparser(subparsers: argparse._SubParsersAction):
    subparser = subparsers.add_parser(
        "infer",
        description="""
    Bootstraps an NLU target files config by inferring targets from the NLU data directory. It does not modify NLU data files.
    If an intent/synonym/etc. is found in multiple files, the last file it appears in will be taken as the target file.
    N.B. Always manually review the the output in to make sure the structure is what you want before enforcing the resulting config.
    """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparser.set_defaults(func=infer)
    subparser.add_argument(
        "--nlu_target_files_config",
        help=("YAML file to which to write inferred target file config."),
        default=constants.TARGET_FILES_CONFIG_FILE,
    )
    subparser.add_argument(
        "--nlu_data_path",
        help=("Path to NLU data directory."),
        default=constants.NLU_DATA_PATH,
    )
    subparser.add_argument(
        "--default_nlu_target_file",
        help=("Target file for items that don't already have a target file."),
        default=constants.DEFAULT_NLU_TARGET_FILE,
    )


def add_enforce_subparser(subparsers: argparse._SubParsersAction):
    parser_enforce = subparsers.add_parser(
        "enforce",
        description="Redistributes NLU training data into the target files specified in the YAML config file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_enforce.set_defaults(func=enforce)
    parser_enforce.add_argument(
        "--nlu_target_files_config",
        help=(
            "YAML file specifying NLU target files. Bootstrap this file with `infer` if you don't have one yet."
        ),
        default=constants.TARGET_FILES_CONFIG_FILE,
    )


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="""
        This program can infer and enforce an NLU target file config for your Rasa NLU data.

        An NLU target file config is a YAML file that specifies which files
        NLU data items belong in.
        Each NLU data type (intent, synonym, regex, and lookup) is assigned
        a default target file, and individual items in each type can also be
        assigned target files. E.g. The default target file for intents could be
        `data/nlu/intents.yml`, but the individual intent `greet` could be assigned to
        `data/nlu/general.yml`. 
    """
    )
    subparsers = parser.add_subparsers()
    add_infer_subparser(subparsers)
    add_enforce_subparser(subparsers)

    return parser
