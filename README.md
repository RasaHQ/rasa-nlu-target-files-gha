# Rasa NLU Target Files Github Action
This repository contains code to infer and enforce target files for Rasa NLU data.
This ensures that data of the same kind and class (e.g. instances of the same synonym) always end
up in the same file, making reviewing NLU data changes easier.

It can be used locally or as a Github Action.
When used as a Github action, it will **enforce** NLU target files.
**N.B.** For this action to be effective, you must **commit the resulting changes in an additional workflow step**!

When used locally, it can either **infer** or **enforce** NLU target files.

## Use as a Github Action

This Github action enforces an NLU target file config using the command `python -m nlu_target_files enforce` with the [input arguments](#input-arguments) provided to it.

Basic usage:
```
...
  steps:
  - name: Enforce NLU Target Files
    uses: RasaHQ/rasa-nlu-target-file-gha@1.0.0
    with:
      nlu_target_file_config: ./nlu_target_file_config.yml
```

### Action Output

There are no output parameters returned by this Github Action. It only rewrites NLU data files according to the given config.
Remember to **commit the resulting changes in an additional workflow step**!


### Input arguments

You can set the following options using [`with`](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#jobsjob_idstepswith) in the step running this action. The file specified by `nlu_target_files_config` must exist for the action to run successfully.



|           Input            |                                                           Description                                                           |        Default         |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `nlu_target_files_config`        | The YAML file specifying the target file config. This file can be bootstrapped by running `python -m nlu_target_files infer` locally. | nlu_target_files_config.yml |



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

To infer NLU target files from your existing Rasa project and bootstrap the config file, run:

```bash
python -m nlu_target_files infer --nlu_data_path <PATH_TO_YOUR_NLU_DATA_DIR>
```

See `python -m nlu_target_files infer --help` for more options.

To enforce your target file config, run:

```
python -m nlu_target_files enforce --nlu_target_files_config <PATH_TO_YAML_FILE>
```
