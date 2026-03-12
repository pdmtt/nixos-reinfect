#!/usr/bin/env bash
# chmod +x tests/scripts/cleanup-orphans.sh
#
# Safety-net script that destroys VMs tagged as nixos-infect-test that are
# older than 2 hours. Run on a schedule to catch any leaked resources.
#
# Required env vars (per provider):
#   HCLOUD_TOKEN        - Hetzner Cloud API token
#   DIGITALOCEAN_TOKEN  - DigitalOcean personal access token
#
set -euo pipefail

MAX_AGE_HOURS=2

# Returns 1 if the ISO 8601 timestamp is older than MAX_AGE_HOURS, 0 otherwise
is_older_than_max_age() {
  local created_at="$1"
  local created_epoch
  created_epoch=$(date -d "$created_at" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$created_at" +%s 2>/dev/null || echo "0")
  local now_epoch
  now_epoch=$(date +%s)
  local age_hours=$(( (now_epoch - created_epoch) / 3600 ))
  [ "$age_hours" -ge "$MAX_AGE_HOURS" ]
}

cleanup_hetzner() {
  if [ -z "${HCLOUD_TOKEN:-}" ]; then
    echo "[hetzner] Skipping: HCLOUD_TOKEN not set"
    return
  fi

  echo "[hetzner] Checking for orphaned servers..."

  local servers
  servers=$(hcloud server list -o json 2>/dev/null) || {
    echo "[hetzner] Failed to list servers"
    return
  }

  echo "$servers" | jq -c '.[] | select(.labels.purpose == "nixos-infect-test")' | while read -r server; do
    local id name created
    id=$(echo "$server" | jq -r '.id')
    name=$(echo "$server" | jq -r '.name')
    created=$(echo "$server" | jq -r '.created')

    if is_older_than_max_age "$created"; then
      echo "[hetzner] Deleting orphan: $name (id=$id, created=$created)"
      hcloud server delete "$id" && echo "[hetzner] Deleted $name" || echo "[hetzner] Failed to delete $name"
    else
      echo "[hetzner] Skipping recent server: $name (created=$created)"
    fi
  done
}

cleanup_digitalocean() {
  if [ -z "${DIGITALOCEAN_TOKEN:-}" ]; then
    echo "[digitalocean] Skipping: DIGITALOCEAN_TOKEN not set"
    return
  fi

  echo "[digitalocean] Checking for orphaned droplets..."

  local response
  response=$(curl -sSf \
    -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
    "https://api.digitalocean.com/v2/droplets?tag_name=nixos-infect-test&per_page=100") || {
    echo "[digitalocean] Failed to list droplets"
    return
  }

  echo "$response" | jq -c '.droplets[]' | while read -r droplet; do
    local id name created
    id=$(echo "$droplet" | jq -r '.id')
    name=$(echo "$droplet" | jq -r '.name')
    created=$(echo "$droplet" | jq -r '.created_at')

    if is_older_than_max_age "$created"; then
      echo "[digitalocean] Deleting orphan: $name (id=$id, created=$created)"
      curl -sSf -X DELETE \
        -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
        "https://api.digitalocean.com/v2/droplets/$id" \
        && echo "[digitalocean] Deleted $name" \
        || echo "[digitalocean] Failed to delete $name"
    else
      echo "[digitalocean] Skipping recent droplet: $name (created=$created)"
    fi
  done
}

echo "==> Starting orphan VM cleanup (max age: ${MAX_AGE_HOURS}h)"
cleanup_hetzner
cleanup_digitalocean
echo "==> Cleanup complete"
