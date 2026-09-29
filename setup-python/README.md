# Setup Python

Install Python and configure PYTHON_HOME on multiple Linux distributions

## Usage

```yaml
steps:
  - name: Setup Python
    id: setup-python
    uses: your-org/forgejo-actions/setup-python@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `python_version` | Python version to install (for example 3, 3.11, 3.12) | No | `3` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Intended for Linux runners and uses the available system package manager; installation may require `sudo`.
