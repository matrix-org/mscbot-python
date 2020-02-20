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

### Usage

Activate the virtualenv and start mscbot:

```
source env/bin/activate
python -m mscbot
```

## Design

### Storage

MSCBot uses Github as its state store. Modifying the state of a proposal is as easy as
editing a status comment (the comment with votes that the bot posts) or modifying labels.

Currently it also uses a single JSON file on disk to store timer information, but it is
proposed that this be migrated to be stored in comments as well.
