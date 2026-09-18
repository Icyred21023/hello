import json
import shlex
from typing import Any
from urllib.parse import parse_qsl

import requests





def normalize_curl(command: str) -> str:
    """
    Convert a multiline copied cURL command into one shell-style command.
    """
    command = command.strip()

    # DevTools may use backslash + newline for line continuation.
    command = command.replace("\\\r\n", " ")
    command = command.replace("\\\n", " ")

    # Some platforms may copy the Windows continuation character.
    command = command.replace("^\r\n", " ")
    command = command.replace("^\n", " ")

    return command


def parse_header(header: str) -> tuple[str, str]:
    if ":" not in header:
        raise ValueError(f"Invalid cURL header: {header!r}")

    name, value = header.split(":", 1)
    return name.strip(), value.strip()


def curl_to_request(command: str) -> dict[str, Any]:
    """
    Parse a common Chrome DevTools 'Copy as cURL' command.

    Supports:
      - URL
      - -X / --request
      - -H / --header
      - -d / --data
      - --data-raw
      - --data-binary
      - --data-urlencode
      - -b / --cookie
      - -A / --user-agent
      - -e / --referer
      - -u / --user
      - -k / --insecure
      - --compressed
    """
    command = normalize_curl(command)
    tokens = shlex.split(command, posix=True)

    if not tokens or tokens[0].lower() not in {"curl", "curl.exe"}:
        raise ValueError("The variable must begin with curl.")

    url: str | None = None
    method: str | None = None
    headers: dict[str, str] = {}
    data_parts: list[str] = []
    auth: tuple[str, str] | None = None
    verify = True

    i = 1

    while i < len(tokens):
        token = tokens[i]

        if token in {"-X", "--request"}:
            i += 1
            method = tokens[i].upper()

        elif token.startswith("--request="):
            method = token.split("=", 1)[1].upper()

        elif token in {"-H", "--header"}:
            i += 1
            name, value = parse_header(tokens[i])

            # :authority is an HTTP/2 pseudo-header. Requests creates Host.
            if name.lower() not in {":authority", "authority"}:
                headers[name] = value

        elif token.startswith("--header="):
            name, value = parse_header(token.split("=", 1)[1])

            if name.lower() not in {":authority", "authority"}:
                headers[name] = value

        elif token in {
            "-d",
            "--data",
            "--data-raw",
            "--data-binary",
            "--data-ascii",
            "--data-urlencode",
        }:
            i += 1
            data_parts.append(tokens[i])

        elif any(
            token.startswith(prefix)
            for prefix in (
                "--data=",
                "--data-raw=",
                "--data-binary=",
                "--data-ascii=",
                "--data-urlencode=",
            )
        ):
            data_parts.append(token.split("=", 1)[1])

        elif token in {"-b", "--cookie"}:
            i += 1
            headers["Cookie"] = tokens[i]

        elif token.startswith("--cookie="):
            headers["Cookie"] = token.split("=", 1)[1]

        elif token in {"-A", "--user-agent"}:
            i += 1
            headers["User-Agent"] = tokens[i]

        elif token.startswith("--user-agent="):
            headers["User-Agent"] = token.split("=", 1)[1]

        elif token in {"-e", "--referer"}:
            i += 1
            headers["Referer"] = tokens[i]

        elif token.startswith("--referer="):
            headers["Referer"] = token.split("=", 1)[1]

        elif token in {"-u", "--user"}:
            i += 1
            username, separator, password = tokens[i].partition(":")
            auth = (username, password if separator else "")

        elif token.startswith("--user="):
            credentials = token.split("=", 1)[1]
            username, separator, password = credentials.partition(":")
            auth = (username, password if separator else "")

        elif token in {"-k", "--insecure"}:
            verify = False

        elif token in {
            "--compressed",
            "-s",
            "--silent",
            "-S",
            "--show-error",
            "-i",
            "--include",
            "-L",
            "--location",
        }:
            # Requests handles decompression automatically.
            # Redirect behavior is configured while sending.
            pass

        elif token.startswith("http://") or token.startswith("https://"):
            url = token

        elif not token.startswith("-") and url is None:
            url = token

        i += 1

    if not url:
        raise ValueError("No URL was found in the copied cURL command.")

    body = "&".join(data_parts) if data_parts else None

    if method is None:
        method = "POST" if body is not None else "GET"

    return {
        "method": method,
        "url": url,
        "headers": headers,
        "body": body,
        "auth": auth,
        "verify": verify,
    }


def execute_curl_as_requests(
    copied_curl: str,
    timeout: int = 30,
) -> requests.Response:
    parsed = curl_to_request(copied_curl)

    method = parsed["method"]
    url = parsed["url"]
    headers = parsed["headers"]
    body = parsed["body"]

    request_kwargs: dict[str, Any] = {
        "method": method,
        "url": url,
        "headers": headers,
        "timeout": timeout,
        "verify": parsed["verify"],
        "allow_redirects": True,
    }

    if parsed["auth"] is not None:
        request_kwargs["auth"] = parsed["auth"]

    if body is not None:
        content_type = headers.get(
            "content-type",
            headers.get("Content-Type", ""),
        ).lower()

        # Decode JSON so Requests serializes it properly.
        if "application/json" in content_type:
            try:
                request_kwargs["json"] = json.loads(body)
            except json.JSONDecodeError:
                request_kwargs["data"] = body

        elif "application/x-www-form-urlencoded" in content_type:
            request_kwargs["data"] = dict(
                parse_qsl(body, keep_blank_values=True)
            )

        else:
            request_kwargs["data"] = body

    with requests.Session() as session:
        return session.request(**request_kwargs)


def print_response(response: requests.Response) -> None:
    print("HTTP status:", response.status_code)
    print("Final URL:", response.url)
    print("Content-Type:", response.headers.get("content-type"))
    print("Server:", response.headers.get("server"))
    print("CF-Ray:", response.headers.get("cf-ray"))
    print()

    try:
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except requests.exceptions.JSONDecodeError:
        print(response.text[:10_000])

def curl_get(url,cookie,pl, ua, sec_ch_ua,prio):
    if isinstance(pl, dict):
        pl = json.dumps(pl, separators=(",", ":"))
    curl = rf"""
curl '{url}' \
    -H 'authority: api.rivalsdata.com' \
    -H 'accept: application/json' \
    -H 'accept-language: en-US,en;q=0.9' \
    -H 'content-type: application/json' \
    -b 'cf_clearance={cookie}' \
    -H 'origin: https://rivalsdata.com' \
    -H 'priority: {prio}' \
    -H 'referer: https://rivalsdata.com/' \
    -H 'sec-ch-ua: {sec_ch_ua}' \
    -H 'sec-ch-ua-mobile: ?0' \
    -H 'sec-ch-ua-platform: "Windows"' \
    -H 'sec-fetch-dest: empty' \
    -H 'sec-fetch-mode: cors' \
    -H 'sec-fetch-site: same-site' \
    -H 'user-agent: {ua}' \
    --data-raw '{pl}'
    """
#     curl 'https://api.rivalsdata.com/player' \
#   -H 'accept: application/json' \
#   -H 'accept-language: en-US,en;q=0.9' \
#   -H 'content-type: application/json' \
#   -b 'cf_clearance=TSSflJQLEbiM34KbvEncOYLtcQehE9qNMVTcxXRCT7A-1785513493-1.2.1.1-reBuM77hB1h.ae1woAhLUTynQ.cGcb71MY3Ap2NJRSzZU3eU0U1O66FDeZg0EdgXYQb6iWxTYLNNWq9pcviVqgzZPu.hDLYBXdP_qV0F_ES9PzdYmfyCCTDzfCW05N.4zt7oXxNmZqRqkThWLDujzdalnxYZJ995swshq3xwcE.H7TjtYaxk8cnqgfgilKngD6AInPpWMFQlDRoX180j0Wx250qLoxYgneVc27rOnTP4SR_hg.vOWWgKAQ6BGQGZMo3oan.gmzVPCHdOyCxShcagrPhfbPdBIOTsoUyNbs5iLUjfdx45tI6v6j9Oxgx5zjIno2YAcId7ak9DWqov0kkWJu7TU6G6N.1wIzI867wH6kwR2j6.G69tsUCwN4HrGlXaEtaW_snWyCj_WCTmmCujrA5KRJqNy4nOAW0HaaMcgEJXabKM27JGAyW0qj6SxeBpyyD4ftLl2.qNxazGkQ' \
#   -H 'origin: https://rivalsdata.com' \
#   -H 'priority: u=1, i' \
#   -H 'referer: https://rivalsdata.com/' \
#   -H 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"' \
#   -H 'sec-ch-ua-mobile: ?0' \
#   -H 'sec-ch-ua-platform: "Windows"' \
#   -H 'sec-fetch-dest: empty' \
#   -H 'sec-fetch-mode: cors' \
#   -H 'sec-fetch-site: same-site' \
#   -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36' \
#   --data-raw '{"uid":1142083854}'
    COPIED_CURL = r"""
curl 'https://api.rivalsdata.com/player' \
  -H 'authority: api.rivalsdata.com' \
  -H 'accept: application/json' \
  -H 'accept-language: en-US,en;q=0.9' \
  -H 'content-type: application/json' \
  -b 'cf_clearance=TSSflJQLEbiM34KbvEncOYLtcQehE9qNMVTcxXRCT7A-1785513493-1.2.1.1-reBuM77hB1h.ae1woAhLUTynQ.cGcb71MY3Ap2NJRSzZU3eU0U1O66FDeZg0EdgXYQb6iWxTYLNNWq9pcviVqgzZPu.hDLYBXdP_qV0F_ES9PzdYmfyCCTDzfCW05N.4zt7oXxNmZqRqkThWLDujzdalnxYZJ995swshq3xwcE.H7TjtYaxk8cnqgfgilKngD6AInPpWMFQlDRoX180j0Wx250qLoxYgneVc27rOnTP4SR_hg.vOWWgKAQ6BGQGZMo3oan.gmzVPCHdOyCxShcagrPhfbPdBIOTsoUyNbs5iLUjfdx45tI6v6j9Oxgx5zjIno2YAcId7ak9DWqov0kkWJu7TU6G6N.1wIzI867wH6kwR2j6.G69tsUCwN4HrGlXaEtaW_snWyCj_WCTmmCujrA5KRJqNy4nOAW0HaaMcgEJXabKM27JGAyW0qj6SxeBpyyD4ftLl2.qNxazGkQ' \
  -H 'origin: https://rivalsdata.com' \
  -H 'priority: u=1, i' \
  -H 'referer: https://rivalsdata.com/' \
  -H 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"' \
  -H 'sec-ch-ua-mobile: ?10' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-site' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36' \
  --data-raw '{"uid":1142083854}'
"""
    try:
        response = execute_curl_as_requests(curl)
        print_response(response)
        return response

    except ValueError as error:
        print("Could not parse cURL:", error)

    except requests.exceptions.Timeout:
        print("The request timed out.")

    except requests.exceptions.SSLError as error:
        print("SSL error:", error)

    except requests.exceptions.RequestException as error:
        print("Request error:", error)

if __name__ == "__main__":
    # Example usage
    url = "https://api.rivalsdata.com/player"
    cookie = "cf_clearance=TSSflJQLEbiM34KbvEncOYLtcQehE9qNMVT"
    pl = {"uid": 1142083854}
    response = curl_get(url, cookie, pl)
