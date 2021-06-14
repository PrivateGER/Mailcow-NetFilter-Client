import os
import argparse
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich import box
import sys
import requests
import json

debug = os.environ.get("DEBUG")
credentials = {}

def create_api_details_file():
    console = Console()
    console.print("Your [pink]~/.mailcow-creds[/] file [red]doesn't exist or isn't accessible![/] Starting setup...")
    fqdn = wizard_get_fqdn(console)
    key = wizard_get_api_key(console)



    with Progress(transient=False, auto_refresh=False) as progress:
        t1 = progress.add_task(":key: Testing access to Mailcow...", total=2)
        progress.refresh()

        if debug:
            console.log("Sending GET / to https://" + fqdn + "/")
        access_response = requests.get("https://" + fqdn + "/")
        if debug:
            console.log("Response: " + str(access_response.status_code) + " " + access_response.reason)
        if access_response.status_code != 200:
            progress.stop()
            progress.refresh()
            console.print(":compass: [red bold]Status code returned by https://" + fqdn + "/ is not 200![/]")
            return
        progress.update(t1, advance=1)
        progress.refresh()

        key_response = requests.get("https://" + fqdn + "/api/v1/get/fail2ban", headers={"X-Api-Key": key})
        if key_response.status_code != 200:
            progress.stop()
            progress.refresh()
            console.print(":key: [red bold]Status code returned by https://" + fqdn + "/api/v1/get/fail2ban is not "
                                                                                      "200! Is your API key invalid?["
                                                                                      "/]")
            return
        progress.update(t1, advance=1)
        progress.refresh()

    with Progress(transient=False, auto_refresh=False) as progress:
        t2 = progress.add_task("Saving configuration...", total=3)
        progress.refresh()

        json_config = json.dumps({"key": key, "fqdn": fqdn})
        progress.update(t2, advance=1)
        progress.refresh()

        f = open(os.path.expanduser("~") + "/.mailcow_creds", "w")
        progress.update(t2, advance=1)
        progress.refresh()

        f.write(json_config)
        f.close()
        progress.update(t2, advance=1)
        progress.refresh()

    console.print(":ok: All done! Re-run this script to use the fail2ban client.")

def wizard_get_fqdn(console):
    while True:
        fqdn = console.input(":compass: What is the [bold green]FQDN[/] of your mailcow instance (without protocol)? ")
        if fqdn.startswith("http"):
            console.print("[red]Only enter the FQDN, do not include a protocol handler![/]")
            continue
        if fqdn.endswith("/"):
            console.print("[red]Only enter the FQDN, do not include a trailing slash![/]")
            continue
        if '.' not in fqdn:
            console.print("[red]That doesn't seem to be a valid FQDN...[/]")
            continue
        if debug:
            console.log("FQDN = " + fqdn)
        return fqdn


def wizard_get_api_key(console):
    while True:
        key = console.input(":key: What is the API key of your mailcow instance (without protocol)? ")
        if len(key) != 34:
            console.print("[red]Invalid API key (incorrect length)![/]")
            continue

        if debug:
            console.log("key = " + key)
        return key


def load_api_details():
    console = Console()
    filename = os.path.expanduser("~") + "/.mailcow_creds"
    if debug:
        console.log("Opening " + os.path.expanduser("~") + "/.mailcow_creds in read-only mode...")
    with open(filename, 'r') as file:
        data = file.read().replace('\n', '')
        parsed = json.loads(data)

        if debug:
            console.log("File content: " + data)
            console.log("Parsed JSON dict: " + str(parsed))

        credentials['fqdn'] = parsed['fqdn']
        credentials['key'] = parsed['key']


def list_banned_ips():
    console = Console()
    parsed_res = {}
    with Progress(transient=False, auto_refresh=False) as progress:
        t = progress.add_task("Sending API request...", total=1)

        if debug:
            console.log("\r\nSending GET request to https://" + credentials['fqdn'] + "/api/v1/get/fail2ban")
        response = requests.get("https://" + credentials['fqdn'] + "/api/v1/get/fail2ban",
                                headers={"X-Api-Key": credentials['key']})
        parsed_res = response.json()
        if debug:
            console.log("Parsed response: " + str(parsed_res))

        progress.update(t, advance=1)
        progress.refresh()

    table = Table(title="Currently banned IPs", box=box.SQUARE)
    table.add_column("IP")
    table.add_column("Ban duration", justify="right")

    if "active_bans" in parsed_res:
        for ban in parsed_res["active_bans"]:
            table.add_row(ban["network"], "[red]" + ban["banned_until"] + "[/]")

    console.print(table)
    if "active_bans" not in parsed_res:
        console.print("No banned IPs :smile:")


def banner():
    console = Console()
    console.print("[green]:cow: Mailcow NetFilter Client v0.1 :cow:[/]")


if __name__ == '__main__':
    banner()
    if not os.path.isfile(os.path.expanduser("~") + "/.mailcow_creds"): # no API cred file
        create_api_details_file()
    load_api_details()
    list_banned_ips()
