# Built from the release source archive of vintoware/grayjay-link. The upstream
# values below are rewritten by ./update from the latest GitHub release after it
# verifies the Sigstore-signed checksums.txt -- edit by hand only for packaging
# fixes (and bump Release when you do). grayjay-link's release workflow runs that
# hook and pushes the result, so new releases build right away.
%global src_sha256 b7bfeab71b5656f9c69ec465aad2c8f2cd27c24095b66f26c7b2296a9121d13a
%global commit 170010df4dc6df4fa638e5355e15a64f54b0400e

%global applet_id com.vintoware.grayjaylink

Name:           grayjay-link
Version:        0.2.0
Release:        1
Summary:        Open YouTube, Twitch and other links in Grayjay Desktop
License:        MIT
URL:            https://github.com/vintoware/grayjay-link
BuildArch:      noarch

Source0:        %{url}/releases/download/v%{version}/grayjay-link-%{version}.tar.gz

BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  coreutils
BuildRequires:  tar
BuildRequires:  gzip

Requires:       python3 >= 3.11
# The widget uses org.kde.plasma.* (incl. plasma5support) and org.kde.kirigami.
Requires:       plasma-workspace >= 6.0
Requires:       kf6-kirigami
# gdbus raises the Grayjay window through KWin.
Requires:       glib2
# Grayjay itself comes from Flathub (app.grayjay.Grayjay).
Recommends:     flatpak

%description
Opens YouTube, Twitch and other video links in Grayjay Desktop (the Flathub
app) instead of a browser tab. A small helper pairs with Grayjay like a phone
would and sends links through Grayjay's sync protocol ("Send to device"). It
runs while the "Grayjay Link" Plasma widget exists; the widget shows status,
pairs with Grayjay and sends links. A companion Firefox extension and
grayjay-link: URLs hand links to the helper.

%prep
%setup -q -c -T
echo "%{src_sha256}  %{SOURCE0}" | sha256sum -c -
tar -xzf %{SOURCE0} --strip-components=1

%build
# Pure Python; nothing to build.

%install
install -d %{buildroot}%{python3_sitelib}
cp -r grayjay_link %{buildroot}%{python3_sitelib}/
install -d %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/grayjay-link <<'EOF'
#!/bin/sh
exec /usr/bin/python3 -P -m grayjay_link "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/grayjay-link

install -d %{buildroot}%{_datadir}/plasma/plasmoids/%{applet_id}
cp -r plasmoid/. %{buildroot}%{_datadir}/plasma/plasmoids/%{applet_id}/
find %{buildroot}%{_datadir}/plasma/plasmoids/%{applet_id} -type d -exec chmod 0755 {} + \
  -o -type f -exec chmod 0644 {} +

install -Dm 0644 plasmoid/contents/icons/grayjay-link.svg \
  %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/grayjay-link.svg
sed 's|@BIN@|%{_bindir}/grayjay-link|' data/grayjay-link-handler.desktop.in > grayjay-link-handler.desktop
desktop-file-install --dir=%{buildroot}%{_datadir}/applications grayjay-link-handler.desktop

%check
python3 -m unittest
desktop-file-validate %{buildroot}%{_datadir}/applications/grayjay-link-handler.desktop
PYTHONPATH=%{buildroot}%{python3_sitelib} python3 -P -m grayjay_link --version | grep -F %{version}

%files
%license LICENSE
%doc README.md CHANGELOG.md CONTRIBUTING.md
%{_bindir}/grayjay-link
%{python3_sitelib}/grayjay_link/
%{_datadir}/plasma/plasmoids/%{applet_id}/
%{_datadir}/icons/hicolor/scalable/apps/grayjay-link.svg
%{_datadir}/applications/grayjay-link-handler.desktop

%changelog
* Mon Nov 23 2026 vintoware-rpm bot <noreply@github.com> - 0.2.0-1
- Update to 0.2.0
- Release notes: https://github.com/vintoware/grayjay-link/releases/tag/v0.2.0

* Mon Nov 23 2026 vintoware-rpm bot <noreply@github.com> - 0.0.0-1
- Initial package (placeholder; ./update sets the first real release)
