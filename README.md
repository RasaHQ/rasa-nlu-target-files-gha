# Rasa NLU Target Files Github Action
This repository contains code to infer and enforce target files for Rasa NLU data.
This ensures that data of the same kind and class (e.g. instances of the same synonym) always end
up in the same file, making reviewing NLU data changes easier.

It can be used locally or as a Github Action.
When used as a Github action, it will enforce an NLU target files config. i.e. it will redistribute your NLU
data into the target files you specify.

Locally it can also be used to bootstrap an NLU target file config by inferrring targets from your existing NLU data.

## Target File Config
To use this action, you will need a config file that specifies target file paths, by default called `target_files.yml`.
The path for `nlu_data_path` should be the root of the directory of all your NLU data. The directory can contain other data as well 
e.g. rules or stories, and these will be ignored.

**Use relative paths!** Absolute paths will not be applicable across different machines.
You can bootstrap a config file by [inferring target files locally](#local-use).
You can then update the config file manually to match the target files you want.
You may specify keys (i.e. intents, synonyms, etc.) that do not exist yet.
They will be ignored unless they appear in your data when you enforce the target file config.

The resulting file should follow this format:

```yaml
nlu_data_path: <path to root directory of your NLU data>
default_target_files:
  intents: <some default path>
  synonyms: <some default path>
  regexes: <some default path>
  lookups: <some default path>
target_files:
  intents:
    intent1: <specific target file path>
    intent2: <specific target file path>
  synonyms:
    synonym1: <specific target file path>
    synonym2: <specific target file path>
  regexes:
    regex1: <specific target file path>
    regex2: <specific target file path>
  lookups:
    lookup1: <specific target file path>
    lookup2: <specific target file path>
```


## Use as a Github Action

This Github action enforces an [NLU target file config](#target-file-config).
It will redistribute the data according to the config file provided.
If an input file has no target data associated with it, the file will be deleted.

Basic usage:
```
...
  steps:
  - name: Enforce NLU Target Files
    uses: RasaHQ/rasa-nlu-target-files-gha@v1.0.1
    with:
      target_files_config: ./target_files.yml
```


### Input arguments

You can set the following options using [`with`](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#jobsjob_idstepswith) in the step running this action. The file specified by `target_files_config` must exist for the action to run successfully.



|           Input            |                                                           Description                                                           |        Default         |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `target_files_config`        | The YAML file specifying the target file config. This file can be bootstrapped by running `python -m nlu_target_files infer` locally. | target_files.yml |
| `update_config_file`        | Also update (rewrite) the `target_files_config` file with any new items found. New items will explicitly be assigned to the default file for their section. Specify `true` to use. | false |

### Action Output

There are no output parameters returned by this Github Action. It only rewrites NLU data files according to the given config,
and updates the config file if `update_config_file` is specified.
Remember to **commit the resulting changes in an additional workflow step**!



### Example Usage

For this action to be effective, your workflow should include steps to run this action and
stage and commit any changes made by the action.

For example:
```yaml
on:
  pull_request: {}

env:
  DATA_DIRECTORY: 'data'
  TARGET_FILE_CONFIG: 'target_files.yml'
  COMMIT_MESSAGE: 'Github action: enforced NLU target files'

jobs:
  enforce_nlu_target_files:
    runs-on: ubuntu-latest
    name: Target Files
    steps:
    - name: Cancel Previous Runs
      uses: styfle/cancel-workflow-action@0.8.0
      with:
        access_token: ${{ github.token }}
    - uses: actions/checkout@v2
      with:
        ref: ${{ github.head_ref }}
    - name: Enforce NLU Target Files
      uses: RasaHQ/rasa-nlu-target-files-gha@v1.0.0
      with:
        nlu_target_file_config: ${{ env.TARGET_FILE_CONFIG }}
        update_config_file: true
    - name: Commit changes if any were made
      uses: stefanzweifel/git-auto-commit-action@v4
      with:
        commit_message: '${{ env.COMMIT_MESSAGE }}'
        file_pattern: ${{ env.DATA_DIRECTORY }} ${{ env.TARGET_FILE_CONFIG }}
```


## Local Use

To infer NLU target files from your existing Rasa project, run:

```bash
python -m nlu_target_files infer --nlu_data_path <PATH_TO_YOUR_NLU_DATA_DIR>
```

See `python -m nlu_target_files infer --help` for more options.

To enforce your target file config, run:

```
python -m nlu_target_files enforce --target_files_config <PATH_TO_YAML_FILE>
```
