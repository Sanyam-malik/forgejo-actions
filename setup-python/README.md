# Setup Python

Install a prebuilt Python distribution from `actions/python-versions` and configure `PYTHON_HOME`.

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
| `python_version` | Python version to install (for example 3, 3.11, 3.12, 3.12.7) | No | `3` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Intended for Linux runners and does not require `sudo`, a compiler, or a system package manager.
- Resolves `3`, `3.11`, or an exact version such as `3.11.9` to the newest matching prebuilt release.
- Requires `curl` and `tar` to already be available on the runner.
- Installs into `$HOME/.python/<version>` and prepends its `bin` directory to `PATH`.
- Downloads the Ubuntu 22.04 x64 or arm64 artifact from `actions/python-versions`.
- When `PKG_CACHE` is set, downloads use `<PKG_CACHE>/github.com/actions/python-versions/releases/download`; otherwise they use GitHub directly.
