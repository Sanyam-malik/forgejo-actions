# Setup Go

Install Go on multiple Linux distributions

## Usage

```yaml
steps:
  - name: Setup Go
    id: setup-go
    uses: your-org/forgejo-actions/setup-go@v1
```

## Inputs

This action has no inputs.

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Intended for Linux runners and uses the available system package manager; installation may require `sudo`.
