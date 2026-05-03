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
# Merge into ~/.m2/settings.xml
# -----------------------------
M2_SETTINGS="${HOME}/.m2/settings.xml"
mkdir -p "${HOME}/.m2"

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

  # Remove existing registry server (avoid duplicates)
  awk '
    BEGIN {skip=0}
    /<server>/ {block=""}
    {
      block = block $0 "\n"
    }
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
    !skip && !/<server>/ && !/<\/server>/ {
      print
    }
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

# Root project
get_coords "."

# Modules
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
# Build first (IMPORTANT)
# -----------------------------
mvn -B clean package -Dmaven.test.skip=true

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
mvn -B deploy \
  -Dmaven.test.skip=true \
  -DaltDeploymentRepository=registry::"${PACKAGE_URL}"

# -----------------------------
# Link artifacts to repo
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