#!/usr/bin/env bash
# Assemble the dnf repository published on GitHub Pages.
#
#   build-site.sh <site-dir> <rpm-dir> <base-url>
#
# <rpm-dir> holds the RPMs to publish (any layout); they are sorted into
# <site-dir>/<arch>/, indexed with createrepo_c, and repomd.xml is signed with
# the key whose fingerprint is in $GPG_FINGERPRINT (already imported).
set -euo pipefail

site=$1 rpms=$2 base_url=${3%/}
: "${GPG_FINGERPRINT:?GPG_FINGERPRINT must be set}"

rm -rf "$site"
mkdir -p "$site"
shopt -s nullglob globstar
found=0
for rpm in "$rpms"/**/*.rpm; do
  arch=$(rpm -qp --qf '%{ARCH}' "$rpm" 2>/dev/null)
  case "$arch" in x86_64|aarch64) ;; *) echo "skipping $rpm ($arch)" >&2; continue ;; esac
  mkdir -p "$site/$arch"
  cp "$rpm" "$site/$arch/"
  found=$((found + 1))
done
((found)) || { echo "no RPMs found in $rpms" >&2; exit 1; }

for dir in "$site"/*/; do
  createrepo_c --quiet --general-compress-type=zstd "$dir"
  gpg --batch --yes --local-user "$GPG_FINGERPRINT" --detach-sign --armor "$dir/repodata/repomd.xml"
done

gpg --batch --armor --export "$GPG_FINGERPRINT" > "$site/RPM-GPG-KEY-vintoware-rpm"

cat > "$site/vintoware.repo" <<EOF
[vintoware]
name=vintoware RPM packages
baseurl=$base_url/\$basearch/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=$base_url/RPM-GPG-KEY-vintoware-rpm
metadata_expire=6h
EOF

{
  echo '<!doctype html><meta charset="utf-8"><title>vintoware RPM repository</title>'
  echo '<h1>vintoware RPM repository</h1>'
  echo '<pre>sudo dnf config-manager addrepo --from-repofile='"$base_url"'/vintoware.repo'
  echo 'sudo dnf install &lt;package&gt;</pre>'
  echo '<ul>'
  for rpm in "$site"/*/*.rpm; do
    rel=${rpm#"$site"/}
    echo "<li><a href=\"$rel\">$rel</a></li>"
  done
  echo '</ul>'
} > "$site/index.html"
touch "$site/.nojekyll"
echo "site ready: $found RPMs"
