# Built from upstream's release source archive (GoReleaser's clankerwatch.src.tar.gz).
# The upstream values below are rewritten by ./update from the latest GitHub release
# after it verifies the Sigstore-signed checksums.txt -- edit by hand only for
# packaging fixes (and bump Release when you do).
%global src_sha256 5b6b88d700ffd053861c420d90a74aed4a8f790f296012880dee9d10a2f77d06
%global commit 4b2e077ae209d698e7c1cf28d811d5bdfc67b5fc

%global goipath github.com/nicholas-fedor/clankerwatch
%global bus_name com.nickfedor.ClankerWatch1
%global applet_id com.nickfedor.clankerwatch

# Don't clamp file mtimes to the changelog date. Qt's QML disk cache treats a
# source file as unchanged when its mtime is unchanged, so two releases built on
# the same day would leave plasmashell running the previous widget's cached QML.
%global clamp_mtime_to_source_date_epoch 0

# Static Go binary stripped like upstream's (-s -w): nothing for debuginfo.
%global debug_package %{nil}

Name:           clankerwatch
Version:        0.1.4
Release:        1
Summary:        Claude Code usage monitor in the KDE Plasma panel
License:        AGPL-3.0-or-later
URL:            https://github.com/nicholas-fedor/clankerwatch
ExclusiveArch:  x86_64 aarch64

Source0:        %{url}/releases/download/v%{version}/clankerwatch.src.tar.gz#/clankerwatch-%{version}.src.tar.gz

BuildRequires:  golang >= 1.27
BuildRequires:  coreutils
BuildRequires:  tar
BuildRequires:  gzip
BuildRequires:  systemd-rpm-macros

# The widget imports org.kde.plasma.*, org.kde.kirigami and org.kde.kcmutils,
# and upstream requires Plasma 6.4 or later.
Requires:       plasma-workspace >= 6.4
Requires:       kf6-kirigami
Requires:       kf6-kcmutils
Requires:       dbus-common
%{?systemd_requires}

%description
Clanker Watch is a KDE Plasma 6 widget that shows Claude Code subscription
usage limits in the panel, with a popup listing every limit, its reset time
and extra usage. A small Go daemon, started on demand through D-Bus
activation, reads Claude Code's login read-only and polls Anthropic's usage
endpoint at most every 5 minutes.

%prep
%setup -q -c -T
echo "%{src_sha256}  %{SOURCE0}" | sha256sum -c -
tar -xzf %{SOURCE0}

%build
# Modules come from the Go proxy and are checked against go.sum and the
# checksum database. GOTOOLCHAIN=auto fetches a newer Go (also checksum-verified)
# only if go.mod ever asks for more than Fedora ships.
export CGO_ENABLED=0 GOTOOLCHAIN=auto GOFLAGS=-mod=readonly
export GOPROXY=https://proxy.golang.org GOSUMDB=sum.golang.org
export GOPATH=$PWD/.gopath GOCACHE=$PWD/.gocache
build_time=$(date -u -d "@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y-%m-%dT%H:%M:%SZ)
go build -trimpath -o clankerwatch -ldflags "-s -w -B gobuildid \
  -X %{goipath}/internal/version.Version=%{version} \
  -X %{goipath}/internal/version.CommitSHA=%{commit} \
  -X %{goipath}/internal/version.BuildTime=$build_time" .

%install
install -Dm 0755 clankerwatch %{buildroot}%{_bindir}/clankerwatch
install -Dm 0644 build/package/systemd/clankerwatch.service %{buildroot}%{_userunitdir}/clankerwatch.service
install -Dm 0644 build/package/dbus/%{bus_name}.service %{buildroot}%{_datadir}/dbus-1/services/%{bus_name}.service
install -d %{buildroot}%{_datadir}/plasma/plasmoids/%{applet_id}
cp -r plasmoid/. %{buildroot}%{_datadir}/plasma/plasmoids/%{applet_id}/
find %{buildroot}%{_datadir}/plasma/plasmoids/%{applet_id} -type d -exec chmod 0755 {} + \
  -o -type f -exec chmod 0644 {} +

%check
export CGO_ENABLED=0 GOTOOLCHAIN=auto GOFLAGS=-mod=readonly
export GOPROXY=https://proxy.golang.org GOSUMDB=sum.golang.org
export GOPATH=$PWD/.gopath GOCACHE=$PWD/.gocache
# No session bus in the build container: keep tests from reaching one.
export DBUS_SESSION_BUS_ADDRESS=unix:path=/nonexistent
# The skipped tests make a directory read-only and expect writes to fail,
# which never happens when the build runs as root (as in CI containers).
go test -count=1 -skip '^(TestApplyReportsAFailedRestore|TestApplyReportsFileErrors)$' \
  $(go list ./... | grep -v /mocks$)
./clankerwatch version | grep -F %{version}

%post
%systemd_user_post clankerwatch.service

%preun
%systemd_user_preun clankerwatch.service

%postun
%systemd_user_postun_with_restart clankerwatch.service

%files
%license LICENSE.md
%doc README.md CHANGELOG.md build/package/config.example.yaml
%{_bindir}/clankerwatch
%{_userunitdir}/clankerwatch.service
%{_datadir}/dbus-1/services/%{bus_name}.service
%{_datadir}/plasma/plasmoids/%{applet_id}

%changelog
* Mon Nov 23 2026 vintoware-rpm bot <noreply@github.com> - 0.1.4-1
- Initial package of clankerwatch 0.1.4
- Release notes: https://github.com/nicholas-fedor/clankerwatch/releases/tag/v0.1.4
