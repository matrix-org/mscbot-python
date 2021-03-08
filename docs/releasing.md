# Releasing mscbot-python

This document gives an overview of creating a new release of mscbot-python.

0. Make sure CI is passing and there are no outstanding critical bugs.

1. Update the version number in [setup.py](../setup.py) and create a new commit with 
   the commit title being the new version number in the form `X.Y.Z`.

2. Create a new, signed git tag with `git tag -s X.Y.Z`, and push it
   with `git tag -s 0.1.7`. The tag's body should contain a changelog with some useful
   information about what's changed since the last release.

3. [Create a new release](https://github.com/matrix-org/mscbot-python/releases/new) 
   with the new tag and the release title as the version number (`X.Y.Z`). Use the 
   body from the tag as the release notes. Publish the release.
   
The release is complete! A new tag should appear on [mscbot-python's Dockerhub page]
(https://hub.docker.com/r/matrixdotorg/mscbot-python/tags) (give it a few minutes to 
build).