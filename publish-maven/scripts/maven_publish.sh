#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${1:?registry required}"
USER="${2:?user required}"
TOKEN="${3:?token required}"

OWNER="${GITHUB_REPOSITORY%%/*}"
OWNER=$(echo "$OWNER" | tr '[:upper:]' '[:lower:]')
REPO_NAME=$(echo "${GITHUB_REPOSITORY##*/}" | tr '[:upper:]' '[:lower:]')

PACKAGE_URL="https://${REGISTRY}/api/packages/${OWNER}/maven"

export MAVEN_PACKAGE_URL="$PACKAGE_URL"
export MAVEN_USER="$USER"
export MAVEN_TOKEN="$TOKEN"

echo "Detected package repository: $PACKAGE_URL"

# Output for GitHub Actions
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "package_url=$PACKAGE_URL" >> "$GITHUB_OUTPUT"
fi

# -----------------------------
# Collect Maven coordinates
# -----------------------------

declare -a COORDS=()

# Function to extract coords from a module
get_coords() {
  local dir="$1"

  pushd "$dir" > /dev/null

  local G A V

  G=$(mvn help:evaluate -Dexpression=project.groupId -q -DforceStdout)
  A=$(mvn help:evaluate -Dexpression=project.artifactId -q -DforceStdout)
  V=$(mvn help:evaluate -Dexpression=project.version -q -DforceStdout)

  if [[ -n "$G" && -n "$A" && -n "$V" ]]; then
    COORDS+=("${G}:${A}:${V}")
  fi

  popd > /dev/null
}

# Root project
get_coords "."

# Detect modules (if any)
if grep -q "<modules>" pom.xml; then
  mapfile -t MODULES < <(xmllint --xpath "//modules/module/text()" pom.xml 2>/dev/null || true)

  for m in "${MODULES[@]}"; do
    if [[ -f "$m/pom.xml" ]]; then
      get_coords "$m"
    fi
  done
fi

if [[ ${#COORDS[@]} -eq 0 ]]; then
  echo "No Maven coordinates found"
  exit 1
fi

# -----------------------------
# De-duplicate
# -----------------------------

declare -A SEEN=()
declare -a UNIQUE_COORDS=()

for c in "${COORDS[@]}"; do
  if [[ -z "${SEEN[$c]+x}" ]]; then
    SEEN[$c]=1
    UNIQUE_COORDS+=("$c")
  fi
done

echo "Found ${#UNIQUE_COORDS[@]} artifact(s):"
printf ' - %s\n' "${UNIQUE_COORDS[@]}"

# -----------------------------
# Delete existing versions
# -----------------------------

for c in "${UNIQUE_COORDS[@]}"; do
  IFS=':' read -r G A V <<< "$c"

  DELETE_URL="https://${REGISTRY}/api/v1/packages/${OWNER}/maven/${G}:${A}/${V}"

  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X DELETE \
    -u "${USER}:${TOKEN}" \
    "$DELETE_URL")

  if [[ "$STATUS" != "204" && "$STATUS" != "404" ]]; then
    echo "Delete failed for ${G}:${A}:${V} (HTTP $STATUS)"
    exit 1
  fi
done

# -----------------------------
# Publish via Maven
# -----------------------------

mvn -B deploy \
  -Dmaven.test.skip=true \
  -DaltDeploymentRepository=registry::"${PACKAGE_URL}" \
  -Dusername="${USER}" \
  -Dpassword="${TOKEN}"

# -----------------------------
# Link artifacts
# -----------------------------

for c in "${UNIQUE_COORDS[@]}"; do
  IFS=':' read -r G A V <<< "$c"

  LINK_URL="https://${REGISTRY}/api/v1/packages/${OWNER}/maven/${G}:${A}/-/link/${REPO_NAME}"

  curl -s -o /dev/null \
    -X POST \
    -u "${USER}:${TOKEN}" \
    "$LINK_URL"
done

echo "Publish complete."