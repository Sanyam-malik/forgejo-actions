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

# GitHub Actions output
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "package_url=$PACKAGE_URL" >> "$GITHUB_OUTPUT"
fi

# -----------------------------
# Use local Maven config (avoid /root issues)
# -----------------------------
M2_DIR="$(pwd)/.m2"
mkdir -p "$M2_DIR"
export MAVEN_CONFIG="$M2_DIR"
M2_SETTINGS="$M2_DIR/settings.xml"

echo "Using Maven config at: $M2_DIR"

# -----------------------------
# Detect project settings.xml
# -----------------------------
PROJECT_SETTINGS=""

if [[ -f "./settings.xml" ]]; then
  PROJECT_SETTINGS="./settings.xml"
elif [[ -f "./.mvn/settings.xml" ]]; then
  PROJECT_SETTINGS="./.mvn/settings.xml"
fi

# -----------------------------
# Copy project settings if exists
# -----------------------------
if [[ -n "$PROJECT_SETTINGS" ]]; then
  echo "Using project settings from: $PROJECT_SETTINGS"
  cp "$PROJECT_SETTINGS" "$M2_SETTINGS"
fi

# -----------------------------
# Merge server credentials
# -----------------------------
if [[ ! -f "$M2_SETTINGS" ]]; then
  cat > "$M2_SETTINGS" <<EOF
<settings>
  <servers>
    <server>
      <id>registry</id>
      <username>${MAVEN_USER}</username>
      <password>${MAVEN_TOKEN}</password>
    </server>
  </servers>
</settings>
EOF
else
  # Ensure <servers> exists
  if ! grep -q "<servers>" "$M2_SETTINGS"; then
    sed -i 's|</settings>|  <servers>\n  </servers>\n</settings>|' "$M2_SETTINGS"
  fi

  # Remove existing registry server
  awk '
    BEGIN {skip=0}
    /<server>/ {block=""}
    { block = block $0 "\n" }
    /<\/server>/ {
      if (block ~ /<id>registry<\/id>/) {
        skip=1
      } else {
        printf "%s", block
      }
      block=""
      skip=0
      next
    }
    !skip && !/<server>/ && !/<\/server>/ { print }
  ' "$M2_SETTINGS" > "${M2_SETTINGS}.tmp" || cp "$M2_SETTINGS" "${M2_SETTINGS}.tmp"

  mv "${M2_SETTINGS}.tmp" "$M2_SETTINGS"

  # Inject new server
  sed -i "s|</servers>|  <server>\n    <id>registry</id>\n    <username>${MAVEN_USER}</username>\n    <password>${MAVEN_TOKEN}</password>\n  </server>\n</servers>|" "$M2_SETTINGS"
fi

# -----------------------------
# Collect Maven coordinates
# -----------------------------
declare -a COORDS=()

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

get_coords "."

if grep -q "<modules>" pom.xml; then
  mapfile -t MODULES < <(xmllint --xpath "//modules/module/text()" pom.xml 2>/dev/null || true)
  for m in "${MODULES[@]}"; do
    [[ -f "$m/pom.xml" ]] && get_coords "$m"
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
# Build first
# -----------------------------
mvn -q -s "$M2_SETTINGS" dependency:go-offline

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
# Deploy
# -----------------------------
mvn -s "$M2_SETTINGS" -B deploy \
  -Dmaven.test.skip=true \
  -DaltDeploymentRepository=registry::default::"${PACKAGE_URL}"

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