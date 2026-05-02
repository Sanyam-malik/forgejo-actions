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

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "package_url=$PACKAGE_URL" >> "$GITHUB_OUTPUT"
fi

# -----------------------------
# Create temporary Gradle init script
# -----------------------------
INIT_SCRIPT=$(mktemp)

cat > "$INIT_SCRIPT" <<'EOF'
allprojects {
  afterEvaluate { project ->
    if (project.extensions.findByName("publishing")) {
      def publishing = project.extensions.getByName("publishing")
      publishing.publications.withType(org.gradle.api.publish.maven.MavenPublication).all { pub ->
        if (pub.groupId && pub.artifactId && pub.version) {
          println("COORD=" + pub.groupId + ":" + pub.artifactId + ":" + pub.version)
        }
      }
    }
  }
}
EOF

# -----------------------------
# Collect coordinates
# -----------------------------
declare -a COORDS=()

while IFS= read -r line; do
  if [[ "$line" == COORD=* ]]; then
    COORDS+=("${line#COORD=}")
  fi
done < <(gradle -q help --init-script "$INIT_SCRIPT")

rm -f "$INIT_SCRIPT"

if [[ ${#COORDS[@]} -eq 0 ]]; then
  echo "No publishable Maven publications found"
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
# Publish
# -----------------------------
gradle publish

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