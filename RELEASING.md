# Releasing `mscbot-python`

To make a new release of `mscbot-python`, perform the following.

1. Determine the new version number. This project follows [semantic versioning](https://semver.org/). Store the release version in an environment variable called `RELEASE_VERSION`.

    ```
    export RELEASE_VERSION=X.Y.Z
    ```

    **Note:** Do not include a `v` before the version number.

1. Update `setup.py` with the new version number:

    ```
    sed -i "s/version=\"[0-9]\+\.[0-9]\+\.[0-9]\+\"/version=\"${RELEASE_VERSION}\"/" setup.py
    ```

1. Stage, commit and push the changes:

    ```
    git add setup.py
    git commit -m "$RELEASE_VERSION"
    ```

1. Create a new git tag:

    ```
    git tag $RELEASE_VERSION -m "$RELEASE_VERSION"
    ```

1. Push the tag to the repository:

    ```
    git push origin $RELEASE_VERSION
    ```

1. [Create a new release](https://github.com/matrix-org/mscbot-python/releases/new)
    on GitHub.
    Select the tag that was just created and click "Generate release notes".

    **Note:** A docker image will be automatically created and uploaded to
    DockerHub and the GitHub container repository when a release is published.

1. Press "Publish release", and you're done! 🍾