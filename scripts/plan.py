#!/usr/bin/env python3
"""Decide which packages need building.

For every packages/<dir>/<dir>.spec, asks rpmspec for its name, EVR and
architectures. A package needs a build when no release tag `<name>/<evr>`
exists yet (pass existing tags on stdin, one per line, e.g. from
`git ls-remote --tags origin`). Prints a GitHub Actions matrix as JSON:

  {"include": [{"package": "...", "name": "...", "evr": "...",
                "arch": "x86_64", "runner": "ubuntu-24.04"}, ...]}

`--force <dir>` plans that package even when its tag exists (the release is
then replaced).
"""
import argparse
import glob
import json
import os
import subprocess
import sys

RUNNERS = {"x86_64": "ubuntu-24.04", "aarch64": "ubuntu-24.04-arm"}


def rpmspec(spec, *query):
    out = subprocess.run(["rpmspec", "-q", *query, spec], check=True, capture_output=True, text=True).stdout
    return out.split()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    parser.add_argument("--force", action="append", default=[])
    args = parser.parse_args()

    tags = set()
    for line in sys.stdin:
        ref = line.split()[-1] if line.strip() else ""
        ref = ref.removeprefix("refs/tags/").removesuffix("^{}")
        if ref:
            tags.add(ref)

    include = []
    for spec in sorted(glob.glob(os.path.join(args.root, "packages", "*", "*.spec"))):
        package = os.path.basename(os.path.dirname(spec))
        if os.path.basename(spec) != f"{package}.spec":
            continue
        name, evr = rpmspec(spec, "--srpm", "--qf", "%{name} %{evr}\n")
        exclusive = set(rpmspec(spec, "--srpm", "--qf", "[%{exclusivearch}\n]"))
        binary_arches = set(rpmspec(spec, "--qf", "%{arch}\n"))
        if binary_arches == {"noarch"}:
            arches = ["x86_64"]
        else:
            arches = [a for a in RUNNERS if not exclusive or a in exclusive]
        tag = f"{name}/{evr}"
        if tag in tags and package not in args.force:
            print(f"{tag}: already released", file=sys.stderr)
            continue
        print(f"{tag}: build on {', '.join(arches)}", file=sys.stderr)
        include += [{"package": package, "name": name, "evr": evr, "arch": a, "runner": RUNNERS[a]} for a in arches]

    print(json.dumps({"include": include}))


if __name__ == "__main__":
    main()
