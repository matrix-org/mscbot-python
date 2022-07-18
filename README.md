# MSCBot: Python Edition™

A bot to help facilitate the [Matrix Spec Proposal
Process](https://matrix.org/docs/spec/proposals).

However it is written in a generic way such that it can be used for any project wanting to
make use of a similar process.

## Installation

### Getting the code

```
git clone https://github.com/matrix-org/mscbot-python && cd mscbot-python
```

### Python dependencies

Create a virtual environment and activate it:

```
virtualenv -p python3 venv
source venv/bin/activate
```

Install packages:

```
pip install -e .
```

### OS dependencies

Install [Postgres](https://www.postgresql.org/download/).

Create a user and a database:

```
sudo -u postgres psql
postgres=# create database mscbot;
postgres=# create user mscbot with encrypted password 'super-strong-password';
postgres=# grant all privileges on database mscbot to mscbot;
```

### Config

Copy and update the config file:

```
cp sample.config.yaml config.yaml
vi config.yaml
```

Be sure to enter the postgres user, password and database details from above.

### Server and webhook setup

On github:

1. Go to your Github project -> Settings -> Webhooks
1. Add a new webhook, point it to a URL that the bot can be accessed at
1. Set the content type to `application/json`
1. Come up with and set a secret (hint: use the `uuid` terminal command)
1. Under events, select "Let me select individual events". Only the following need to be checked:
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
source venv/bin/activate
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

You'll also probably want a [postgres
container](https://hub.docker.com/_/postgres) to hold your database.

### Running

Put your config file somewhere and then mount it via a volume.

```
docker run -v /path/to/config/dir:/config matrixdotorg/mscbot-python python -m mscbot -c /config/config.yaml
```

## User guide

See [docs/user_guide.md](docs/user_guide.md).

## Development

Several python dependencies are necessary to support development scripts. They can be installed by running:

```
# Activate your python environment
source venv/bin/activate

# Install development dependencies in editable mode
pip install -e ".[dev]"
```

### Code linting

Before submitting a PR, make sure to lint your code:

```
./scripts-dev/lint.sh
```