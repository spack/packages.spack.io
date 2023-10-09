# Spack Packages

This repository provides a rich search interface to currently available Spack packages. The metadata
is updated nightly. ⭐️ [See the Packages!](https://packages.spack.io) ⭐️

## Usage

You should run the generate script with spack, which means that it needs to be
on your path.

```bash
$ spack python generate_packages.py
```

This will generate a structure of data in [data](data) that is used to
generate the site.

```bash
$ tree data/
data/
├── packages
│   ├── 3dtk.json
│   ├── 3proxy.json
│   ├── abduco.json
│   ├── abi-compliance-checker.json
│   ├── abi-dumper.json
│   ├── abinit.json
│   ├── abseil-cpp.json
│   ├── abyss.json
│   ├── accfft.json
...
│   ├── zfs.json
│   ├── zig.json
│   ├── zip.json
│   ├── zipkin.json
│   ├── zlib.json
│   ├── zlib-ng.json
│   ├── zoltan.json
│   ├── zookeeper-benchmark.json
│   ├── zookeeper.json
│   ├── zsh.json
│   ├── zstd.json
│   ├── zstr.json
│   └── zziplib.json
└── packages.json

1 directory, 5668 files
```

You can then start a local web server to look at the interface!

```bash
$ python -m http.server 9999
```

The above would open to [http://localhost:9999](http://localhost:9999).
You can then browse the packages!

![img/package.png](img/package.png)

## Find an Issue?

There are a lot of edge cases with respect to metadata, so if you find a bug
please [let us know!](https://github.com/spack/packages). We will get it 
fixed up promptly.
