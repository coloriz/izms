# IZ*ONE Mail Shelter (for backup)

IZ\*ONE Mail Shelter is a Python program for pulling data out of IZ\*ONE Private Mail App server and saving as an HTML file.
It automatically recognize the difference between your local backup directory and the server inbox,
so it only downloads the new items.

## Getting Started

Before you run the script, you need to make a `user_settings.json`
in which the following variables are defined:
```json
{
  "user_id": "<YOUR_USER_ID>",
  "access_token": "<YOUR_ACCESS_TOKEN>",
  "download_path": "<DOWNLOAD_PATH>"
}
```
`user_settings.json` should be located in the same directory as `run.py`.

> 🔔 This document does not cover how you get these IDs or tokens.

### Prerequisites
- Python 3.6+
- beautifulsoup4 >= 4.8.2
- colorama >= 0.4.3
- lxml >= 4.5.0
- requests >= 2.22.0

### Download CSS (optional)
Because of the huge size of a CSS linked in HTML, I choose not to nest it.
Instead, you can download it manually.
```shell script
curl -O "<APP_HOST>/css/starship.css"
```
and place it at `<http_root>/css/`.

## Usage
```shell script
$ python3 run.py
```

### Directory structure
> 🔔 This is not mandatory.
- <http_root>
    - css
        - starship.css
    - <download_path>
        - 1 (This is a member id)
            - m100.html
            - m103.html
        - 2
            - m101.html
        - 3
            - m102.html
        - ...

### How to see
The easiest way to see these HTMLs is to run a local http server.
This method also can solve a browsers' invalid protocol error.
```shell script
"@http_root"$ python3 -m http.server
```
