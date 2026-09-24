#!/usr/bin/env bash

set -euo pipefail

###############################################################################
# Configuration
###############################################################################

: "${FORGEJO_TOKEN:?FORGEJO_TOKEN is required}"
: "${INACTIVE_DAYS:?INACTIVE_DAYS is required}"
: "${FORGEJO_API_URL:?FORGEJO_API_URL is required}"
: "${FORGEJO_REPOSITORY:?FORGEJO_REPOSITORY is required}"

PROCESS_ISSUES="${PROCESS_ISSUES:-true}"
PROCESS_PULL_REQUESTS="${PROCESS_PULL_REQUESTS:-true}"
EXCLUDE_LABELS="${EXCLUDE_LABELS:-}"
INCLUDE_DRAFTS="${INCLUDE_DRAFTS:-false}"
LOCK_COMMENT="${LOCK_COMMENT:-}"
DRY_RUN="${DRY_RUN:-false}"

# Internal API page size.
# Deliberately not exposed as an action input.
PAGE_SIZE=50

###############################################################################
# Validation
###############################################################################

if ! [[ "$INACTIVE_DAYS" =~ ^[0-9]+$ ]]; then
    echo "::error::days must be a non-negative integer"
    exit 1
fi

###############################################################################
# Repository
###############################################################################

OWNER="${FORGEJO_REPOSITORY%%/*}"
REPO="${FORGEJO_REPOSITORY#*/}"

if [ -z "$OWNER" ] || [ -z "$REPO" ] || [ "$OWNER" = "$REPO" ]; then
    echo "::error::Invalid repository: ${FORGEJO_REPOSITORY}"
    exit 1
fi

###############################################################################
# API helpers
###############################################################################

AUTH_HEADER="Authorization: token ${FORGEJO_TOKEN}"

api_get() {
    local url="$1"

    curl \
        --fail \
        --silent \
        --show-error \
        --location \
        --header "$AUTH_HEADER" \
        --header "Accept: application/json" \
        "$url"
}

api_post_json() {
    local url="$1"
    local body="$2"

    curl \
        --fail \
        --silent \
        --show-error \
        --location \
        --request POST \
        --header "$AUTH_HEADER" \
        --header "Accept: application/json" \
        --header "Content-Type: application/json" \
        --data "$body" \
        "$url"
}

api_put() {
    local url="$1"

    curl \
        --fail \
        --silent \
        --show-error \
        --location \
        --request PUT \
        --header "$AUTH_HEADER" \
        --header "Accept: application/json" \
        "$url"
}

###############################################################################
# Cutoff time
###############################################################################

CUTOFF_TIMESTAMP="$(
    date -u \
        -d "${INACTIVE_DAYS} days ago" \
        +%s
)"

CUTOFF_ISO="$(
    date -u \
        -d "@${CUTOFF_TIMESTAMP}" \
        +"%Y-%m-%dT%H:%M:%SZ"
)"

###############################################################################
# Logging
###############################################################################

echo "============================================================"
echo "Forgejo Lock Inactive Conversations"
echo "============================================================"
echo "Repository      : ${OWNER}/${REPO}"
echo "Inactive days   : ${INACTIVE_DAYS}"
echo "Cutoff          : ${CUTOFF_ISO}"
echo "Issues          : ${PROCESS_ISSUES}"
echo "Pull requests   : ${PROCESS_PULL_REQUESTS}"
echo "Include drafts  : ${INCLUDE_DRAFTS}"
echo "Excluded labels : ${EXCLUDE_LABELS:-<none>}"
echo "Dry run         : ${DRY_RUN}"
echo "Page size       : ${PAGE_SIZE}"
echo "============================================================"

###############################################################################
# Label handling
###############################################################################

has_excluded_label() {
    local labels_json="$1"

    if [ -z "$EXCLUDE_LABELS" ]; then
        return 1
    fi

    IFS=',' read -ra LABELS <<< "$EXCLUDE_LABELS"

    for excluded in "${LABELS[@]}"; do
        excluded="$(echo "$excluded" | xargs)"

        [ -z "$excluded" ] && continue

        if echo "$labels_json" |
            jq -e \
                --arg label "$excluded" \
                '.[] | select(.name == $label)' \
                >/dev/null; then
            return 0
        fi
    done

    return 1
}

###############################################################################
# Determine whether an item is a pull request
###############################################################################

is_pull_request() {
    local item="$1"

    echo "$item" |
        jq -e '.pull_request != null' \
        >/dev/null
}

###############################################################################
# Determine latest activity
###############################################################################

get_latest_activity() {
    local number="$1"
    local issue_updated="$2"

    # Forgejo's issue updated_at represents the latest issue/PR update.
    #
    # This is used as the inactivity timestamp instead of creation time.
    #
    # Keeping this function separate allows the activity calculation to be
    # expanded later without changing the rest of the action.
    echo "$issue_updated"
}

###############################################################################
# Lock conversation
###############################################################################

lock_conversation() {
    local number="$1"

    if [ "$DRY_RUN" = "true" ]; then
        echo "::notice::DRY RUN: would lock #${number}"
        return 0
    fi

    ###########################################################################
    # Comment
    ###########################################################################

    if [ -n "$LOCK_COMMENT" ]; then

        COMMENT_JSON="$(
            jq -n \
                --arg body "$LOCK_COMMENT" \
                '{body: $body}'
        )"

        echo "Posting lock comment to #${number}"

        api_post_json \
            "${FORGEJO_API_URL}/repos/${OWNER}/${REPO}/issues/${number}/comments" \
            "$COMMENT_JSON" \
            >/dev/null
    fi

    ###########################################################################
    # Lock
    ###########################################################################

    echo "Locking #${number}"

    api_put \
        "${FORGEJO_API_URL}/repos/${OWNER}/${REPO}/issues/${number}/lock" \
        >/dev/null

    echo "::notice::Locked #${number}"
}

###############################################################################
# Process one issue / pull request
###############################################################################

process_item() {
    local item="$1"

    local number
    local title
    local updated
    local locked
    local labels
    local latest_activity
    local latest_timestamp

    number="$(echo "$item" | jq -r '.number')"
    title="$(echo "$item" | jq -r '.title')"
    updated="$(echo "$item" | jq -r '.updated_at')"
    locked="$(echo "$item" | jq -r '.locked')"
    labels="$(echo "$item" | jq -c '.labels // []')"

    echo
    echo "------------------------------------------------------------"
    echo "#${number}: ${title}"
    echo "Updated: ${updated}"

    ###########################################################################
    # Already locked
    ###########################################################################

    if [ "$locked" = "true" ]; then
        echo "Skipping: already locked"
        return
    fi

    ###########################################################################
    # Draft PR
    ###########################################################################

    if is_pull_request "$item"; then

        local draft

        draft="$(echo "$item" | jq -r '.draft // false')"

        if [ "$draft" = "true" ] &&
            [ "$INCLUDE_DRAFTS" != "true" ]; then

            echo "Skipping: draft pull request"
            return
        fi
    fi

    ###########################################################################
    # Excluded labels
    ###########################################################################

    if has_excluded_label "$labels"; then
        echo "Skipping: excluded label"
        return
    fi

    ###########################################################################
    # Activity
    ###########################################################################

    latest_activity="$(
        get_latest_activity \
            "$number" \
            "$updated"
    )"

    latest_timestamp="$(
        date -u \
            -d "$latest_activity" \
            +%s
    )"

    ###########################################################################
    # Still active
    ###########################################################################

    if [ "$latest_timestamp" -ge "$CUTOFF_TIMESTAMP" ]; then
        echo "Skipping: still active"
        return
    fi

    ###########################################################################
    # Inactive
    ###########################################################################

    echo "Inactive since: ${latest_activity}"

    lock_conversation "$number"
}

###############################################################################
# Process API pages
###############################################################################

process_pages() {

    local page=1

    while true; do

        echo
        echo "Fetching page ${page}"

        RESPONSE="$(
            api_get \
                "${FORGEJO_API_URL}/repos/${OWNER}/${REPO}/issues?state=open&type=all&limit=${PAGE_SIZE}&page=${page}"
        )"

        COUNT="$(echo "$RESPONSE" | jq 'length')"

        if [ "$COUNT" -eq 0 ]; then
            break
        fi

        echo "Found ${COUNT} conversations"

        while IFS= read -r item; do

            ###################################################################
            # Issues
            ###################################################################

            if is_pull_request "$item"; then

                if [ "$PROCESS_PULL_REQUESTS" != "true" ]; then
                    continue
                fi

            ###################################################################
            # Issues
            ###################################################################

            else

                if [ "$PROCESS_ISSUES" != "true" ]; then
                    continue
                fi

            fi

            process_item "$item"

        done < <(
            echo "$RESPONSE" |
                jq -c '.[]'
        )

        #######################################################################
        # Last page
        #######################################################################

        if [ "$COUNT" -lt "$PAGE_SIZE" ]; then
            break
        fi

        page=$((page + 1))
    done
}

###############################################################################
# Run
###############################################################################

process_pages

echo
echo "============================================================"
echo "Completed"
echo "============================================================"