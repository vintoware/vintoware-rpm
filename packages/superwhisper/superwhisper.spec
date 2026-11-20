# Unofficial repackage of the Superwhisper for Linux release archive.
# The upstream values below are rewritten by scripts/check-update.py from
# https://tux.superwhisper.com/stable.json -- edit by hand only for packaging fixes
# (and bump Release when you do).
%global sw_version 1.3.1
%global url_x86_64 https://tux.superwhisper.com/x86_64/v1.3.1/superwhisper-omarchy-x86_64-1.3.1.tar.zst
%global sha256_x86_64 464a732ca6c928d3f2b8bb94687176a75ca2b09c186333d34d94d051ccb5f0e4
%global url_aarch64 https://tux.superwhisper.com/aarch64/v1.3.1/superwhisper-omarchy-aarch64-1.3.1.tar.zst
%global sha256_aarch64 a440c85ea31bdb0c3c3b3de971a042402cc698efa27c54dc573c9553fd28f06f

%global appdir %{_libdir}/superwhisper
%global gnome_uuid superwhisper@superwhisper.com

# Prebuilt upstream binaries: no debuginfo, no stripping, no build-id links
# (they would collide with other packages shipping the same libraries).
%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none

# The bundled onnxruntime is private to the app. The fcitx5 addon links fcitx5's
# own libraries, which fcitx5 provides when it loads the addon.
%global __provides_exclude_from ^%{appdir}/.*$
%global __requires_exclude ^(libonnxruntime|libFcitx5Core|libFcitx5Utils)\\.so.*$

Name:           superwhisper
Version:        %{sw_version}
Release:        2
Summary:        Fast local and cloud dictation (unofficial repackage)
License:        LicenseRef-Proprietary
URL:            https://superwhisper.com
ExclusiveArch:  x86_64 aarch64

%ifarch x86_64
Source0:        %{url_x86_64}
%global src_sha256 %{sha256_x86_64}
%endif
%ifarch aarch64
Source0:        %{url_aarch64}
%global src_sha256 %{sha256_aarch64}
%endif
Source1:        superwhisper.sh
Source2:        superwhisper.service
Source3:        80-superwhisper.preset
Source4:        com.superwhisper.Superwhisper.desktop
Source5:        superwhisper-url.desktop
Source6:        uninstall.sh

BuildRequires:  coreutils
BuildRequires:  tar
BuildRequires:  zstd
BuildRequires:  desktop-file-utils
BuildRequires:  systemd-rpm-macros

# Runtime commands and libraries, after upstream's dependencies.sh (dnf branch)
# and its Nix package. Libraries the app dlopen()s are listed explicitly because
# rpm cannot see them.
Requires:       python3
Requires:       python3-gobject
Requires:       python3-cairo
Requires:       gtk4
Requires:       gtk4-layer-shell
Requires:       at-spi2-core
Requires:       librsvg2
Requires:       pipewire-utils
Requires:       pulseaudio-utils
Requires:       libnotify
Requires:       wl-clipboard
Requires:       /usr/bin/ffmpeg
Requires:       vulkan-loader
Requires:       libwayland-client
Requires:       libxkbcommon
Requires:       libxkbcommon-x11
Requires:       libxcb
Requires:       fontconfig
Requires:       procps-ng
Requires:       xdg-utils
Requires:       hicolor-icon-theme
Requires:       systemd
Recommends:     mesa-vulkan-drivers
# Sends the paste keystroke on wlroots compositors such as Sway.
Recommends:     wtype
Suggests:       fcitx5
%{?systemd_requires}
Requires(post): coreutils
Requires(post): glibc-common

%description
Superwhisper turns speech into text with local (Vulkan) or cloud
transcription and pastes it into the focused application. Built for
Wayland: Hyprland, KDE Plasma and GNOME.

This is an unofficial repackage of the upstream release archive for Fedora.
The in-app updater is disabled; updates arrive through dnf.

%prep
%setup -q -c -T
echo "%{src_sha256}  %{SOURCE0}" | sha256sum -c -
tar --zstd -xf %{SOURCE0} --strip-components=1
sha256sum --quiet -c MANIFEST.sha256

%build
# Nothing to build: upstream ships binaries.

%install
install -d %{buildroot}%{appdir}
cp -a app/. %{buildroot}%{appdir}/
# Upstream's uninstaller deletes a per-user install; replace it with a pointer to dnf.
install -m 0755 %{SOURCE6} %{buildroot}%{appdir}/uninstall.sh

sed 's|@APPDIR@|%{appdir}|' %{SOURCE1} > superwhisper.sh
install -Dm 0755 superwhisper.sh %{buildroot}%{_bindir}/superwhisper

install -Dm 0644 %{SOURCE2} %{buildroot}%{_userunitdir}/superwhisper.service
install -Dm 0644 %{SOURCE3} %{buildroot}%{_userpresetdir}/80-superwhisper.preset

install -d %{buildroot}%{_datadir}/applications
desktop-file-install --dir=%{buildroot}%{_datadir}/applications %{SOURCE4}
desktop-file-install --dir=%{buildroot}%{_datadir}/applications %{SOURCE5}

for png in app/assets/app-icon/*.png; do
  size=$(basename "$png" .png)
  [[ "$size" =~ ^[0-9]+$ ]] || continue
  install -Dm 0644 "$png" %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/superwhisper.png
done

install -Dm 0644 app/assets/linux-status/SuperwhisperTUI.ttf \
  %{buildroot}%{_datadir}/fonts/superwhisper/SuperwhisperTUI.ttf

install -d %{buildroot}%{_datadir}/gnome-shell/extensions
cp -a app/assets/gnome-extension/%{gnome_uuid} %{buildroot}%{_datadir}/gnome-shell/extensions/

install -d %{buildroot}%{_datadir}/fcitx5/addon
sed 's|@LIBRARY@|%{appdir}/lib/fcitx5/libsuperwhisper-fcitx5|' \
  app/assets/fcitx5/superwhisper.conf.in > %{buildroot}%{_datadir}/fcitx5/addon/superwhisper.conf

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/*.desktop
test -x %{buildroot}%{appdir}/bin/superwhisper
test -L %{buildroot}%{appdir}/lib/libonnxruntime.so

%post
%systemd_user_post superwhisper.service
# Like upstream's installer, start the daemon in graphical sessions that are
# already running; the preset alone only takes effect at the next login. Users
# who disabled the service are left alone; starting a running one is a no-op.
if [ -d /run/systemd/system ]; then
  for unit in $(systemctl list-units --type=service --state=active --plain --no-legend 'user@*.service' 2>/dev/null | awk '{print $1}'); do
    uid=${unit#user@}; uid=${uid%%.service}
    user=$(getent passwd "$uid" | cut -d: -f1)
    [ -n "$user" ] || continue
    timeout 10 systemctl --user -M "$user@" --quiet is-active graphical-session.target 2>/dev/null || continue
    timeout 10 systemctl --user -M "$user@" --quiet is-enabled superwhisper.service 2>/dev/null || continue
    timeout 10 systemctl --user -M "$user@" --no-block start superwhisper.service 2>/dev/null || :
  done
fi

%preun
%systemd_user_preun superwhisper.service

%postun
%systemd_user_postun_with_restart superwhisper.service

%files
%license licenses/*
%doc README.md BUILD_INFO.json
%{_bindir}/superwhisper
%{appdir}
%{_userunitdir}/superwhisper.service
%{_userpresetdir}/80-superwhisper.preset
%{_datadir}/applications/com.superwhisper.Superwhisper.desktop
%{_datadir}/applications/superwhisper-url.desktop
%{_datadir}/icons/hicolor/*/apps/superwhisper.png
%{_datadir}/fonts/superwhisper
%{_datadir}/gnome-shell/extensions/%{gnome_uuid}
%dir %{_datadir}/fcitx5
%dir %{_datadir}/fcitx5/addon
%{_datadir}/fcitx5/addon/superwhisper.conf

%changelog
* Fri Nov 20 2026 vintoware-rpm bot <noreply@github.com> - 1.3.1-2
- Start the user service in running graphical sessions on install and upgrade

* Fri Nov 20 2026 vintoware-rpm bot <noreply@github.com> - 1.3.1-1
- Initial package of Superwhisper 1.3.1
- Release notes: https://github.com/superultrainc/superwhisper-linux-releases/releases/tag/v1.3.1
