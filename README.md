# MSCBot Python

mscbot written in python.

## Installation

### Getting the code

```
git clone https://github.com/matrix-org/mscbot-python && cd mscbot-python
```

### Distro dependencies

Ubuntu: `apt install libpq-dev python-virtualenv postgres`

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

## Database setup

Create a postgres user and database for mscbot:

```
sudo -u postgres createuser mscbot  # prompts for password
sudo -u postgres createdb -O mscbot mscbot
```

## Config

Copy and update the config file:

```
cp sample.config.yaml config.yaml
# update config.yaml
```

## Usage

Activate the virtualenv and start mscbot:

```
source env/bin/activate
python -m mscbot
```
