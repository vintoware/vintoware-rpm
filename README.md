# vintoware-rpm

A personal dnf repository for Fedora (x86_64 and aarch64). GitHub Actions builds signed
RPMs, then publishes them on GitHub Pages at <https://vintoware.github.io/vintoware-rpm/>.

| Package | Upstream | Updates |
|---|---|---|
| `superwhisper` | [Superwhisper for Linux](https://superwhisper.com) (unofficial repackage of the release archive) | automatic, from `https://tux.superwhisper.com/stable.json` |

## Install

```sh
sudo dnf config-manager addrepo --from-repofile=https://vintoware.github.io/vintoware-rpm/vintoware.repo
sudo dnf install superwhisper
```

Packages and repository metadata are GPG-signed (`gpgcheck=1`, `repo_gpgcheck=1`), and
dnf asks you to confirm the key on first use. After that, `sudo dnf upgrade` picks up new
versions.

## How it works

`.github/workflows/build.yml` runs every 3 hours, on every push to `main`, and on demand:

1. **check**: runs every `packages/<name>/update` hook. A hook bumps its spec when
   upstream has a newer version. If a hook changes anything, the job commits the change.
   `scripts/plan.py` then lists each package whose `<name>/<version>-<release>` has no
   GitHub release yet.
2. **build**: one job per package and architecture, in a `fedora:latest` container on
   native x86_64 and arm64 runners: `dnf builddep`, `spectool -g`, `rpmbuild -bb`,
   `rpmsign`.
3. **publish**: creates a GitHub release `<name>/<evr>` holding the RPMs. Then it
   collects the newest 3 releases of every package (older versions stay available for
   `dnf downgrade`), runs `createrepo_c`, signs `repomd.xml`, and deploys the site to
   GitHub Pages.

Manual runs (**Actions → Update, build and publish → Run workflow**) accept `force`, a
package directory to rebuild even though its version is already released, and
`republish`, which rebuilds the site without building anything.

## Adding a package

Create `packages/<name>/` containing:

- `<name>.spec`. It can use remote `SourceN:` URLs, which are fetched with `spectool`.
  Local sources sit next to the spec. Builds run on x86_64 and aarch64 unless the spec
  sets `ExclusiveArch`. `BuildArch: noarch` builds once.
- optionally, an executable `update` that rewrites the spec when upstream has a new
  version. It must exit non-zero if it can't verify what it downloaded. See
  `packages/superwhisper/update`.

To ship a packaging-only change, bump `Release:` and push.

## superwhisper notes

- Installs to `/usr/lib64/superwhisper`, with `/usr/bin/superwhisper` as a wrapper. The
  in-app updater is disabled (`SUPERWHISPER_UPDATE_DISABLED=1`, as in upstream's own Nix
  package), so updates arrive only through dnf.
- `superwhisper.service` (a systemd user unit) is enabled for all users through a preset
  and starts with the graphical session. After a dnf upgrade, running instances restart.
  To opt out, run `systemctl --user disable superwhisper.service`.
- **If you used upstream's `curl … | sh` installer before**, run
  `~/.local/share/superwhisper/app/current/uninstall.sh` first. Its unit in
  `~/.config/systemd/user` would otherwise override the packaged one. Your settings,
  history and models are kept.
- GNOME: the Shell extension is installed system-wide. Enable it once with
  `gnome-extensions enable superwhisper@superwhisper.com`, then log out and back in.
- Hyprland: the app writes shortcut bindings that point at `~/.local/bin/superwhisper`.
  Run `ln -s /usr/bin/superwhisper ~/.local/bin/superwhisper` to make them work.
- `update` checks each new archive's size, its SHA-256 from the channel metadata, and its
  minisign signature against the pinned upstream key
  (`packages/superwhisper/superwhisper-release.pub`), all before it commits a bump. The
  build checks the SHA-256 again.

Superwhisper itself is proprietary software by Super Ultra, Inc. This repository holds
only the packaging, under the MIT license below.

## Maintenance

- The signing key lives only in the `GPG_PRIVATE_KEY` repository secret, and its
  fingerprint in the `GPG_FINGERPRINT` repository variable. To rotate it, generate a new
  key, update both, and run the workflow with `republish`. Users then re-import the key.
- GitHub turns off scheduled workflows in repositories with no activity for 60 days. If
  that happens, re-enable the workflow from the Actions tab.
