# User Guide

MSCBot is a github bot that helps with managing MSCs (Matrix Spec Changes). It
does this by keeping track of Final Comment Periods (FCPs) and proposals for
them.

The bot can be controlled by members of a specified Github Team (defined in the
config) through commands. These commands are specified in Github comments on
proposals.

You can place a command in any part of a comment as long as it's on its own
line. The command must start with the Github username of the bot. An example:

```
This is a really great proposal! Let's merge it!

@mscbot fcp merge
```

The bot will verify the user is part of the right Github team, then post a
comment and edit labels, starting an FCP proposal.

Below is the list of available commands and what they do:

* `fcp`

  Proposes a FCP or cancel an existing one.
  
  Parameters:
  
    * `merge`
    
      Propose a FCP to merge the current proposal.
    
    * `close`
    
      Propose a FCP to close the current proposal.

    * `postpone`
    
      Propose a FCP to postpone the current proposal.
    
    Each of the above will start a FCP with the given *disposition* (merge,
    close or postpone). Other members of the appropriate Github team will then vote on
    whether a FCP should begin.
    
    * `cancel`
    
      Cancel a currently running FCP.
      
    There is no way to cancel an FCP proposal at this time.
  
  Example:
  
  ```
  @mscbot fcp merge
  ```
  
* `concern`

  Raises a concern on the current state of a proposal. This can only be done
  while an FCP proposal is ongoing.
  
  This will add a concern to the FCP proposal comment. Note that FCP is blocked
  until all raised concerns are resolved.
  
  Parameters:
  
    * The concern text
    
      Some text describing your concern.
  
  Example:

  ```
  @mscbot concern I don't think this proposal has enough horse photos.
  ```
  
* `resolve`

  Resolves a concern that has already been raised on the current proposal.
  
  Once the topic of a given concern has been sorted out, the concern should be
  marked as resolved.

  Concerns can be resolved by any authorised team member, regardless of whether they raised
  it themselves.
  
  Parameters:
  
    * The concern text
    
      Text of an existing concern.
  
  Example:
  
  ```
  @mscbot resolve I don't think this proposal has enough horse photos.
  ```

* `review`/`reviewed`

  Signify that you vote in favour of the current FCP proposal. This does the same thing as
  ticking the box next to your name in an FCP proposal comment.
  
  There is currently no command for retracting your vote, but you can do so by simply
  unticking the box next to your name in the FCP proposal comment.

  Example:

  ```
  @mscbot reviewed
  ```
