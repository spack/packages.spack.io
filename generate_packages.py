#!/usr/bin/env spack-python

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
from datetime import datetime

import spack.repo
import spack.spec
import spack.version

here = os.getcwd()

# spack python does not have __file__
__file__ = os.path.join(here, "generate_packages.py")
if not os.path.exists(__file__):
    sys.exit("Please run in the same directory as generate_packages.py")

## File Operations


def write_json(content, filename):
    with open(filename, "w") as outfile:
        outfile.write(json.dumps(content, indent=4, sort_keys=True))


def main():

    pkgs = spack.repo.all_package_names(include_virtuals=True)
    deps_of = {}
    descriptions = {}
    metas = {}
    package_variants = {}

    # Iterate through consistent order
    pkgs = sorted(pkgs)

    # Prepre to create repology output alongside packages files
    repology = {
        "repository_name": "spack",
        "num_packages": len(pkgs),
        "last_update": str(datetime.now()),
        "packages": {},
    }

    for i, package in enumerate(pkgs):

        print("Parsing %s, %s of %s" % (package, i, len(pkgs)))
        pkg_class = spack.repo.PATH.get_pkg_class(package)
        # this should be refactored later to just use the pkg_class
        pkg = pkg_class(spack.spec.Spec(package))
        descriptions[pkg.name] = pkg.format_doc().strip()

        patches = []
        patches_repology = []
        if pkg.patches:
            for key, patchlist in pkg.patches.items():
                for patch in patchlist:
                    patch = patch.to_dict()
                    patch.update({"version": str(key)})
                    patches.append(patch)
                    if patch["version"]:
                        patches_repology.append(
                            "%s when %s"
                            % (
                                patch.get("relative_path") or patch.get("url"),
                                patch["version"],
                            )
                        )
                    else:
                        patches_repology.append(
                            patch.get("relative_path") or patch.get("url")
                        )

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

        # this will miss ibm-java, which only adds versions for ppc64le, but we can fix
        # that in the package later.
        if not pkg.versions:
            continue

        versions = []
        versions_deprecated = []
        seen_versions = set()
        for version, hashes in sorted(pkg.versions.items(), reverse=True):

            # Skip a version we have already seen
            if str(version) in seen_versions:
                continue

            seen_versions.add(str(version))
            meta = {"name": str(version)}
            for key, h in hashes.items():
                if isinstance(key, str) and isinstance(h, str):
                    meta[key] = h

            if pkg.versions[version].get("deprecated", False):
                versions_deprecated.append(meta)
            else:
                versions.append(meta)

        # Repology wants a completely different format for versions
        repology_versions = []
        for version, version_meta in pkg.versions.items():

            # Skip deprecated versions entirely since repology picks the
            # most recent version, even if deprecated due to switch from
            # calver to semver or so (e.g. ants)
            if pkg.versions[version].get("deprecated", False):
                continue

            meta = {"version": str(version)}

            try:
                url = pkg.url_for_version(version)
            except BaseException as e:
                url = pkg.all_urls

            # Is there a develop branch?
            if version.isdevelop():
                meta["branch"] = str(version)
                if hasattr(pkg, "git"):
                    meta["repositories"] = [{"url": pkg.git, "type": "git", "branch": str(version)}]
            elif "commit" in version_meta and hasattr(pkg, "git"):
                meta["repositories"] = [{"url": pkg.git, "type": "git", "commit": version_meta["commit"]}]
            elif "tag" in version_meta and hasattr(pkg, "git"):
                meta["repositories"] = [{"url": pkg.git, "type": "git", "tag": version_meta["tag"]}]
            elif "branch" in version_meta and hasattr(pkg, "git"):
                meta["repositories"] = [{"url": pkg.git, "type": "git", "branch": version_meta["branch"]}]
            else:
                meta["downloads"] = [url]

            # We can only get specific deps with concretization, which doesn't always work
            # try:
            #    spec = spack.spec.Spec("%s@%s" %(pkg.name, version))
            #    spec.concretize()
            #    deps = list(spec.dependencies_dict().keys())
            # except:
            #    deps = []
            # meta['dependencies'] = deps
            repology_versions.append(meta)
        repology_versions.sort(key=lambda x: x["version"])

        variants = []
        if pkg.variants:
            for name in pkg.variant_names():
                variant = [vdef for _, vdef in pkg.variant_definitions(name)]
                if name not in package_variants:
                    package_variants[name] = []
                package_variants[name].append(
                    {"package": pkg.name, "default": variant[0].default}
                )
                variants.append(
                    {
                        "name": name,
                        "default": variant[0].default,
                        "description": variant[0].description,
                    }
                )
        variants.sort(key=lambda x: x["name"])

        conflicts = []
        if pkg.conflicts:
            for when, conflict_list in pkg.conflicts.items():
                for conflict, msg in conflict_list:
                    conflicts.append(
                        {
                            "name": str(conflict),
                            "spec": str(when),
                            "description": msg,
                        }
                    )
        conflicts.sort(key=lambda x: x["spec"] + x["name"] + getattr(x, "description", ""))

        aliases = []
        raw_aliases = set()
        if pkg.provided:
            for when, provided_specs in pkg.provided.items():
                for provided in provided_specs:
                    descriptions[provided.name] = pkg.format_doc().strip()
                    aliases.append({"name": str(provided.name), "alias_for": str(when)})
                    raw_aliases.add(provided.name)
        aliases.sort(key=lambda x: x["alias_for"] + x["name"])

        # Get latest version!
        latest_version = spack.version.VersionList(pkg.versions).preferred()
        meta = {
            "name": pkg.name,
            "aliases": aliases,
            "versions": versions,
            "versions_deprecated": versions_deprecated,
            "latest_version": str(latest_version),
            "build_system": pkg.build_system_class,
            "conflicts": conflicts,
            "variants": variants,
            "homepage": pkg.homepage,
            "maintainers": pkg.maintainers,
            "patches": patches,
            "resources": resources,
            "description": pkg.format_doc(),
            "dependencies": pkg.dependency_names(),
        }

        # Keep master lookup of all dependents
        for dep in meta["dependencies"]:
            if dep not in deps_of:
                deps_of[dep] = set()
            deps_of[dep].add(pkg.name)

        metas[pkg.name] = meta

        # Aliases can be linked too
        for alias in sorted(list(raw_aliases)):
            metas[alias] = meta

        # Best effort to get urls for versions
        try:
            urls = [pkg.url_for_version(x["name"]) for x in versions]
        except:
            urls = pkg.all_urls

        # Add git repository to urls if specified
        if hasattr(pkg, "git"):
            urls.append(pkg.git)

        # Add to repology
        repology_pkg = {
            "name": pkg.name,
            "version": repology_versions,
            "summary": meta["description"],
            "maintainers": meta["maintainers"],
            "licenses": list(pkg.licenses.values()),
            "downloads": urls,
            "homepages": [pkg.homepage],
            "patches": patches_repology,
            "categories": getattr(pkg, "tags", []),
            "dependencies": meta["dependencies"],
            "alias": meta["aliases"],
        }

        repology["packages"][pkg.name] = repology_pkg
        for alias in raw_aliases:
            repology["packages"][alias] = repology_pkg

    # Sort package variants
    for name in package_variants.keys():
        package_variants[name].sort(key=lambda x: x["package"])

    # Save package variants
    outfile = os.path.join(here, "data", "variants.json")
    write_json(package_variants, outfile)

    # Save repology
    outfile = os.path.join(here, "data", "repology.json")
    write_json(repology, outfile)

    # We need one file with all names available
    names = [{'name': p, 'description': metas[p]['description']} for p in metas.keys()]
    names.sort(key=lambda x: x['name'])
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
        meta["dependencies"].sort(key=lambda x: x["name"])
        meta["dependent_to"].sort(key=lambda x: x["name"])
        outfile = os.path.join(here, "data", "packages", "%s.json" % pkg)
        try:
            write_json(meta, outfile)
        except Exception as e:
            print(f"cannot update {pkg}: {str(e)}")


if __name__ == "__main__":
    main()
