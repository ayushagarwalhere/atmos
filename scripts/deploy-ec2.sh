#!/usr/bin/env bash
set -Eeuo pipefail

revision="${1:?Pass the Git commit SHA to deploy}"
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid Git revision" >&2; exit 1; }
deploy_root="${ATMOS_DEPLOY_ROOT:-$HOME/atmos}"
env_file="$deploy_root/atmos.env"
image="atmos:$revision"
candidate="atmos-candidate-${revision:0:12}"
switched=false
had_previous=false

mkdir -p "$deploy_root"
exec 9>"$deploy_root/.deploy.lock"
flock -w 1800 9
sudo -n test -f "$env_file"

cleanup() {
  status=$?
  trap - EXIT
  sudo -n docker rm -f "$candidate" >/dev/null 2>&1 || true
  if [ "$status" -ne 0 ] && [ "$switched" = true ]; then
    sudo -n docker rm -f atmos >/dev/null 2>&1 || true
    if [ "$had_previous" = true ]; then
      sudo -n docker rename atmos-previous atmos
      sudo -n docker start atmos >/dev/null
      echo "Deployment failed; the previous container has been restored." >&2
    fi
  fi
  exit "$status"
}
trap cleanup EXIT

wait_for_health() {
  local url="$1"
  for attempt in $(seq 1 30); do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

echo "Building Atmos revision $revision"
sudo -n docker build --label "org.opencontainers.image.revision=$revision" --tag "$image" .

# Check startup against disposable storage before stopping the live container.
sudo -n docker run -d --name "$candidate" --env-file "$env_file" \
  -e ATMOS_DATA_DIR=/tmp/atmos-smoke -e ATMOS_DISABLE_SCHEDULER=true \
  -p 127.0.0.1:8001:8000 "$image" >/dev/null
if ! wait_for_health http://127.0.0.1:8001/api/health; then
  sudo -n docker logs --tail 60 "$candidate" >&2
  exit 1
fi
sudo -n docker rm -f "$candidate" >/dev/null

sudo -n docker volume create atmos-data >/dev/null
sudo -n docker run --rm --user 0 -v atmos-data:/app/data "$image" \
  chown 10001:10001 /app/data

# Keep the stopped previous container available for automatic rollback.
if sudo -n docker inspect atmos-previous >/dev/null 2>&1; then
  if [ "$(sudo -n docker inspect --format '{{.State.Running}}' atmos-previous)" = true ]; then
    echo "A previous deployment container is still running; inspect it before deploying." >&2
    exit 1
  fi
  sudo -n docker rm atmos-previous >/dev/null
fi
if sudo -n docker inspect atmos >/dev/null 2>&1; then
  sudo -n docker stop --time 30 atmos >/dev/null
  sudo -n docker rename atmos atmos-previous
  had_previous=true
fi
switched=true
sudo -n docker run -d --name atmos --restart unless-stopped \
  --env-file "$env_file" -p 127.0.0.1:8000:8000 \
  -e ATMOS_HOSTING=ec2 -e ATMOS_HOSTING_REGION="${ATMOS_HOSTING_REGION:-eu-north-1}" \
  -v atmos-data:/app/data "$image" >/dev/null
if ! wait_for_health http://127.0.0.1:8000/api/health; then
  sudo -n docker logs --tail 60 atmos >&2
  exit 1
fi
curl --fail --silent --show-error --max-time 15 http://127.0.0.1/ >/dev/null
sudo -n docker tag "$image" atmos:latest
printf '%s\n' "$revision" > "$deploy_root/deployed-revision"
switched=false
echo "Atmos revision $revision is live."
