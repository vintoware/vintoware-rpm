# Built from upstream's source at the release tag's commit. Upstream signs its
# commits but publishes no signed release artifacts, so ./update pins the tag's
# commit after GitHub reports its signature as verified, and records the source
# archive's SHA-256, which %%prep checks again. The upstream values below are
# rewritten by ./update -- edit by hand only for packaging fixes (and bump
# Release when you do).
%global commit 62a1f685b231c0cd8633a658f481059bb9ed0641
%global src_sha256 6a05408893643d05b8e6fc0f474def5f2bc48614b3bda4b48a1c1c605aa12b20

# Swift has no stable ABI on Linux, and Fedora's swift-lang-runtime installs
# its libraries in %%{_libdir} with unversioned sonames, so a later swift-lang
# update could break a binary linked against them. Fedora's toolchain can't link
# the Swift runtime statically (no swift_static), so the runtime libraries this
# build links against are bundled privately in %%{_libdir}/xcodegen instead.
%global privlibdir %{_libdir}/xcodegen
%global __provides_exclude_from ^%{privlibdir}/
%global __requires_exclude ^(libswift|libFoundation|lib_Foundation|libdispatch|libBlocksRuntime|libTesting|lib_Testing|libXCTest)[^ ]*\\.so

# Fedora's Swift libraries are shipped stripped: no debuginfo package.
%global debug_package %{nil}

# SwiftPM compiles the C parts of the Swift toolchain's packages with $CC, and
# they need clang (-target, -fblocks); gcc, the default, rejects them.
%global toolchain clang

Name:           xcodegen
Version:        2.48.0
Release:        1
Summary:        Generate Xcode projects from a YAML or JSON project spec
# XcodeGen is MIT. Statically linked: AEXML, JSONUtilities, Rainbow, SwiftCLI,
# XcodeProj, Yams (MIT); PathKit (BSD-2-Clause); Version, xcode-project-format
# (Apache-2.0). Bundled: the Swift runtime and Foundation (Apache-2.0 WITH
# Swift-exception).
License:        MIT AND BSD-2-Clause AND Apache-2.0 AND Apache-2.0 WITH Swift-exception
URL:            https://github.com/yonaskolb/XcodeGen
# Swift only supports these architectures on Fedora.
ExclusiveArch:  x86_64 aarch64

Source0:        %{url}/archive/%{commit}.tar.gz#/XcodeGen-%{version}.tar.gz

BuildRequires:  swift-lang
BuildRequires:  clang
BuildRequires:  patchelf
BuildRequires:  lld
BuildRequires:  binutils
BuildRequires:  git-core
BuildRequires:  coreutils
BuildRequires:  tar
BuildRequires:  gzip

%description
XcodeGen is a command line tool that generates an Xcode project from a
project.yml (or JSON) spec and the folder structure of your source files, so
the .xcodeproj can stay out of version control and merge conflicts go away.

On Linux it generates projects for use on a Mac or by tools that read
.xcodeproj files; building them still needs Xcode.

%prep
%setup -q -c -T
echo "%{src_sha256}  %{SOURCE0}" | sha256sum -c -
tar -xzf %{SOURCE0} --strip-components=1
chmod 0644 LICENSE
# The release commit sets the version the CLI reports.
grep -qF 'Version("%{version}")' Sources/XcodeGen/main.swift

%build
# Dependencies are cloned by SwiftPM at the exact git revisions pinned in
# upstream's Package.resolved; --force-resolved-versions refuses to move them.
# Linked with lld: ld.bfd merges this binary into a single writable and
# executable LOAD segment. Full RELRO, as Fedora's own hardening flags ask for.
swift build -c release --force-resolved-versions --disable-sandbox \
  %{?_smp_build_ncpus:-j %{_smp_build_ncpus}} \
  -Xswiftc -use-ld=lld -Xlinker -z -Xlinker now \
  --product xcodegen

%install
bin=$(swift build -c release --show-bin-path)
install -Dm 0755 "$bin/xcodegen" %{buildroot}%{_bindir}/xcodegen

# Bundle every library the binary loads from swift-lang-runtime. The binary
# finds them through its rpath and they find each other through $ORIGIN.
install -d %{buildroot}%{privlibdir}
ldd "$bin/xcodegen" | awk '$2 == "=>" && $3 ~ /^\// { print $3 }' > needed.txt
while read -r lib; do
  case $(rpm -qf --qf '%%{NAME}' "$lib") in
    swift-lang-runtime)
      dest=%{buildroot}%{privlibdir}/$(basename "$lib")
      install -m 0755 "$(readlink -f "$lib")" "$dest"
      patchelf --set-rpath '$ORIGIN' "$dest"
      ;;
  esac
done < needed.txt
test -e %{buildroot}%{privlibdir}/libswiftCore.so
test -e %{buildroot}%{privlibdir}/libFoundation.so
patchelf --set-rpath %{privlibdir} %{buildroot}%{_bindir}/xcodegen
# XcodeGen looks for its presets at <bindir>/../share/xcodegen/SettingPresets.
install -d %{buildroot}%{_datadir}/xcodegen
cp -rL SettingPresets %{buildroot}%{_datadir}/xcodegen/
find %{buildroot}%{_datadir}/xcodegen -type d -exec chmod 0755 {} + -o -type f -exec chmod 0644 {} +

# License texts of the statically linked dependencies.
install -d licenses
for dep in AEXML JSONUtilities PathKit Rainbow SwiftCLI Version xcode-project-format XcodeProj Yams; do
  install -m 0644 .build/checkouts/$dep/LICENSE* licenses/$dep-LICENSE
done
for f in $(rpm -ql swift-lang-runtime | grep '^%{_datadir}/licenses/'); do
  [ -f "$f" ] && install -m 0644 "$f" licenses/swift-runtime-$(basename "$f")
done
ls licenses/swift-runtime-*

%check
# No segment may be both writable and executable.
if readelf -lW %{buildroot}%{_bindir}/xcodegen | grep -E '^\s*LOAD.*RWE'; then
  echo 'xcodegen has a writable and executable LOAD segment' >&2; exit 1
fi
readelf -dW %{buildroot}%{_bindir}/xcodegen | grep -q 'BIND_NOW'

# Generate an iOS project from a minimal spec and check the presets were
# applied. The source tree's presets are moved aside (XcodeGen also looks next
# to its compile-time source path) so they must come from the installed copy.
export HOME=$PWD/.home
# generate records $USER in the project; build containers may not set it.
export USER=${USER:-builder}
mv SettingPresets SettingPresets.check
trap 'mv SettingPresets.check SettingPresets' EXIT
work=$(mktemp -d)
mkdir -p "$work/App"
echo 'print("hi")' > "$work/App/main.swift"
cat > "$work/project.yml" <<'EOF'
name: Smoke
options:
  bundleIdPrefix: org.example
targets:
  Smoke:
    type: application
    platform: iOS
    deploymentTarget: "17.0"
    sources: [App]
EOF
# Run against the bundled libraries, and make sure that is what gets loaded.
export LD_LIBRARY_PATH=%{buildroot}%{privlibdir}
if ldd %{buildroot}%{_bindir}/xcodegen | grep -E '^\s*lib(swift|Foundation|_Foundation|dispatch|BlocksRuntime)' |
    grep -vF '=> %{buildroot}%{privlibdir}/'; then
  echo 'xcodegen loads system Swift libraries instead of the bundled ones' >&2; exit 1
fi
(cd "$work" && %{buildroot}%{_bindir}/xcodegen generate --quiet)
pbx="$work/Smoke.xcodeproj/project.pbxproj"
grep -q 'SDKROOT = iphoneos;' "$pbx"
grep -q 'IPHONEOS_DEPLOYMENT_TARGET = 17.0;' "$pbx"
grep -q 'main.swift in Sources' "$pbx"
%{buildroot}%{_bindir}/xcodegen version | grep -F %{version}
rm -rf "$work"

%files
%license LICENSE licenses/*
%doc README.md CHANGELOG.md Docs/*.md
%{_bindir}/xcodegen
%{privlibdir}
%{_datadir}/xcodegen

%changelog
* Tue Nov 24 2026 vintoware-rpm bot <noreply@github.com> - 2.48.0-1
- Initial package of XcodeGen 2.48.0
- Release notes: https://github.com/yonaskolb/XcodeGen/releases/tag/2.48.0
