#!/bin/sh
# Launcher installed by the superwhisper RPM. Updates come from dnf, so the
# in-app updater is switched off (upstream's Nix package does the same).
export SUPERWHISPER_UPDATE_DISABLED=1
exec @APPDIR@/run.sh "$@"
