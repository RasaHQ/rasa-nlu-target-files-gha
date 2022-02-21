# Rasa NLU Target Files Github Action
This repository contains code to infer and enforce target files for Rasa NLU data.
This ensures that data of the same kind and class (e.g. instances of the same synonym) always end
up in the same file, making reviewing NLU data changes easier.

It can be used locally or as a Github Action.
When used as a Github action, it will enforce an NLU target files config. i.e. it will redistribute your NLU
data into the target files you specify.

Locally it can also be used to bootstrap an NLU target file config by inferrring targets from your existing NLU data.

## Target File Config
To use this action, you will need a config file that specifies target file paths, by default called `target_files_config.yml`.
**Use relative paths!** Absolute paths will not be applicable across different machines.
You can bootstrap a config file by [inferring target files locally](#local-use).
The resulting file will follow this format:
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

You can update the config file manually to match the target files you want.
You may specify keys (i.e. intents, synonyms, etc.) that do not exist yet.
They will be ignored unless they appear in your data when you enforce the target file config.


## Use as a Github Action

This Github action enforces an [NLU target file config](#target-file-config).
It will redistribute the data according to the config file provided.
If an input file has no target data associated with it, the file will be deleted.

Basic usage:
```
...
  steps:
  - name: Enforce NLU Target Files
    uses: RasaHQ/rasa-nlu-target-file-gha@1.0.0
    with:
      nlu_target_file_config: ./nlu_target_file_config.yml
```


### Input arguments

You can set the following options using [`with`](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#jobsjob_idstepswith) in the step running this action. The file specified by `target_files_config` must exist for the action to run successfully.



|           Input            |                                                           Description                                                           |        Default         |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `target_files_config`        | The YAML file specifying the target file config. This file can be bootstrapped by running `python -m nlu_target_files infer` locally. | target_files_config.yml |


### Action Output

There are no output parameters returned by this Github Action. It only rewrites NLU data files according to the given config.
Remember to **commit the resulting changes in an additional workflow step**!



### Example Usage

For this action to be effective, your workflow should include steps to run this action and
stage and commit any changes made by the action.

For example:
```yaml
on:
  push: {}

jobs:
  enforce_nlu_target_files:
    runs-on: ubuntu-latest
    name: Cross-validate
    steps:
    - name: Enforce NLU Target Files
      uses: RasaHQ/rasa-nlu-target-file-gha@1.0.0
      with:
        nlu_target_file_config: ./nlu_target_file_config.yml
    - name: Check if changes were made
      id: git_diff
      run: |
        git diff --exit-code
      continue-on-error: true
    - name: Commit changes if any were made
      if: steps.git_diff.outcome=='failure'
      env:
        COMMIT_USERNAME: 'Github Actions'
        COMMIT_EMAIL: 'github.actions@users.noreply.github.com'
        DATA_DIRECTORY: 'data'
        COMMIT_MESSAGE: 'Github action: enforced NLU target files'
      run: |
        git config --global user.name '${{ env.COMMIT_USERNAME }}'
        git config --global user.email '${{ env.COMMIT_EMAIL }}'
        git add '${{ env.DATA_DIRECTORY }}'
        git commit -am '${{ env.COMMIT_MESSAGE }}'
        git push
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
