from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SHOPPING_CONTAINER = "webarena-shopping-ref"
FORUM_CONTAINER = "webarena-forum-ref"
SHOPPING_IMAGE = "am1n3e/webarena-verified-shopping"
FORUM_IMAGE = "webarenaimages/postmill-populated-exposed-withimg"
DEFAULT_TIMEOUT = 60
DEFAULT_WSL_DISTRO = "Ubuntu-24.04"
DEFAULT_CAPTURE_FLAGS = (
    "--disable-gpu",
    "--hide-scrollbars",
    "--run-all-compositor-stages-before-draw",
    "--virtual-time-budget=5000",
)
CAPTURE_TARGETS = (
    ("shopping_ref.png", "http://127.0.0.1:7770/", "1440,9000"),
    ("shopping_search.png", "http://127.0.0.1:7770/catalogsearch/result/?q=rice", "1440,7000"),
    (
        "shopping_product.png",
        "http://127.0.0.1:7770/crunchy-rice-rollers-gluten-free-vegan-3-5-oz-individual-packs-4-packs-of-8-rollers.html",
        "1440,7000",
    ),
    ("shopping_cart.png", "http://127.0.0.1:7770/checkout/cart/", "1440,3200"),
    ("forum_home.png", "http://127.0.0.1:9999/all/hot", "1440,5200"),
    ("forum_community.png", "http://127.0.0.1:9999/f/memes", "1440,5200"),
    (
        "forum_thread.png",
        "http://127.0.0.1:9999/f/memes/41616/which-of-the-following-fruits-will-be-the-2nd-most-popular",
        "1440,6200",
    ),
)


def docker_command_prefix() -> list[str]:
    candidate = shutil.which("docker") or shutil.which("docker.exe")
    if candidate:
        return [candidate]

    wsl = shutil.which("wsl") or shutil.which("wsl.exe")
    if wsl:
        distro = os.environ.get("WEBARENA_WSL_DISTRO", DEFAULT_WSL_DISTRO)
        return [wsl, "-d", distro, "--", "docker"]

    raise RuntimeError("docker was not found on PATH. Install Docker Desktop or make docker available first.")


def run_docker(*args: str, check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*docker_command_prefix(), *args],
        check=check,
        capture_output=capture_output,
        text=True,
    )


def stop_reference_containers() -> None:
    for container_name in (SHOPPING_CONTAINER, FORUM_CONTAINER):
        run_docker("rm", "-f", container_name, check=False, capture_output=True)


def start_reference_containers() -> None:
    stop_reference_containers()
    run_docker("run", "--name", SHOPPING_CONTAINER, "-p", "7770:80", "-d", SHOPPING_IMAGE)
    run_docker("run", "--name", FORUM_CONTAINER, "-p", "9999:80", "-d", FORUM_IMAGE)


def wait_http_ok(url: str, timeout_seconds: int = DEFAULT_TIMEOUT) -> None:
    deadline = time.time() + timeout_seconds
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})

    while time.time() < deadline:
        try:
            with urlopen(request, timeout=5):
                return
        except (HTTPError, URLError, TimeoutError, OSError):
            time.sleep(2)

    raise RuntimeError(f"Timed out waiting for {url}")


def find_capture_browser() -> str:
    candidates = [
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("msedge"),
        shutil.which("msedge.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate

    raise RuntimeError("No Chrome/Chromium/Edge executable was found for screenshot capture.")


def capture_reference_pages() -> None:
    browser = find_capture_browser()

    for file_name, url, window_size in CAPTURE_TARGETS:
        output_path = ROOT / file_name
        command = [
            browser,
            "--headless=new",
            *DEFAULT_CAPTURE_FLAGS,
            f"--window-size={window_size}",
            f"--screenshot={output_path}",
            url,
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            fallback = [
                browser,
                "--headless",
                *DEFAULT_CAPTURE_FLAGS,
                f"--window-size={window_size}",
                f"--screenshot={output_path}",
                url,
            ]
            subprocess.run(fallback, check=True)
        print(output_path)


def cmd_serve(args: argparse.Namespace) -> None:
    import tracking_server

    tracking_server.run_server(host=args.host, port=args.port)


def cmd_build_html(_: argparse.Namespace) -> None:
    import build_actual_html_mirror

    build_actual_html_mirror.main()


def cmd_build_zips(_: argparse.Namespace) -> None:
    import build_release_zips

    build_release_zips.main()


def cmd_compare(args: argparse.Namespace) -> None:
    import build_actual_html_mirror
    import tracking_server

    start_reference_containers()
    wait_http_ok("http://localhost:7770/")
    wait_http_ok("http://localhost:9999/all/hot")

    if args.build_html:
        build_actual_html_mirror.main()

    print("Tracking mirror: http://localhost:8000/")
    print("Getter JSON:     http://localhost:8000/getter")
    print("Shopping ref:    http://localhost:7770/")
    print("Forum ref:       http://localhost:9999/all/hot")

    try:
        tracking_server.run_server(host=args.host, port=args.port)
    finally:
        if not args.keep_refs:
            stop_reference_containers()


def cmd_stop_ref(_: argparse.Namespace) -> None:
    stop_reference_containers()


def cmd_capture(_: argparse.Namespace) -> None:
    capture_reference_pages()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Python CLI for the local WebArena mirror workspace.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Serve the local mirror and collect /getter events.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.set_defaults(func=cmd_serve)

    compare_parser = subparsers.add_parser(
        "compare",
        help="Start reference Docker containers and run the tracking server in the foreground.",
    )
    compare_parser.add_argument("--host", default="127.0.0.1")
    compare_parser.add_argument("--port", type=int, default=8000)
    compare_parser.add_argument("--build-html", action="store_true", help="Refresh the static mirror before serving.")
    compare_parser.add_argument(
        "--keep-refs",
        action="store_true",
        help="Keep the reference containers running after the server stops.",
    )
    compare_parser.set_defaults(func=cmd_compare)

    build_html_parser = subparsers.add_parser("build-html", help="Rebuild static HTML from the local reference servers.")
    build_html_parser.set_defaults(func=cmd_build_html)

    build_zips_parser = subparsers.add_parser("build-zips", help="Build shopping/reddit release ZIPs.")
    build_zips_parser.set_defaults(func=cmd_build_zips)

    stop_ref_parser = subparsers.add_parser("stop-ref", help="Stop and remove the local reference containers.")
    stop_ref_parser.set_defaults(func=cmd_stop_ref)

    capture_parser = subparsers.add_parser("capture", help="Capture reference screenshots with a local browser.")
    capture_parser.set_defaults(func=cmd_capture)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
