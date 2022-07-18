# Was used to add 'unresolved-concern' labels to all MSCs with unresolved concerns.
# Left here for posterity.
# main()'s github_access_token var will need to be populated to run this again.

import logging
import re
from typing import List, Optional, Tuple

from github import Github
from github.AuthenticatedUser import AuthenticatedUser
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.PaginatedList import PaginatedList
from progress.bar import Bar

log = logging.getLogger(__name__)


def _get_status_comment(
    github_user: AuthenticatedUser, proposal: Issue
) -> Optional[IssueComment]:
    """Retrieves an existing status comment for a proposal

    Returns:
        The status comment, or None if it cannot be found.
    """
    # Retrieve all of the comments for the proposal
    comments: PaginatedList = proposal.get_comments()

    # Find the latest status comment
    for comment in comments.reversed:
        if (
            comment.body.startswith("Team member @")
            and comment.user.login == github_user.login
        ):
            return comment

    return None


def _parse_concerns_from_status_comment_body(
    comment_body: str,
) -> List[Tuple[str, bool]]:
    """Retrieves the concerns and their resolved state from the body of a given
    status comment.
    """
    concern_tuples = []

    # We search for a list of concerns in the comment body, however
    # tagged members is also a list. We know the list of concerns will
    # come after a line starting with "concerns:", so ignore all list
    # items before that
    past_tagged_people_list = False
    for line in comment_body.split("\n"):
        # Check if we've passed the Concerns: bit of a status comment yet
        if line.lower().startswith("concerns:"):
            past_tagged_people_list = True
        if not past_tagged_people_list:
            continue

        # Check if this is a concern line
        if line.startswith("* ") or line.startswith("- "):
            # Check if this concern is resolved or not
            if line.startswith("* ~~") or line.startswith("- ~~"):
                # Extract concern text from resolved concern
                match = re.match(r"^[*|-] ~~(.+)~~.*", line)
                if not match:
                    log.error(
                        "Unable to match a resolved concern ('%s') with our regex",
                        line,
                    )
                    continue

                # Get the concern text from the regex match
                concern_text = match.group(1)
                concern_tuples.append((concern_text, True))
            else:
                # Extract concern text from non-resolved concern
                concern_tuples.append((line[2:], False))

    return concern_tuples


def main():
    github_access_token = ""
    github_repo = "matrix-org/matrix-spec-proposals"

    # Log into github with provided access token
    github = Github(github_access_token)
    if not github:
        log.fatal("Unable to connect to github")
        return

    # Connect to the configured repository
    repo = github.get_repo(github_repo)
    if not repo:
        log.fatal(f"Unable to connect to github repo '{github_repo}'")
        return

    # Get the user object of the bot
    github_user = github.get_user()
    if not github_user:
        log.fatal("Unable to download our own github user information")
        return

    log.info("Successfully logged in as %s!", github_user.login)

    # Get all issues/prs with the proposal tag
    proposals = repo.get_issues(labels=["proposal"])

    with Bar("Checking and labelling MSCs...", max=proposals.totalCount) as bar:
        for proposal in proposals:
            # Get the current concerns
            status_comment = _get_status_comment(github_user, proposal)
            if not status_comment:
                # FCP has not been proposed for this MSC yet
                bar.next()
                continue

            concerns = _parse_concerns_from_status_comment_body(status_comment.body)
            unresolved_concerns = [c for c in concerns if c[1] is False]

            # If any concerns exist, add the label
            if unresolved_concerns:
                proposal.add_to_labels("unresolved-concerns")
                print(" - Adding label to proposal #%d" % (proposal.number,))

            bar.next()


if __name__ == "__main__":
    main()
