import logging

from nlu_target_files import cli

logger = logging.getLogger(__file__)


def main():
    parser = cli.create_argument_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_usage()
        exit()
    args.func(args)


if __name__ == "__main__":
    main()
