# Condition Check

Check whether a value matches a regular expression

## Usage

```yaml
steps:
  - name: Condition Check
    id: condition-check
    uses: your-org/forgejo-actions/condition-check@v1
    with:
      value: value
      regex: ^value$
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `value` | Value to evaluate against the regular expression | Yes | — |
| `regex` | Regular expression used to validate the input value | Yes | — |

## Outputs

| Name | Description |
| --- | --- |
| `matches` | Returns 'true' if the value matches the regex, otherwise 'false' |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
