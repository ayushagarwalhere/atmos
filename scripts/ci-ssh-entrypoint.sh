#!/usr/bin/env bash
set -Eeuo pipefail

# Install a root-owned copy at /usr/local/bin/atmos-ci-deploy and use it
# as the forced command for the dedicated GitHub Actions SSH key.
revision="${SSH_ORIGINAL_COMMAND:-}"
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || { echo "Expected a Git commit SHA" >&2; exit 1; }
mkdir -p "$HOME/atmos"
exec 8>"$HOME/atmos/.ci-repo.lock"
flock -w 1800 8
cd "$HOME/atmos"
if [ ! -d repo/.git ]; then
  git clone https://github.com/ayushagarwalhere/atmos.git repo
fi
cd repo
git fetch origin main
git merge-base --is-ancestor "$revision" origin/main || {
  echo "Only commits from the repository's main branch can be deployed." >&2
  exit 1
}
git checkout --detach "$revision"
bash scripts/deploy-ec2.sh "$revision"
