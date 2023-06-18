#!/usr/bin/env python3

import os
import os.path
import subprocess

BUILD_DIR: str
PWD: str
XCODE_SDK: str

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

def dtrace():
    if not os.path.exists("./dtrace"):
        log("Fetching dtrace")
        run("git clone https://github.com/apple-oss-distributions/dtrace".split())

    log("Building dtrace")
    for ext in "obj sym dst".split():
        os.makedirs(os.path.join(BUILD_DIR.join(f"dtrace.{ext}")), exist_ok=True)

    os.chdir("dtrace")
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

    run(["ditto", f"{BUILD_DIR}/dtrace.dst", "{build_dir}/dependencies"])

def main():

    global PWD, BUILD_DIR, XCODE_SDK
    PWD = os.getcwd()
    os.makedirs("build/dependencies", exist_ok=True)
    BUILD_DIR = os.path.join(PWD, "build")

    xcode_sdk_version = capture("SDK_VERSION", "xcrun -show-sdk-platform-version".split())
    XCODE_SDK = f"macosx{xcode_sdk_version}"
    xcode_developer_dir = capture("XCODE_DEVELOPER_DIR", "xcode-select -print-path".split())

    dtrace()


if __name__ == "__main__":
    main()
