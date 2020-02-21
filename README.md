# MSCBot: Python Edition™

A bot to help facilitate the [Matrix Spec Proposal
Process](https://matrix.org/docs/spec/proposals).

However it is written in a generic way such that it can be used for any project wanting to
make use of a similar process.

# TODO: Postgres docs

## Installation

### Getting the code

```
git clone https://github.com/matrix-org/mscbot-python && cd mscbot-python
```

### Python dependencies

Create a virtual environment and activate it:

```
virtualenv -p python3 env
source env/bin/activate
```

Install packages:

```
pip install -e .
```

### Config

Copy and update the config file:

```
cp sample.config.yaml config.yaml
vi config.yaml
```

### Server and webhook setup

On github:

1. Go to your Github project -> Settings -> Webhooks
1. Add a new webhook, point it to a URL that the bot can be accessed at
1. Set the content type to `application/json`
1. Come up with and set a secret (hint: use the `uuid` terminal command)
1. Under events, select "Let me select individual events". And check the following:
    - Issue comments
    - Pull request review comments

On your server:

Edit the config file and
  - add the webhook secret
  - configure the appropriate webhook path (`/webhook` by default). The bot will listen
    here for webhook hits from github

### Usage

Activate the virtualenv and start mscbot:

```
source env/bin/activate
python -m mscbot
```

### Command line flags

The following command line options are available:

* `-c`/`config` - The path to a config file. Defaults to `./config.yaml`.

## Docker

### Getting the image
Either download the latest release from Dockerhub:

```
docker pull matrixdotorg/mscbot-python
```

Or build an image from the source locally:

```
docker build -t matrixdotorg/mscbot-python .
```

### Running

TODO: Set up postgres container

Put your config file somewhere and then mount it via a volume.

```
docker run -v /path/to/config/dir:/config matrixdotorg/mscbot-python python -m mscbot -c /config/config.yaml
```

## User guide

See [docs/user_guide.md](docs/user_guide.md).
