#!/bin/bash
# Ship the three TypoGram images from the ShapitoGram box to the new VPS.
set -uo pipefail
TARGET=root@177.3.222.2
PASS=eazy_game14
IMAGES="ghcr.io/iamxvbaba/gramsrv/server:main ghcr.io/iamxvbaba/gramsrv/admin:main shapitogram-store:local"

echo "start $(date -u)"
docker save $IMAGES | gzip -1 | \
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "$TARGET" 'gunzip | docker load'
echo "rc=$? $(date -u)"
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  "$TARGET" 'docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | grep -E "gramsrv|shapito"'
echo "done $(date -u)"
