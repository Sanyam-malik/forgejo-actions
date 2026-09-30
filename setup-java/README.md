# Setup Java

Install a Java distribution and configure JAVA_HOME on multiple Linux distributions

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
| `distribution` | Java distribution to install (`openjdk`, `temurin`, `zulu`, `liberica`, `microsoft`, `corretto`, `oracle`, `semeru`, `graalvm`, `sapmachine`, `dragonwell`, or `mandrel`) | No | `openjdk` |

To install Temurin instead of the system OpenJDK packages:

```yaml
steps:
  - uses: your-org/forgejo-actions/setup-java@v1
    with:
      java_version: "21"
      distribution: temurin
```

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Intended for Linux runners and uses the available system package manager; installation may require `sudo`.
- Reads the inherited `PKG_CACHE` environment value for Foojay API and archive downloads, falling back to the official service when it is unset. Run `setup-cache` before this action to configure mirrored system package repositories.
