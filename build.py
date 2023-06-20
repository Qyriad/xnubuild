#!/usr/bin/env python3

import os
import os.path
import shutil
import argparse
import subprocess
from contextlib import contextmanager

BUILD_DIR: str
PWD: str
XCODE_SDK: str

LAST_CHECKED_COMMITS: dict[str, str] = dict(

)

@contextmanager
def chdir(path):
    oldcwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldcwd)

def run(args: list):
    print("\x1b[1m{}\x1b[0m".format(" ".join(args)))
    subprocess.check_call(args)

def capture(var: str, args: list) -> str:
    print("\x1b[1m{} = $({})\x1b[0m".format(var, " ".join(args)), end="")
    output = subprocess.check_output(args, encoding="utf-8").strip()
    print(f"\x1b[1m = {output}\x1b[0m")
    return output

def log(msg: str):
    print(f"\x1b[36;1m:: {msg}\x1b[0m")

def get_head_commit(repo_name: str) -> str:

    # head_commit = capture(
        # f"{repo_name.upper()}_HEAD",
        # "git show --no-patch --pretty=format:%h".split()
    # )

    with open(f"./{repo_name}/.git/HEAD", "r") as head_file:
        head_ref = head_file.read().strip().split()[1]

    with open(f"./{repo_name}/.git/{head_ref}", "r") as head_ref_file:
        head_commit = head_ref_file.read().strip()

    return head_commit

def dtrace():
    if not os.path.exists("./dtrace"):
        log("Fetching dtrace")
        run("git clone --depth=1 https://github.com/apple-oss-distributions/dtrace".split())

    head_commit = get_head_commit("dtrace")
    log(f"dtrace is: {head_commit}")

    log("Building dtrace")
    for ext in "obj sym dst".split():
        os.makedirs(os.path.join(BUILD_DIR.join(f"dtrace.{ext}")), exist_ok=True)

    with chdir("dtrace"):
        run([
            "xcodebuild",
            "CODE_SIGNING_ALLOWED=NO",
            "install",
            "-target", "ctfconvert",
            "-target", "ctfmerge",
            # "ARCHES=x86_64",
            "-sdk", f"{XCODE_SDK}",
            f"SRCROOT={PWD}/dtrace",
            f"OBJROOT={BUILD_DIR}/dtrace.obj",
            f"SYMROOT={BUILD_DIR}/dtrace.sym",
            f"DSTROOT={BUILD_DIR}/dtrace.dst",
        ])

        run(["ditto", f"{BUILD_DIR}/dtrace.dst", f"{BUILD_DIR}/dependencies"])

def availability_versions():

    if not os.path.exists("./AvailabilityVersions"):
        log("Fetching AvailabilityVersions")
        run("git clone --depth=1 https://github.com/apple-oss-distributions/AvailabilityVersions".split())

    head_commit = get_head_commit("AvailabilityVersions/")
    log(f"AvailabilityVersions is: {head_commit}")

    log("Building AvailabilityVersions")
    os.makedirs(os.path.join(BUILD_DIR.join("AvailabilityVersions.dst")), exist_ok=True)
    with chdir("./AvailabilityVersions"):
        run([
            "make",
            "install",
            f"SRCROOT={PWD}/AvailabilityVersions",
            f"DSTROOT={BUILD_DIR}/AvailabilityVersions.dst",
        ])

        run(["ditto", f"{BUILD_DIR}/AvailabilityVersions.dst/usr/local", f"{BUILD_DIR}/dependencies"])

# def bootstrap_cmds():

    # if not os.path.exists("./bootstrap_cmds"):
        # log("Fetching bootstrap_cmds")
        # run("git clone --depth=1 https://github.com/apple-oss-distributions/bootstrap_cmds".split())

        # head_commit = get_head_commit("bootstrap_cmds")
        # log(f"bootstrap_cmds is: {head_commit}")

        # log("Building bootstrap_cmds")
        # os.makedirs(os.path.join(BUILD_DIR.join("bootstrap_cmds.dst")), exist_ok=True)
        # with chdir("./bootstrap_cmds"):
            # run([
                # "V

def xnu_headers():

    if not os.path.exists("./xnu"):
        log("Fetching XNU")
        run("git clone --depth=1 https://github.com/apple-oss-distributions/xnu".split())

    head_commit = get_head_commit("xnu")
    log(f"XNU is: {head_commit}")

    log("Building XNU headers")
    for ext in "obj sym dst".split():
        os.makedirs(os.path.join(BUILD_DIR.join(f"xnu.hdrs.{ext}")), exist_ok=True)

    with chdir("./xnu"):
        dependencies_dir = os.path.join(BUILD_DIR, "dependencies")
        run([
            "make",
            "config",
            f"SDKROOT={XCODE_SDK}",
            # "ARCH_CONFIGS=X86_64",
            f"SRCROOT={PWD}/xnu",
            f"OBJROOT={BUILD_DIR}/xnu.hdrs.obj",
            f"SYMROOT={BUILD_DIR}/xnu.hdrs.sym",
            f"DSTROOT={BUILD_DIR}/xnu.hdrs.dst",
            f"DEPENCENCIES_DIR={dependencies_dir}",
        ])

        run([
            "xcodebuild",
            "installhdrs",
            "-project", "libsyscall/Libsyscall.xcodeproj",
            "-sdk", f"{XCODE_SDK}",
            f"SRCROOT={PWD}/xnu/libsyscall",
            f"OBJROOT={BUILD_DIR}/xnu.hdrs.obj"
            f"SYMROOT={BUILD_DIR}/xnu.hdrs.sym",
            f"DSTROOT={BUILD_DIR}/xnu.hdrs.dst",
            f"DEPENDENCIES_DIR={BUILD_DIR}/dependencies",
        ])

        run(["ditto", f"{BUILD_DIR}/xnu.hdrs.dst", f"{BUILD_DIR}/dependencies"])


def main():

    parser = argparse.ArgumentParser("xnubuild")
    parser.add_argument("action", choices=["build", "clean"], default="build", nargs="?")
    args = parser.parse_args()
    if args.action == "clean":
        for directory in "dtrace AvailabilityVersions xnu build d A x".split():
            if os.path.exists(directory):
                print(f"rm -rf {directory}")
                shutil.rmtree(directory)
        return

    global PWD, BUILD_DIR, XCODE_SDK
    PWD = os.getcwd()
    os.makedirs("build/dependencies", exist_ok=True)
    BUILD_DIR = os.path.join(PWD, "build")

    xcode_sdk_version = capture("SDK_VERSION", "xcrun -show-sdk-platform-version".split())
    XCODE_SDK = f"macosx{xcode_sdk_version}"
    xcode_developer_dir = capture("XCODE_DEVELOPER_DIR", "xcode-select -print-path".split())

    dtrace()
    availability_versions()
    xnu_headers()


if __name__ == "__main__":
    main()
