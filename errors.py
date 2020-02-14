class ConfigError(RuntimeError):
    """An error encountered during reading the config file
    Args:
        msg (str): The message displayed on error
    """
    def __init__(self, msg):
        super(ConfigError, self).__init__("%s" % (msg,))


class ProposalNotInFCP(RuntimeError):
    """An error encountered when a command is performed on an FCP that could
    only be performed on one in FCP, but it is not in FCP

    Args:
        msg (str): The message displayed on error
    """
    def __init__(self, msg):
        super(ProposalNotInFCP, self).__init__("%s" % (msg,))
