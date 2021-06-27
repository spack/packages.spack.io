#!/usr/bin/env python3

# This script will generate package metadata files for
# each package in the latest version of spack
#
# Usage:
# spack python generate_packages.py


import json
import tempfile
import subprocess
import shutil
import sys
import os

import spack.repo
import spack.spec

here = os.getcwd()

# spack python does not have __file__
__file__ = os.path.join(here, "generate_packages.py")
if not os.path.exists(__file__):
    sys.exit("Please run in the same directory as generate_packages.py")

## File Operations


def write_json(content, filename):
    with open(filename, "w") as outfile:
        outfile.write(json.dumps(content, indent=4))


def main():

    pkgs = set(spack.repo.all_package_names(include_virtuals=True))
    deps_of = {}
    descriptions = {}
    metas = {}

    for i, package in enumerate(pkgs):

        print("Parsing %s, %s of %s" % (package, i, len(pkgs)))
        pkg = spack.spec.Spec(package).package
        descriptions[pkg.name] = pkg.format_doc().strip()

        patches = []
        if pkg.patches:
            for key, patchlist in pkg.patches.items():
                for patch in patchlist:
                    patch = patch.to_dict()
                    patch.update({"version": str(key)})
                    patches.append(patch)

        resources = []
        if pkg.resources:
            for version, resourcelist in pkg.resources.items():
                for resource in resourcelist:
                    resources.append(
                        {
                            "version": str(version),
                            "name": resource.name,
                            "destination": resource.destination,
                            "placement": resource.placement,
                        }
                    )

        versions = []
        for version, hashes in pkg.versions.items():
            meta = {"name": str(version)}
            for key, h in hashes.items():
                meta[key] = h
            versions.append(meta)

        variants = []
        if pkg.variants:
            for name, variant in pkg.variants.items():
                variants.append(
                    {
                        "name": name,
                        "default": variant.default,
                        "description": variant.description,
                    }
                )

        conflicts = []
        if pkg.conflicts:
            for name, conflict_list in pkg.conflicts.items():
                for conflict in conflict_list:
                    conflicts.append(
                        {
                            "name": name,
                            "spec": str(conflict[0]),
                            "description": str(conflict[1]),
                        }
                    )

        aliases = []
        raw_aliases = []
        if pkg.provided:
            for name, alias in pkg.provided.items():
                splitup = str(name).split("@", 1)[0]
                descriptions[splitup] = pkg.format_doc().strip()
                aliases.append({"name": str(name), "alias_for": str(alias)})
                raw_aliases.append(splitup)

        # We don't include any fields that would require concretization
        meta = {
            "name": pkg.name,
            "aliases": aliases,
            "versions": versions,
            "build_system": pkg.build_system_class,
            "conflicts": conflicts,
            "variants": variants,
            "homepage": pkg.homepage,
            "maintainers": pkg.maintainers,
            "patches": patches,
            "resources": resources,
            "description": pkg.format_doc(),
            "dependencies": list(pkg.dependencies.keys()),
        }

        # Keep master lookup of all dependents
        for dep in meta["dependencies"]:
            if dep not in deps_of:
                deps_of[dep] = set()
            deps_of[dep].add(pkg.name)

        metas[pkg.name] = meta

        # Aliases can be linked too
        for alias in raw_aliases:
            metas[alias] = meta

    # We need one file with all names available
    names = list(metas.keys())
    names.sort()
    outfile = os.path.join(here, "data", "packages.json")
    write_json(names, outfile)

    # Once we get here, add dependents and save to file
    print("Writing results to file!")
    for pkg, meta in metas.items():

        # Add descriptions to dependent to and deps
        new_deps = []
        for dep in meta["dependencies"]:

            # If we've already seen it via an alias, we're good
            if isinstance(dep, dict):
                new_deps.append(dep)
            else:
                new_deps.append({"name": dep, "description": descriptions.get(dep, "")})

        meta["dependencies"] = new_deps
        meta["dependent_to"] = []

        deps = deps_of.get(pkg, set())
        for dep in list(deps):
            meta["dependent_to"].append(
                {"name": dep, "description": descriptions.get(dep, "")}
            )
        outfile = os.path.join(here, "data", "packages", "%s.json" % pkg)
        write_json(meta, outfile)


if __name__ == "__main__":
    main()
