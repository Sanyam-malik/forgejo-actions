# Setup Java

Install OpenJDK and configure JAVA_HOME on multiple Linux distributions

## Usage

```yaml
steps:
  - name: Setup Java
    id: setup-java
    uses: your-org/forgejo-actions/setup-java@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `java_version` | Java version to install | No | `17` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Intended for Linux runners and uses the available system package manager; installation may require `sudo`.
